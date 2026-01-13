"""Integration tests for the Shadow Service Admin API."""

import pytest
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock


# ============================================================================
# Shadow Service Config API Tests
# ============================================================================

class TestShadowServiceConfigAPI:
    """Tests for the shadow service configuration endpoints."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_shadow_config(self, test_client):
        """Test GET /api/admin/shadow-service returns config."""
        mock_config = {
            "enabled": True,
            "global_cooldown_messages": 3,
            "max_messages_per_response": 1,
            "subagents": [
                {
                    "id": "test_advisor",
                    "enabled": True,
                    "relevance_threshold": 80,
                }
            ],
        }

        with patch("app.routes.admin.load_shadow_service_config", return_value=mock_config):
            response = await test_client.get("/api/admin/shadow-service")

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        assert data["global_cooldown_messages"] == 3
        assert "subagents" in data

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_update_shadow_config(self, test_client):
        """Test PUT /api/admin/shadow-service updates config."""
        update_data = {
            "enabled": False,
            "global_cooldown_messages": 5,
            "max_messages_per_response": 2,
        }

        current_config = {
            "enabled": True,
            "global_cooldown_messages": 3,
            "max_messages_per_response": 1,
            "subagents": [],
        }

        with patch("app.routes.admin.load_shadow_service_config", return_value=current_config):
            with patch("app.routes.admin.save_shadow_service_config") as mock_save:
                response = await test_client.put(
                    "/api/admin/shadow-service",
                    json=update_data,
                )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        # Verify updated values are reflected
        assert data["enabled"] is False
        assert data["global_cooldown_messages"] == 5
        mock_save.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_update_shadow_config_preserves_subagents(self, test_client):
        """Test PUT /api/admin/shadow-service preserves existing subagents."""
        update_data = {
            "enabled": False,
        }

        current_config = {
            "enabled": True,
            "global_cooldown_messages": 3,
            "max_messages_per_response": 1,
            "subagents": [{"id": "test_subagent", "enabled": True}],
        }

        with patch("app.routes.admin.load_shadow_service_config", return_value=current_config):
            with patch("app.routes.admin.save_shadow_service_config") as mock_save:
                response = await test_client.put(
                    "/api/admin/shadow-service",
                    json=update_data,
                )

        assert response.status_code == 200
        data = response.json()
        # Subagents should be preserved
        assert len(data["subagents"]) == 1
        assert data["subagents"][0]["id"] == "test_subagent"


# ============================================================================
# Shadow Subagent API Tests
# ============================================================================

class TestShadowSubagentAPI:
    """Tests for the shadow subagent CRUD endpoints."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_subagent(self, test_client):
        """Test GET /api/admin/shadow-service/subagents/:id returns subagent."""
        mock_subagent = {
            "id": "financial_advisor",
            "enabled": True,
            "relevance_threshold": 80,
            "priority": 1,
            "source_label": {"en": "Financial Advisor", "es": "Asesor Financiero"},
        }

        with patch("app.routes.admin.get_shadow_subagent_config", return_value=mock_subagent):
            response = await test_client.get(
                "/api/admin/shadow-service/subagents/financial_advisor"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "financial_advisor"
        assert data["enabled"] is True

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_subagent_not_found(self, test_client):
        """Test GET /api/admin/shadow-service/subagents/:id returns 404."""
        with patch("app.routes.admin.get_shadow_subagent_config", return_value=None):
            response = await test_client.get(
                "/api/admin/shadow-service/subagents/nonexistent"
            )

        assert response.status_code == 404

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_subagent(self, test_client):
        """Test POST /api/admin/shadow-service/subagents creates subagent."""
        new_subagent = {
            "id": "new_advisor",
            "enabled": True,
            "relevance_threshold": 75,
            "priority": 2,
            "model": "gpt-4o-mini",
            "temperature": 0.3,
            "cooldown_messages": 5,
            "max_tip_length": 280,
            "source_label": {"en": "New Advisor", "es": "Nuevo Asesor"},
            "tone": {"en": "friendly", "es": "amigable"},
            "system_prompt_addition": {"en": "Be helpful", "es": "Se util"},
            "activation_intents": ["help"],
        }

        with patch("app.routes.admin.add_shadow_subagent") as mock_add:
            response = await test_client.post(
                "/api/admin/shadow-service/subagents",
                json=new_subagent,
            )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["id"] == "new_advisor"
        mock_add.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_subagent_missing_id(self, test_client):
        """Test POST /api/admin/shadow-service/subagents requires id."""
        response = await test_client.post(
            "/api/admin/shadow-service/subagents",
            json={"enabled": True},
        )

        assert response.status_code == 400

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_subagent_duplicate_id(self, test_client):
        """Test POST /api/admin/shadow-service/subagents rejects duplicate id."""
        with patch("app.routes.admin.add_shadow_subagent") as mock_add:
            mock_add.side_effect = ValueError("Subagent with id already exists")
            response = await test_client.post(
                "/api/admin/shadow-service/subagents",
                json={"id": "existing"},
            )

        assert response.status_code == 400

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_update_subagent(self, test_client):
        """Test PUT /api/admin/shadow-service/subagents/:id updates subagent."""
        update_data = {
            "id": "financial_advisor",
            "enabled": False,
            "relevance_threshold": 90,
            "priority": 2,
        }

        updated_subagent = {**update_data, "source_label": {"en": "Financial Advisor"}}

        with patch("app.routes.admin.update_shadow_subagent_config", return_value=True):
            with patch("app.routes.admin.get_shadow_subagent_config", return_value=updated_subagent):
                response = await test_client.put(
                    "/api/admin/shadow-service/subagents/financial_advisor",
                    json=update_data,
                )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["id"] == "financial_advisor"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_update_subagent_not_found(self, test_client):
        """Test PUT /api/admin/shadow-service/subagents/:id returns 404."""
        with patch("app.routes.admin.update_shadow_subagent_config", return_value=False):
            response = await test_client.put(
                "/api/admin/shadow-service/subagents/nonexistent",
                json={"id": "nonexistent", "enabled": True},
            )

        assert response.status_code == 404

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_delete_subagent(self, test_client):
        """Test DELETE /api/admin/shadow-service/subagents/:id deletes subagent."""
        with patch("app.routes.admin.delete_shadow_subagent", return_value=True):
            response = await test_client.delete(
                "/api/admin/shadow-service/subagents/financial_advisor"
            )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_delete_subagent_not_found(self, test_client):
        """Test DELETE /api/admin/shadow-service/subagents/:id returns 404."""
        with patch("app.routes.admin.delete_shadow_subagent", return_value=False):
            response = await test_client.delete(
                "/api/admin/shadow-service/subagents/nonexistent"
            )

        assert response.status_code == 404


# ============================================================================
# Chat API with Shadow Service Tests
# ============================================================================

class TestChatWithShadowService:
    """Tests for chat API responses including shadow service."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_response_includes_shadow_messages_field(
        self, test_client, sample_agent
    ):
        """Test chat response includes shadow_messages field."""
        response = await test_client.post(
            "/api/chat/message",
            json={
                "user_id": "test_user",
                "message": "Hello",
            },
        )

        assert response.status_code == 200
        data = response.json()
        # The response should include shadow_messages (may be empty list)
        assert "shadow_messages" in data
        assert isinstance(data["shadow_messages"], list)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_shadow_messages_format(self, test_client, sample_agent):
        """Test that shadow messages field is always a list."""
        # Send multiple messages to ensure consistent behavior
        for _ in range(3):
            response = await test_client.post(
                "/api/chat/message",
                json={
                    "user_id": "test_user",
                    "message": "I want to send money to Mexico",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data.get("shadow_messages", []), list)
