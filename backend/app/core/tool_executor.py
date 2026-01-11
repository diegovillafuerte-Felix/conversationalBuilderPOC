"""Tool executor for handling tool calls from the LLM."""

import logging
import re
from typing import Optional, Any
from dataclasses import dataclass

from app.models.agent import Tool
from app.models.session import ConversationSession
from app.services import remittances, credit, wallet, topups, billpay

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Result of a tool execution."""

    success: bool
    data: Any
    error: Optional[str] = None
    requires_confirmation: bool = False
    confirmation_message: Optional[str] = None


class ToolExecutor:
    """Executes tools and manages confirmations."""

    def __init__(self, language: str = "es"):
        self._language = language
        # Map service names to service instances
        self.services = {
            "remittances": remittances.MockRemittancesService(language=language),
            "credit": credit.MockCreditService(language=language),
            "wallet": wallet.MockWalletService(language=language),
            "topups": topups.MockTopUpsService(language=language),
            "billpay": billpay.MockBillPayService(language=language),
        }

    def set_language(self, language: str) -> None:
        """Update language for all services."""
        self._language = language
        for service in self.services.values():
            if hasattr(service, 'language'):
                service.language = language

    async def execute(
        self,
        tool: Tool,
        params: dict,
        session: ConversationSession,
        skip_confirmation: bool = False,
    ) -> ToolResult:
        """
        Execute a tool call.

        Args:
            tool: The tool definition
            params: Parameters for the tool
            session: Current conversation session
            skip_confirmation: If True, skip confirmation even if tool requires it

        Returns:
            ToolResult with success/failure and data
        """
        # Check if tool requires confirmation
        if tool.requires_confirmation and not skip_confirmation:
            confirmation_message = self._render_confirmation(tool, params, session)
            return ToolResult(
                success=True,
                data=None,
                requires_confirmation=True,
                confirmation_message=confirmation_message,
            )

        # Execute the tool
        try:
            result = await self._call_service(tool, params, session)
            return ToolResult(success=True, data=result)
        except Exception as e:
            logger.error(f"Tool execution failed: {tool.name} - {e}")
            return ToolResult(success=False, data=None, error=str(e))

    async def execute_mock(
        self, tool_name: str, params: dict, user_id: str
    ) -> ToolResult:
        """Execute a mock tool directly by name (for internal navigation tools)."""
        # Handle navigation tools
        if tool_name in ["up_one_level", "go_home", "escalate_to_human"]:
            return ToolResult(success=True, data={"action": tool_name})

        # Handle agent entry tools
        if tool_name.startswith("enter_"):
            agent_name = tool_name.replace("enter_", "")
            return ToolResult(success=True, data={"action": "enter_agent", "agent": agent_name})

        # Handle flow start tools
        if tool_name.startswith("start_flow_"):
            flow_name = tool_name.replace("start_flow_", "")
            return ToolResult(success=True, data={"action": "start_flow", "flow": flow_name})

        # Try to find the appropriate service
        for service_name, service in self.services.items():
            if hasattr(service, tool_name):
                method = getattr(service, tool_name)
                # Add user_id to params if needed
                if "user_id" in method.__code__.co_varnames:
                    params["user_id"] = user_id
                result = method(**params)
                return ToolResult(success=True, data=result)

        return ToolResult(
            success=False,
            data=None,
            error=f"Unknown tool: {tool_name}",
        )

    async def _call_service(
        self, tool: Tool, params: dict, session: ConversationSession
    ) -> Any:
        """Call the appropriate service method for a tool."""
        # For POC, we route based on tool name patterns
        tool_name = tool.name

        # Add user_id to params
        params["user_id"] = session.user_id

        # Route to appropriate service
        for service_name, service in self.services.items():
            if hasattr(service, tool_name):
                method = getattr(service, tool_name)
                # Filter params to only those the method accepts
                import inspect
                sig = inspect.signature(method)
                valid_params = {
                    k: v for k, v in params.items()
                    if k in sig.parameters
                }
                return method(**valid_params)

        # If no service method found, check API config
        if tool.api_config:
            return await self._call_api(tool, params)

        raise ValueError(f"No handler found for tool: {tool_name}")

    async def _call_api(self, tool: Tool, params: dict) -> Any:
        """Call an external API (placeholder for future implementation)."""
        # For POC, return mock success
        logger.warning(f"API call for {tool.name} not implemented, returning mock success")
        return {"status": "success", "message": "Mock API response"}

    def _render_confirmation(
        self, tool: Tool, params: dict, session: ConversationSession
    ) -> str:
        """Render the confirmation message template."""
        template = tool.confirmation_template or f"¿Confirmas ejecutar {tool.name}?"

        # Simple template rendering with {{placeholder}} syntax
        def replace_placeholder(match):
            key = match.group(1)
            # Check params first
            if key in params:
                return str(params[key])
            # Check flow data
            if session.current_flow and key in session.current_flow.get("stateData", {}):
                return str(session.current_flow["stateData"][key])
            return f"{{{{{key}}}}}"  # Return original if not found

        rendered = re.sub(r"\{\{(\w+)\}\}", replace_placeholder, template)
        return rendered

    def classify_user_confirmation(self, message: str) -> Optional[bool]:
        """
        Classify if a user message is a confirmation or denial.

        Returns:
            True if confirmed, False if denied, None if unclear
        """
        message_lower = message.lower().strip()

        # Positive confirmations
        positive_patterns = [
            r"^s[íi]$",
            r"^si$",
            r"^yes$",
            r"^confirmo$",
            r"^confirmar$",
            r"^dale$",
            r"^ok$",
            r"^okay$",
            r"^hazlo$",
            r"^adelante$",
            r"^procede$",
            r"^claro$",
            r"^por supuesto$",
            r"^está bien$",
            r"^esta bien$",
        ]

        # Negative denials
        negative_patterns = [
            r"^no$",
            r"^nop$",
            r"^nope$",
            r"^cancel",
            r"^cancela",
            r"^no quiero$",
            r"^mejor no$",
            r"^dejalo$",
            r"^déjalo$",
            r"^olvidalo$",
            r"^olvídalo$",
        ]

        for pattern in positive_patterns:
            if re.match(pattern, message_lower):
                return True

        for pattern in negative_patterns:
            if re.match(pattern, message_lower):
                return False

        return None


# Global executor instance
_tool_executor: Optional[ToolExecutor] = None


def get_tool_executor() -> ToolExecutor:
    """Get or create the tool executor singleton."""
    global _tool_executor
    if _tool_executor is None:
        _tool_executor = ToolExecutor()
    return _tool_executor
