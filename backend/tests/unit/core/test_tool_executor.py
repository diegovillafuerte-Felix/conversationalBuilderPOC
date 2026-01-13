"""Unit tests for the ToolExecutor."""

import pytest
from uuid import uuid4

from app.core.tool_executor import ToolExecutor, ToolResult
from app.models.agent import Tool
from app.models.session import ConversationSession


class TestToolExecutorConfirmation:
    """Test cases for user confirmation classification."""

    def test_classify_positive_confirmations(self):
        """Test positive confirmation classification."""
        executor = ToolExecutor()

        positive_messages = [
            "Sí",
            "si",
            "SÍ",
            "SI",
            "yes",
            "YES",
            "ok",
            "OK",
            "okay",
            "dale",
            "confirmo",
            "confirmar",
            "hazlo",
            "adelante",
            "procede",
            "claro",
            "por supuesto",
            "está bien",
            "esta bien",
        ]

        for msg in positive_messages:
            result = executor.classify_user_confirmation(msg)
            assert result is True, f"Expected True for '{msg}', got {result}"

    def test_classify_negative_confirmations(self):
        """Test negative confirmation classification."""
        executor = ToolExecutor()

        negative_messages = [
            "no",
            "No",
            "NO",
            "nop",
            "nope",
            "cancelar",
            "cancela",
            "cancel",
            "no quiero",
            "mejor no",
            "dejalo",
            "déjalo",
            "olvidalo",
            "olvídalo",
        ]

        for msg in negative_messages:
            result = executor.classify_user_confirmation(msg)
            assert result is False, f"Expected False for '{msg}', got {result}"

    def test_classify_unclear_confirmations(self):
        """Test unclear confirmation classification."""
        executor = ToolExecutor()

        unclear_messages = [
            "maybe",
            "quizás",
            "let me think",
            "cuánto cuesta",
            "¿qué incluye?",
            "hola",
            "quiero información",
        ]

        for msg in unclear_messages:
            result = executor.classify_user_confirmation(msg)
            assert result is None, f"Expected None for '{msg}', got {result}"


class TestToolExecutorMockExecution:
    """Test cases for mock tool execution.

    Note: Routing tools (navigation, enter_agent, start_flow) are now handled
    by RoutingHandler, not execute_mock. These tests only cover service tools.
    """

    @pytest.mark.asyncio
    async def test_execute_mock_unknown_tool(self):
        """Test mock execution of unknown tool returns error."""
        executor = ToolExecutor()

        result = await executor.execute_mock("unknown_tool_xyz", {}, "user_123")

        assert result.success is False
        assert "Unknown tool" in result.error

    @pytest.mark.asyncio
    async def test_execute_mock_routing_tools_now_fail(self):
        """Test that routing tools now fail in execute_mock (handled by RoutingHandler)."""
        executor = ToolExecutor()

        # These tools are now handled by RoutingHandler, not execute_mock
        routing_tools = [
            "go_home",
            "up_one_level",
            "escalate_to_human",
            "enter_topups",
            "start_flow_recarga",
        ]

        for tool_name in routing_tools:
            result = await executor.execute_mock(tool_name, {}, "user_123")
            # Should fail because routing is handled elsewhere
            assert result.success is False, f"{tool_name} should not be handled by execute_mock"


class TestToolExecutorWithTool:
    """Test cases for tool execution with Tool model."""

    @pytest.mark.asyncio
    async def test_execute_requires_confirmation(self):
        """Test tool execution when confirmation is required."""
        executor = ToolExecutor()

        tool = Tool(
            id=uuid4(),
            agent_id=uuid4(),
            name="send_topup",
            description="Send a topup",
            parameters=[],
            requires_confirmation=True,
            confirmation_template="Confirm sending topup of {{amount}} to {{phone_number}}?",
        )

        session = ConversationSession(user_id="test_user")
        session.agent_stack = [{"agentId": str(uuid4())}]

        result = await executor.execute(
            tool=tool,
            params={"amount": 100, "phone_number": "+52 55 1234 5678"},
            session=session,
        )

        assert result.success is True
        assert result.requires_confirmation is True
        assert "100" in result.confirmation_message
        assert "+52 55 1234 5678" in result.confirmation_message

    @pytest.mark.asyncio
    async def test_execute_skip_confirmation(self):
        """Test tool execution with skip_confirmation flag."""
        executor = ToolExecutor()

        tool = Tool(
            id=uuid4(),
            agent_id=uuid4(),
            name="get_carriers",
            description="Get available carriers",
            parameters=[],
            requires_confirmation=True,
            confirmation_template="Confirm?",
        )

        session = ConversationSession(user_id="test_user")
        session.agent_stack = [{"agentId": str(uuid4())}]

        result = await executor.execute(
            tool=tool,
            params={"country": "MX"},
            session=session,
            skip_confirmation=True,
        )

        # Should not require confirmation when skip_confirmation is True
        assert result.requires_confirmation is False


class TestToolExecutorLanguage:
    """Test cases for language handling."""

    def test_language_initialization(self):
        """Test that executor initializes with correct language."""
        executor_es = ToolExecutor(language="es")
        executor_en = ToolExecutor(language="en")

        assert executor_es._language == "es"
        assert executor_en._language == "en"

    def test_set_language(self):
        """Test setting language updates services."""
        executor = ToolExecutor(language="es")

        executor.set_language("en")

        assert executor._language == "en"


class TestToolExecutorServices:
    """Test cases for service method routing."""

    @pytest.mark.asyncio
    async def test_execute_mock_topups_get_carriers(self):
        """Test that topups service methods are accessible."""
        executor = ToolExecutor()

        result = await executor.execute_mock(
            "get_carriers", {"country": "MX"}, "user_123"
        )

        assert result.success is True
        assert "carriers" in result.data

    @pytest.mark.asyncio
    async def test_execute_mock_topups_detect_carrier(self):
        """Test carrier detection through mock execution."""
        executor = ToolExecutor()

        result = await executor.execute_mock(
            "detect_carrier", {"phone_number": "+52 55 1234 5678"}, "user_123"
        )

        assert result.success is True
        assert "carrier" in result.data
        assert result.data["valid"] is True

    @pytest.mark.asyncio
    async def test_execute_mock_wallet_get_balance(self):
        """Test wallet balance through mock execution."""
        executor = ToolExecutor()

        result = await executor.execute_mock("get_balance", {}, "user_demo")

        assert result.success is True
        # Balance should be returned (structure may vary)
