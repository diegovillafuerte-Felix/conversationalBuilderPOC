"""State manager for conversation sessions and flow state."""

import copy
import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.session import ConversationSession
from app.core.agent_registry import get_agent_registry
from app.core.config_types import AgentConfig, SubflowConfig, SubflowStateConfig

logger = logging.getLogger(__name__)


class StateManager:
    """Manages conversation state, agent navigation, and flow transitions."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_session(
        self,
        session_id: Optional[UUID],
        user_id: str,
        root_agent_id: str,
    ) -> ConversationSession:
        """Get existing session or create a new one."""
        if session_id:
            result = await self.db.execute(
                select(ConversationSession).where(
                    ConversationSession.session_id == session_id
                )
            )
            session = result.scalar_one_or_none()
            if session:
                return session

        # Create new session
        session = ConversationSession(
            user_id=user_id,
            agent_stack=[
                {
                    "agentId": root_agent_id,
                    "enteredAt": datetime.utcnow().isoformat(),
                    "entryReason": "Session start",
                }
            ],
            status="active",
        )
        self.db.add(session)
        await self.db.flush()
        logger.info(f"Created new session {session.session_id} for user {user_id}")
        return session

    async def get_session(self, session_id: UUID) -> Optional[ConversationSession]:
        """Get a session by ID."""
        result = await self.db.execute(
            select(ConversationSession).where(
                ConversationSession.session_id == session_id
            )
        )
        return result.scalar_one_or_none()

    def get_current_agent(self, session: ConversationSession) -> Optional[AgentConfig]:
        """Get the current agent from the session's agent stack (sync - no DB)."""
        agent_id = session.get_current_agent_id()
        if not agent_id:
            return None
        return get_agent_registry().get_agent(agent_id)

    async def push_agent(
        self,
        session: ConversationSession,
        agent_id: str,
        reason: str,
        preserve_flow: bool = False,
    ) -> ConversationSession:
        """
        Push a new agent onto the session's agent stack with row-level locking.

        Args:
            session: The conversation session
            agent_id: ID of the agent to push
            reason: Reason for entering this agent
            preserve_flow: If True, preserve current flow state for resumption
                          when returning to previous agent (used by shadow service)

        Returns:
            Updated session with locked changes committed
        """
        # Re-fetch session with FOR UPDATE lock to prevent race conditions
        result = await self.db.execute(
            select(ConversationSession)
            .where(ConversationSession.session_id == session.session_id)
            .with_for_update()
        )
        locked_session = result.scalar_one()

        # Store current flow state if preserving
        if preserve_flow and locked_session.current_flow:
            # Store the preserved flow in the current stack frame before pushing
            if locked_session.agent_stack:
                current_frame = locked_session.agent_stack[-1]
                # Deep copy to avoid reference issues
                current_frame["preservedFlow"] = copy.deepcopy(locked_session.current_flow)
                current_frame["preservedConfirmation"] = copy.deepcopy(
                    locked_session.pending_confirmation
                )
                # Explicit reassignment for SQLAlchemy change detection
                locked_session.agent_stack = locked_session.agent_stack.copy()

        locked_session.push_agent(agent_id, reason)

        # Clear flow state for the new agent
        locked_session.current_flow = None
        locked_session.pending_confirmation = None

        await self.db.flush()  # Persist and release lock

        logger.info(
            f"Session {locked_session.session_id}: pushed agent {agent_id}"
            f"{' (flow preserved)' if preserve_flow else ''}"
        )
        return locked_session

    async def pop_agent(self, session: ConversationSession) -> Optional[str]:
        """
        Pop the current agent and return the new current agent ID with row-level locking.

        If the previous agent had a preserved flow state (from shadow takeover),
        restore it so the user can continue where they left off.
        """
        # Re-fetch session with FOR UPDATE lock
        result = await self.db.execute(
            select(ConversationSession)
            .where(ConversationSession.session_id == session.session_id)
            .with_for_update()
        )
        locked_session = result.scalar_one()

        popped = locked_session.pop_agent()
        if popped:
            logger.info(f"Session {locked_session.session_id}: popped agent {popped.get('agentId')}")

            # Check if the new current agent has a preserved flow to restore
            if locked_session.agent_stack:
                current_frame = locked_session.agent_stack[-1]
                preserved_flow = current_frame.pop("preservedFlow", None)
                preserved_confirmation = current_frame.pop("preservedConfirmation", None)

                if preserved_flow:
                    locked_session.current_flow = preserved_flow
                    locked_session.pending_confirmation = preserved_confirmation
                    # Explicit reassignment for change detection
                    locked_session.agent_stack = locked_session.agent_stack.copy()
                    logger.info(
                        f"Session {locked_session.session_id}: restored preserved flow "
                        f"state {preserved_flow.get('currentState')}"
                    )
                else:
                    # No preserved flow, clear state as before
                    locked_session.current_flow = None
                    locked_session.pending_confirmation = None
            else:
                locked_session.current_flow = None
                locked_session.pending_confirmation = None

            await self.db.flush()  # Persist and release lock
            return locked_session.get_current_agent_id()

        await self.db.flush()  # Release lock even if nothing was popped
        return None

    async def go_home(self, session: ConversationSession) -> str:
        """Return to the root agent."""
        if len(session.agent_stack) > 1:
            root_frame = session.agent_stack[0]
            session.agent_stack = [root_frame]
            session.current_flow = None
            session.pending_confirmation = None
            logger.info(f"Session {session.session_id}: returned home")
        return session.get_current_agent_id()

    async def escalate(self, session: ConversationSession, reason: str) -> None:
        """Mark session as escalated."""
        session.status = "escalated"
        session.current_flow = None
        session.pending_confirmation = None
        logger.info(f"Session {session.session_id}: escalated - {reason}")

    async def enter_subflow(
        self, session: ConversationSession, subflow: SubflowConfig, initial_data: dict = None
    ) -> ConversationSession:
        """Enter a subflow with optional initial data from tool parameters."""
        # Check if already in this flow (prevent duplicate entries)
        if session.current_flow and session.current_flow.get("flowId") == subflow.config_id:
            logger.warning(
                f"Already in flow {subflow.name} (ID: {subflow.config_id}) - ignoring duplicate entry"
            )
            return session

        session.current_flow = {
            "agentId": subflow.agent_id,      # Agent config_id (for lookups)
            "flowId": subflow.config_id,       # Subflow config_id
            "currentState": subflow.initial_state,
            "stateData": initial_data or {},
            "enteredAt": datetime.utcnow().isoformat(),
        }
        logger.info(
            f"Session {session.session_id}: entered flow {subflow.name}, state {subflow.initial_state}, "
            f"initial_data: {list((initial_data or {}).keys())}"
        )
        return session

    async def transition_state(
        self, session: ConversationSession, new_state_id: str, state_def: SubflowStateConfig
    ) -> ConversationSession:
        """Transition to a new state within the current flow with row-level locking."""
        # Re-fetch session with FOR UPDATE lock
        result = await self.db.execute(
            select(ConversationSession)
            .where(ConversationSession.session_id == session.session_id)
            .with_for_update()
        )
        locked_session = result.scalar_one()

        if not locked_session.current_flow:
            raise ValueError("Not in a flow")

        old_state = locked_session.current_flow.get("currentState")
        locked_session.current_flow["currentState"] = new_state_id
        flag_modified(locked_session, "current_flow")

        logger.info(
            f"Session {locked_session.session_id}: state transition {old_state} -> {new_state_id}"
        )

        # Check if terminal state
        if state_def.is_final:
            logger.info(f"Session {locked_session.session_id}: reached terminal state, exiting flow")
            locked_session.current_flow = None

        await self.db.flush()  # Persist and release lock
        return locked_session

    async def update_flow_data(
        self, session: ConversationSession, data: dict
    ) -> ConversationSession:
        """Update the data collected during the flow with row-level locking."""
        # Re-fetch session with FOR UPDATE lock
        result = await self.db.execute(
            select(ConversationSession)
            .where(ConversationSession.session_id == session.session_id)
            .with_for_update()
        )
        locked_session = result.scalar_one()

        if locked_session.current_flow:
            current_data = locked_session.current_flow.get("stateData", {})
            current_data.update(data)
            locked_session.current_flow["stateData"] = current_data
            flag_modified(locked_session, "current_flow")

        await self.db.flush()  # Persist and release lock
        return locked_session

    async def set_pending_confirmation(
        self,
        session: ConversationSession,
        tool_name: str,
        tool_params: dict,
        display_message: str,
        expires_minutes: int = 5,
    ) -> ConversationSession:
        """Set a pending confirmation for a tool execution with row-level locking."""
        # Re-fetch session with FOR UPDATE lock
        result = await self.db.execute(
            select(ConversationSession)
            .where(ConversationSession.session_id == session.session_id)
            .with_for_update()
        )
        locked_session = result.scalar_one()

        locked_session.pending_confirmation = {
            "toolName": tool_name,
            "toolParams": tool_params,
            "displayMessage": display_message,
            "expiresAt": (datetime.utcnow() + timedelta(minutes=expires_minutes)).isoformat(),
        }

        await self.db.flush()  # Persist and release lock
        logger.info(f"Session {locked_session.session_id}: set pending confirmation for {tool_name}")
        return locked_session

    async def clear_pending_confirmation(
        self, session: ConversationSession
    ) -> ConversationSession:
        """Clear any pending confirmation."""
        session.pending_confirmation = None
        return session

    def is_confirmation_expired(self, session: ConversationSession) -> bool:
        """Check if the pending confirmation has expired."""
        if not session.pending_confirmation:
            return True
        expires_at = session.pending_confirmation.get("expiresAt")
        if not expires_at:
            return True
        return datetime.utcnow() > datetime.fromisoformat(expires_at)

    def get_subflow(self, agent_id: str, subflow_id: str) -> Optional[SubflowConfig]:
        """Get a subflow by agent and subflow config_ids (sync - no DB)."""
        return get_agent_registry().get_subflow(agent_id, subflow_id)

    def get_flow_state(
        self, agent_id: str, subflow_id: str, state_id: str
    ) -> Optional[SubflowStateConfig]:
        """Get a specific state within a subflow (sync - no DB)."""
        return get_agent_registry().get_flow_state(agent_id, subflow_id, state_id)

    def get_current_flow_state(
        self, session: ConversationSession
    ) -> Optional[SubflowStateConfig]:
        """Get the current flow state if session is in a flow (sync - no DB)."""
        if not session.current_flow:
            return None
        return self.get_flow_state(
            session.current_flow["agentId"],
            session.current_flow["flowId"],
            session.current_flow["currentState"],
        )

    async def increment_message_count(
        self, session: ConversationSession
    ) -> ConversationSession:
        """Increment the session's message count."""
        session.message_count = (session.message_count or 0) + 1
        session.last_interaction_at = datetime.utcnow()
        return session

    async def end_session(
        self, session: ConversationSession, reason: str = "completed"
    ) -> ConversationSession:
        """End a session."""
        session.status = reason
        session.current_flow = None
        session.pending_confirmation = None
        logger.info(f"Session {session.session_id}: ended - {reason}")
        return session
