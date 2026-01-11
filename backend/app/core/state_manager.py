"""State manager for conversation sessions and flow state."""

import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import ConversationSession
from app.models.agent import Agent
from app.models.subflow import Subflow, SubflowState

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

    async def get_current_agent(self, session: ConversationSession) -> Optional[Agent]:
        """Get the current agent from the session's agent stack."""
        agent_id = session.get_current_agent_id()
        if not agent_id:
            return None

        result = await self.db.execute(
            select(Agent).where(Agent.id == UUID(agent_id))
        )
        return result.scalar_one_or_none()

    async def push_agent(
        self, session: ConversationSession, agent_id: str, reason: str
    ) -> ConversationSession:
        """Push a new agent onto the session's agent stack."""
        session.push_agent(agent_id, reason)
        # Clear any active flow when changing agents
        session.current_flow = None
        session.pending_confirmation = None
        logger.info(f"Session {session.session_id}: pushed agent {agent_id}")
        return session

    async def pop_agent(self, session: ConversationSession) -> Optional[str]:
        """Pop the current agent and return the new current agent ID."""
        popped = session.pop_agent()
        if popped:
            # Clear flow state
            session.current_flow = None
            session.pending_confirmation = None
            logger.info(f"Session {session.session_id}: popped agent {popped.get('agentId')}")
            return session.get_current_agent_id()
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
        self, session: ConversationSession, subflow: Subflow
    ) -> ConversationSession:
        """Enter a subflow."""
        session.current_flow = {
            "flowId": str(subflow.id),
            "currentState": subflow.initial_state,
            "stateData": {},
            "enteredAt": datetime.utcnow().isoformat(),
        }
        logger.info(
            f"Session {session.session_id}: entered flow {subflow.name}, state {subflow.initial_state}"
        )
        return session

    async def transition_state(
        self, session: ConversationSession, new_state_id: str, state_def: SubflowState
    ) -> ConversationSession:
        """Transition to a new state within the current flow."""
        if not session.current_flow:
            raise ValueError("Not in a flow")

        old_state = session.current_flow.get("currentState")
        session.current_flow["currentState"] = new_state_id

        logger.info(
            f"Session {session.session_id}: state transition {old_state} -> {new_state_id}"
        )

        # Check if terminal state
        if state_def.is_final:
            logger.info(f"Session {session.session_id}: reached terminal state, exiting flow")
            session.current_flow = None

        return session

    async def update_flow_data(
        self, session: ConversationSession, data: dict
    ) -> ConversationSession:
        """Update the data collected during the flow."""
        if session.current_flow:
            current_data = session.current_flow.get("stateData", {})
            current_data.update(data)
            session.current_flow["stateData"] = current_data
        return session

    async def set_pending_confirmation(
        self,
        session: ConversationSession,
        tool_name: str,
        tool_params: dict,
        display_message: str,
        expires_minutes: int = 5,
    ) -> ConversationSession:
        """Set a pending confirmation for a tool execution."""
        session.pending_confirmation = {
            "toolName": tool_name,
            "toolParams": tool_params,
            "displayMessage": display_message,
            "expiresAt": (datetime.utcnow() + timedelta(minutes=expires_minutes)).isoformat(),
        }
        logger.info(f"Session {session.session_id}: set pending confirmation for {tool_name}")
        return session

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

    async def get_subflow(self, flow_id: str) -> Optional[Subflow]:
        """Get a subflow by ID."""
        result = await self.db.execute(
            select(Subflow).where(Subflow.id == UUID(flow_id))
        )
        return result.scalar_one_or_none()

    async def get_flow_state(
        self, subflow_id: str, state_id: str
    ) -> Optional[SubflowState]:
        """Get a specific state within a subflow."""
        result = await self.db.execute(
            select(SubflowState).where(
                SubflowState.subflow_id == UUID(subflow_id),
                SubflowState.state_id == state_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_current_flow_state(
        self, session: ConversationSession
    ) -> Optional[SubflowState]:
        """Get the current flow state if session is in a flow."""
        if not session.current_flow:
            return None
        return await self.get_flow_state(
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
