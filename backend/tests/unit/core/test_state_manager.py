"""Unit tests for the StateManager."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.core.state_manager import StateManager
from app.models.session import ConversationSession


class TestStateManager:
    """Test cases for the StateManager class."""

    @pytest.mark.asyncio
    async def test_get_or_create_session_creates_new(self, db_session, sample_agent):
        """Test creating a new session."""
        manager = StateManager(db_session)

        session = await manager.get_or_create_session(
            session_id=None,
            user_id="new_user",
            root_agent_id=sample_agent.config_id,
        )

        assert session is not None
        assert session.user_id == "new_user"
        assert len(session.agent_stack) == 1
        assert session.agent_stack[0]["agentId"] == sample_agent.config_id
        assert session.status == "active"

    @pytest.mark.asyncio
    async def test_get_or_create_session_returns_existing(
        self, db_session, sample_session, sample_agent
    ):
        """Test returning an existing session."""
        manager = StateManager(db_session)

        session = await manager.get_or_create_session(
            session_id=sample_session.session_id,
            user_id=sample_session.user_id,
            root_agent_id=sample_agent.config_id,
        )

        assert session.session_id == sample_session.session_id

    @pytest.mark.asyncio
    async def test_get_session(self, db_session, sample_session):
        """Test getting a session by ID."""
        manager = StateManager(db_session)

        session = await manager.get_session(sample_session.session_id)

        assert session is not None
        assert session.session_id == sample_session.session_id

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, db_session):
        """Test getting a non-existent session."""
        manager = StateManager(db_session)

        session = await manager.get_session(uuid4())

        assert session is None

    @pytest.mark.asyncio
    async def test_get_current_agent(self, db_session, sample_session, sample_agent):
        """Test getting the current agent from session."""
        manager = StateManager(db_session)

        # get_current_agent is now synchronous
        agent = manager.get_current_agent(sample_session)

        assert agent is not None
        assert agent.config_id == sample_agent.config_id
        assert agent.name == sample_agent.name

    @pytest.mark.asyncio
    async def test_push_agent(self, db_session, sample_session, sample_child_agent):
        """Test pushing an agent onto the stack."""
        manager = StateManager(db_session)
        original_stack_len = len(sample_session.agent_stack)

        await manager.push_agent(
            sample_session, sample_child_agent.config_id, "User requested topups"
        )

        assert len(sample_session.agent_stack) == original_stack_len + 1
        assert sample_session.agent_stack[-1]["agentId"] == sample_child_agent.config_id
        assert sample_session.agent_stack[-1]["entryReason"] == "User requested topups"
        # Flow state should be cleared
        assert sample_session.current_flow is None
        assert sample_session.pending_confirmation is None

    @pytest.mark.asyncio
    async def test_pop_agent(self, db_session, sample_session_with_child):
        """Test popping an agent from the stack."""
        manager = StateManager(db_session)
        original_stack_len = len(sample_session_with_child.agent_stack)

        new_agent_id = await manager.pop_agent(sample_session_with_child)

        assert new_agent_id is not None
        assert len(sample_session_with_child.agent_stack) == original_stack_len - 1
        assert sample_session_with_child.current_flow is None

    @pytest.mark.asyncio
    async def test_pop_agent_prevents_empty_stack(self, db_session, sample_session):
        """Test that pop_agent doesn't remove the last agent."""
        manager = StateManager(db_session)

        # Stack has only one agent
        assert len(sample_session.agent_stack) == 1

        new_agent_id = await manager.pop_agent(sample_session)

        assert new_agent_id is None
        assert len(sample_session.agent_stack) == 1

    @pytest.mark.asyncio
    async def test_go_home(self, db_session, sample_session_with_child):
        """Test going home to root agent."""
        manager = StateManager(db_session)
        root_agent_id = sample_session_with_child.agent_stack[0]["agentId"]

        # Session has multiple agents in stack
        assert len(sample_session_with_child.agent_stack) > 1

        result_agent_id = await manager.go_home(sample_session_with_child)

        assert result_agent_id == root_agent_id
        assert len(sample_session_with_child.agent_stack) == 1
        assert sample_session_with_child.current_flow is None

    @pytest.mark.asyncio
    async def test_escalate(self, db_session, sample_session):
        """Test escalating a session."""
        manager = StateManager(db_session)

        await manager.escalate(sample_session, "User requested human")

        assert sample_session.status == "escalated"
        assert sample_session.current_flow is None
        assert sample_session.pending_confirmation is None

    @pytest.mark.asyncio
    async def test_set_and_clear_pending_confirmation(self, db_session, sample_session):
        """Test setting and clearing pending confirmation."""
        manager = StateManager(db_session)

        await manager.set_pending_confirmation(
            sample_session,
            tool_name="send_topup",
            tool_params={"phone_number": "+52 55 1234 5678", "amount": 100},
            display_message="Confirm topup?",
            expires_minutes=5,
        )

        assert sample_session.pending_confirmation is not None
        assert sample_session.pending_confirmation["toolName"] == "send_topup"
        assert sample_session.pending_confirmation["toolParams"]["amount"] == 100

        await manager.clear_pending_confirmation(sample_session)

        assert sample_session.pending_confirmation is None

    def test_is_confirmation_expired_no_confirmation(self, db_session):
        """Test confirmation expiration check with no confirmation."""
        manager = StateManager(db_session)
        session = ConversationSession(user_id="test")

        assert manager.is_confirmation_expired(session) is True

    def test_is_confirmation_expired_future(self, db_session):
        """Test confirmation expiration check with future expiry."""
        manager = StateManager(db_session)
        session = ConversationSession(user_id="test")
        session.pending_confirmation = {
            "expiresAt": (datetime.utcnow() + timedelta(hours=1)).isoformat()
        }

        assert manager.is_confirmation_expired(session) is False

    def test_is_confirmation_expired_past(self, db_session):
        """Test confirmation expiration check with past expiry."""
        manager = StateManager(db_session)
        session = ConversationSession(user_id="test")
        session.pending_confirmation = {
            "expiresAt": (datetime.utcnow() - timedelta(hours=1)).isoformat()
        }

        assert manager.is_confirmation_expired(session) is True

    @pytest.mark.asyncio
    async def test_update_flow_data(self, db_session, sample_session):
        """Test updating flow data."""
        manager = StateManager(db_session)

        # Set up a current flow
        sample_session.current_flow = {
            "flowId": str(uuid4()),
            "currentState": "collect_number",
            "stateData": {"phone_number": "+52 55 1234 5678"},
            "enteredAt": datetime.utcnow().isoformat(),
        }

        await manager.update_flow_data(sample_session, {"carrier_id": "telcel"})

        assert sample_session.current_flow["stateData"]["phone_number"] == "+52 55 1234 5678"
        assert sample_session.current_flow["stateData"]["carrier_id"] == "telcel"

    @pytest.mark.asyncio
    async def test_increment_message_count(self, db_session, sample_session):
        """Test incrementing message count."""
        manager = StateManager(db_session)
        original_count = sample_session.message_count

        await manager.increment_message_count(sample_session)

        assert sample_session.message_count == original_count + 1

    @pytest.mark.asyncio
    async def test_end_session(self, db_session, sample_session):
        """Test ending a session."""
        manager = StateManager(db_session)

        await manager.end_session(sample_session, "completed")

        assert sample_session.status == "completed"
        assert sample_session.current_flow is None
        assert sample_session.pending_confirmation is None
