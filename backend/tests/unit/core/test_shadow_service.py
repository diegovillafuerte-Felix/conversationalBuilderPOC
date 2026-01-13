"""Unit tests for the Shadow Service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.core.shadow_service import (
    ShadowService,
    ShadowServiceConfig,
    SubagentConfig,
    ShadowResult,
    SubagentResult,
    ShadowMessage,
    Activation,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_subagent_config():
    """Sample subagent configuration for testing."""
    return {
        "id": "test_advisor",
        "enabled": True,
        "relevance_threshold": 80,
        "model": "gpt-4o-mini",
        "temperature": 0.3,
        "priority": 1,
        "full_agent_id": "test_full_agent",
        "tone": {"en": "friendly", "es": "amigable"},
        "system_prompt_addition": {"en": "Be helpful", "es": "Se util"},
        "activation_intents": ["help_intent", "advice_intent"],
        "max_tip_length": 200,
        "cooldown_messages": 3,
        "source_label": {"en": "Test Advisor", "es": "Asesor de Prueba"},
    }


@pytest.fixture
def sample_service_config(sample_subagent_config):
    """Sample shadow service configuration."""
    return {
        "enabled": True,
        "global_cooldown_messages": 2,
        "max_messages_per_response": 1,
        "subagents": [sample_subagent_config],
    }


@pytest.fixture
def mock_session():
    """Mock conversation session."""
    session = MagicMock()
    session.metadata = {"message_count": 10}
    return session


@pytest.fixture
def mock_user_context():
    """Mock user context."""
    context = MagicMock()
    context.profile = {"name": "Test User", "language": "en"}
    return context


@pytest.fixture
def mock_llm_client():
    """Mock LLM client."""
    return MagicMock()


# ============================================================================
# ShadowServiceConfig Tests
# ============================================================================

class TestShadowServiceConfig:
    """Tests for ShadowServiceConfig dataclass."""

    def test_from_dict_with_defaults(self):
        """Test config creation with defaults when fields missing."""
        config = ShadowServiceConfig.from_dict({})

        assert config.enabled is True
        assert config.global_cooldown_messages == 3
        assert config.max_messages_per_response == 1
        assert config.subagents == []

    def test_from_dict_parses_subagents(self, sample_subagent_config):
        """Test config parses subagents list."""
        config = ShadowServiceConfig.from_dict({
            "enabled": False,
            "global_cooldown_messages": 5,
            "max_messages_per_response": 2,
            "subagents": [sample_subagent_config],
        })

        assert config.enabled is False
        assert config.global_cooldown_messages == 5
        assert config.max_messages_per_response == 2
        assert len(config.subagents) == 1
        assert config.subagents[0].id == "test_advisor"

    def test_subagent_config_from_dict(self, sample_subagent_config):
        """Test SubagentConfig creation from dict."""
        config = SubagentConfig.from_dict(sample_subagent_config)

        assert config.id == "test_advisor"
        assert config.enabled is True
        assert config.relevance_threshold == 80
        assert config.priority == 1
        assert config.full_agent_id == "test_full_agent"
        assert config.activation_intents == ["help_intent", "advice_intent"]
        assert config.source_label["en"] == "Test Advisor"


# ============================================================================
# SubagentResult Tests
# ============================================================================

class TestSubagentResult:
    """Tests for SubagentResult dataclass."""

    def test_has_message_true(self):
        """Test has_message returns True when message exists."""
        result = SubagentResult(
            subagent_id="test",
            relevance_score=90,
            message="Here's a helpful tip!",
        )
        assert result.has_message is True

    def test_has_message_false_when_none(self):
        """Test has_message returns False when message is None."""
        result = SubagentResult(
            subagent_id="test",
            relevance_score=90,
            message=None,
        )
        assert result.has_message is False

    def test_has_message_false_when_empty(self):
        """Test has_message returns False when message is empty."""
        result = SubagentResult(
            subagent_id="test",
            relevance_score=90,
            message="   ",
        )
        assert result.has_message is False


# ============================================================================
# ShadowResult Tests
# ============================================================================

class TestShadowResult:
    """Tests for ShadowResult dataclass."""

    def test_has_messages_true(self):
        """Test has_messages returns True when messages exist."""
        result = ShadowResult(
            messages=[ShadowMessage(
                content="Test",
                source="Test",
                subagent_id="test",
            )],
        )
        assert result.has_messages is True

    def test_has_messages_false(self):
        """Test has_messages returns False when empty."""
        result = ShadowResult()
        assert result.has_messages is False

    def test_has_activation_true(self):
        """Test has_activation returns True when activation exists."""
        result = ShadowResult(
            activation=Activation(
                target_agent_id="agent_1",
                subagent_id="test",
                intent="help",
            ),
        )
        assert result.has_activation is True

    def test_has_activation_false(self):
        """Test has_activation returns False when no activation."""
        result = ShadowResult()
        assert result.has_activation is False


# ============================================================================
# ShadowService Tests
# ============================================================================

class TestShadowService:
    """Tests for the ShadowService class."""

    @pytest.mark.asyncio
    async def test_evaluate_returns_empty_when_disabled(
        self, mock_llm_client, mock_session, mock_user_context
    ):
        """Test evaluate returns empty result when service is disabled."""
        config = ShadowServiceConfig.from_dict({"enabled": False})
        service = ShadowService(mock_llm_client, config)

        result = await service.evaluate(
            user_message="Hello",
            session=mock_session,
            user_context=mock_user_context,
            recent_messages=[],
            language="en",
        )

        assert result.has_messages is False
        assert result.has_activation is False

    @pytest.mark.asyncio
    async def test_evaluate_respects_global_cooldown(
        self, mock_llm_client, sample_service_config, mock_user_context
    ):
        """Test evaluate returns empty result during global cooldown."""
        config = ShadowServiceConfig.from_dict(sample_service_config)
        service = ShadowService(mock_llm_client, config)

        # Create session that's in cooldown (last message at count 9, current at 10)
        session = MagicMock()
        session.metadata = {
            "message_count": 10,
            "shadow_service": {
                "last_global_message_count": 9,  # Only 1 message since last shadow
            },
        }

        result = await service.evaluate(
            user_message="Hello",
            session=session,
            user_context=mock_user_context,
            recent_messages=[],
            language="en",
        )

        assert result.has_messages is False

    def test_is_in_global_cooldown_true(self, mock_llm_client, sample_service_config):
        """Test global cooldown detection."""
        config = ShadowServiceConfig.from_dict(sample_service_config)
        service = ShadowService(mock_llm_client, config)

        session = MagicMock()
        session.metadata = {
            "message_count": 5,
            "shadow_service": {"last_global_message_count": 4},
        }

        # Cooldown is 2, only 1 message since last = in cooldown
        assert service._is_in_global_cooldown(session) is True

    def test_is_in_global_cooldown_false(self, mock_llm_client, sample_service_config):
        """Test global cooldown expired."""
        config = ShadowServiceConfig.from_dict(sample_service_config)
        service = ShadowService(mock_llm_client, config)

        session = MagicMock()
        session.metadata = {
            "message_count": 10,
            "shadow_service": {"last_global_message_count": 5},
        }

        # Cooldown is 2, 5 messages since last = not in cooldown
        assert service._is_in_global_cooldown(session) is False

    def test_update_cooldowns(self, mock_llm_client, sample_service_config):
        """Test cooldown counters are updated correctly."""
        config = ShadowServiceConfig.from_dict(sample_service_config)
        service = ShadowService(mock_llm_client, config)

        session = MagicMock()
        session.metadata = {"message_count": 15}

        service.update_cooldowns(session, ["test_advisor"])

        assert session.metadata["shadow_service"]["last_global_message_count"] == 15
        assert session.metadata["shadow_service"]["subagent_cooldowns"]["test_advisor"] == 15


class TestShadowServiceAggregation:
    """Tests for result aggregation logic."""

    def test_aggregate_empty_results(self, mock_llm_client, sample_service_config):
        """Test aggregation with empty results."""
        config = ShadowServiceConfig.from_dict(sample_service_config)
        service = ShadowService(mock_llm_client, config)

        session = MagicMock()
        result = service._aggregate_results([], session, "en")

        assert result.has_messages is False
        assert result.has_activation is False

    def test_aggregate_returns_activation_when_detected(
        self, mock_llm_client, sample_service_config
    ):
        """Test aggregation returns activation when subagent detects it."""
        config = ShadowServiceConfig.from_dict(sample_service_config)
        service = ShadowService(mock_llm_client, config)

        # Create a mock subagent that would be in _subagents
        mock_subagent = MagicMock()
        mock_subagent.config = config.subagents[0]
        service._subagents["test_advisor"] = mock_subagent

        results = [
            SubagentResult(
                subagent_id="test_advisor",
                relevance_score=95,
                message="Here's some advice",
                activation_detected=True,
                activation_intent="help_intent",
            )
        ]

        session = MagicMock()
        aggregated = service._aggregate_results(results, session, "en")

        assert aggregated.has_activation is True
        assert aggregated.activation.target_agent_id == "test_full_agent"
        assert aggregated.activation.intent == "help_intent"

    def test_aggregate_filters_below_threshold(
        self, mock_llm_client, sample_service_config
    ):
        """Test aggregation filters messages below threshold."""
        config = ShadowServiceConfig.from_dict(sample_service_config)
        service = ShadowService(mock_llm_client, config)

        mock_subagent = MagicMock()
        mock_subagent.config = config.subagents[0]  # threshold = 80
        service._subagents["test_advisor"] = mock_subagent

        results = [
            SubagentResult(
                subagent_id="test_advisor",
                relevance_score=70,  # Below 80 threshold
                message="Low relevance tip",
            )
        ]

        session = MagicMock()
        aggregated = service._aggregate_results(results, session, "en")

        assert aggregated.has_messages is False

    def test_aggregate_includes_above_threshold(
        self, mock_llm_client, sample_service_config
    ):
        """Test aggregation includes messages above threshold."""
        config = ShadowServiceConfig.from_dict(sample_service_config)
        service = ShadowService(mock_llm_client, config)

        mock_subagent = MagicMock()
        mock_subagent.config = config.subagents[0]  # threshold = 80
        service._subagents["test_advisor"] = mock_subagent

        results = [
            SubagentResult(
                subagent_id="test_advisor",
                relevance_score=90,  # Above 80 threshold
                message="High relevance tip",
            )
        ]

        session = MagicMock()
        aggregated = service._aggregate_results(results, session, "en")

        assert aggregated.has_messages is True
        assert len(aggregated.messages) == 1
        assert aggregated.messages[0].content == "High relevance tip"
        assert aggregated.messages[0].source == "Test Advisor"

    def test_aggregate_respects_max_messages(self, mock_llm_client):
        """Test aggregation respects max_messages_per_response."""
        config_dict = {
            "enabled": True,
            "global_cooldown_messages": 1,
            "max_messages_per_response": 1,  # Only 1 message allowed
            "subagents": [
                {
                    "id": "advisor1",
                    "enabled": True,
                    "relevance_threshold": 50,
                    "priority": 1,
                    "max_tip_length": 200,
                    "cooldown_messages": 1,
                    "source_label": {"en": "Advisor 1"},
                    "tone": {},
                    "system_prompt_addition": {},
                    "activation_intents": [],
                },
                {
                    "id": "advisor2",
                    "enabled": True,
                    "relevance_threshold": 50,
                    "priority": 2,
                    "max_tip_length": 200,
                    "cooldown_messages": 1,
                    "source_label": {"en": "Advisor 2"},
                    "tone": {},
                    "system_prompt_addition": {},
                    "activation_intents": [],
                },
            ],
        }
        config = ShadowServiceConfig.from_dict(config_dict)
        service = ShadowService(mock_llm_client, config)

        # Mock subagents
        for subagent_config in config.subagents:
            mock_subagent = MagicMock()
            mock_subagent.config = subagent_config
            service._subagents[subagent_config.id] = mock_subagent

        results = [
            SubagentResult(subagent_id="advisor1", relevance_score=90, message="Tip 1"),
            SubagentResult(subagent_id="advisor2", relevance_score=90, message="Tip 2"),
        ]

        session = MagicMock()
        aggregated = service._aggregate_results(results, session, "en")

        # Should only have 1 message due to max_messages_per_response
        assert len(aggregated.messages) == 1
        # Should be advisor1 due to higher priority (lower number)
        assert aggregated.messages[0].source == "Advisor 1"
