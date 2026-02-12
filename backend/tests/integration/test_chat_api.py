"""Integration tests for the Chat API."""

import pytest


class TestChatAPIEndpoints:
    """Test cases for the Chat API endpoints."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_health_check(self, test_client):
        """Test health check endpoint."""
        response = await test_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_send_message_new_session(self, test_client, sample_agent):
        """Test sending a message creates a new session."""
        response = await test_client.post(
            "/api/chat/message",
            json={
                "user_id": "test_user",
                "message": "Hola",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "message" in data
        assert data["agent_name"] is not None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_send_message_existing_session(self, test_client, sample_session):
        """Test sending a message to an existing session."""
        response = await test_client.post(
            "/api/chat/message",
            json={
                "user_id": sample_session.user_id,
                "session_id": str(sample_session.session_id),
                "message": "Quiero hacer una recarga",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == str(sample_session.session_id)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_session(self, test_client, sample_agent):
        """Test creating a new session explicitly."""
        response = await test_client.post(
            "/api/chat/session",
            json={"user_id": "new_user"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "new_user"
        assert data["status"] == "active"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_session(self, test_client, sample_session):
        """Test getting session information."""
        response = await test_client.get(
            f"/api/chat/session/{sample_session.session_id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == str(sample_session.session_id)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_session_not_found(self, test_client):
        """Test getting non-existent session."""
        import uuid

        response = await test_client.get(f"/api/chat/session/{uuid.uuid4()}")

        assert response.status_code == 404

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_end_session(self, test_client, sample_session):
        """Test ending a session."""
        response = await test_client.post(
            f"/api/chat/session/{sample_session.session_id}/end",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_users(self, test_client, sample_user_context):
        """Test listing test users."""
        response = await test_client.get("/api/chat/users")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestChatAPIMessageFlow:
    """Test cases for message flow scenarios."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_conversation_returns_response_fields(
        self, test_client, sample_agent
    ):
        """Test that responses include expected fields."""
        response = await test_client.post(
            "/api/chat/message",
            json={
                "user_id": "test_user",
                "message": "Hola, quiero ayuda",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Check all expected fields are present
        assert "session_id" in data
        assert "message" in data
        assert "agent_id" in data
        assert "agent_name" in data
        assert "tool_calls" in data
        assert isinstance(data["tool_calls"], list)
        assert "escalated" in data
        assert data["escalated"] is False

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_session_persists_across_messages(
        self, test_client, sample_agent
    ):
        """Test that session state persists across messages."""
        # First message - creates session
        response1 = await test_client.post(
            "/api/chat/message",
            json={
                "user_id": "test_user",
                "message": "Hola",
            },
        )
        session_id = response1.json()["session_id"]

        # Second message - uses same session
        response2 = await test_client.post(
            "/api/chat/message",
            json={
                "user_id": "test_user",
                "session_id": session_id,
                "message": "¿Qué puedo hacer?",
            },
        )

        assert response2.json()["session_id"] == session_id


class TestConversationReviewEndpoints:
    """Integration tests for conversation browse/detail/event endpoints."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_conversations(self, test_client):
        """List conversations after creating one via chat flow."""
        await test_client.post(
            "/api/chat/message",
            json={"user_id": "review_user", "message": "Hola"},
        )

        response = await test_client.get("/api/chat/conversations")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "session_id" in data[0]

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_conversation_detail_and_events(self, test_client):
        """Conversation detail and events should be retrievable for a session."""
        create_resp = await test_client.post(
            "/api/chat/message",
            json={"user_id": "review_user_2", "message": "Necesito ayuda"},
        )
        session_id = create_resp.json()["session_id"]

        detail_resp = await test_client.get(f"/api/chat/conversations/{session_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["session_id"] == session_id
        assert isinstance(detail.get("messages", []), list)

        events_resp = await test_client.get(f"/api/chat/conversations/{session_id}/events")
        assert events_resp.status_code == 200
        events = events_resp.json()
        assert events["session_id"] == session_id
        assert isinstance(events.get("events", []), list)
