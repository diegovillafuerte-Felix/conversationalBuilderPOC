"""Tool executor for handling tool calls from the LLM."""

import logging
import re
from typing import Optional, Any
from dataclasses import dataclass

from app.models.agent import Tool
from app.models.session import ConversationSession
from app.clients.service_client import ServiceClient, ServiceResult, get_service_client
from app.clients.service_mapping import SERVICE_MAPPING

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
    """Executes tools via HTTP calls to services gateway."""

    def __init__(self, language: str = "es"):
        self._language = language
        self._client: ServiceClient = get_service_client()

    def set_language(self, language: str) -> None:
        """Update language for service calls."""
        self._language = language

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
        """Execute a tool directly by name via HTTP (for service tools without DB definition)."""
        # Note: Navigation, agent entry, and flow start tools are now handled by RoutingHandler.
        # This method is only for service tools that don't have a Tool record in the database.

        # Get endpoint mapping
        mapping = SERVICE_MAPPING.get(tool_name)
        if not mapping:
            return ToolResult(
                success=False,
                data=None,
                error=f"Unknown tool: {tool_name}",
            )

        method, endpoint_template = mapping

        # Substitute path parameters
        endpoint = endpoint_template
        path_params = set()
        for key, value in list(params.items()):
            placeholder = f"{{{key}}}"
            if placeholder in endpoint:
                endpoint = endpoint.replace(placeholder, str(value))
                path_params.add(key)

        # Remove path params from body/query params
        query_params = {k: v for k, v in params.items() if k not in path_params}

        # Make the HTTP call
        if method == "GET":
            result = await self._client.call_service(
                method=method,
                endpoint=endpoint,
                params=query_params,
                user_id=user_id,
                language=self._language,
            )
        else:
            result = await self._client.call_service(
                method=method,
                endpoint=endpoint,
                json_body=query_params,
                user_id=user_id,
                language=self._language,
            )

        if result.success:
            return ToolResult(success=True, data=result.data)
        else:
            return ToolResult(
                success=False,
                data={"error": result.error_code or "SERVICE_ERROR", "message": result.error},
                error=result.error,
            )

    async def _call_service(
        self, tool: Tool, params: dict, session: ConversationSession
    ) -> Any:
        """Call the service via HTTP with validation."""
        tool_name = tool.name

        # VALIDATE PARAMETERS against tool definition
        if tool.parameters:
            try:
                validated_params = self._validate_params(params, tool.parameters)
                params = validated_params
            except ValueError as e:
                logger.error(f"Parameter validation failed for {tool_name}: {e}")
                return {"error": "INVALID_PARAMETERS", "details": str(e)}

        # Sanitize string parameters
        params = self._sanitize_params(params)

        # Validate user_id
        if not session.user_id or not isinstance(session.user_id, str):
            raise ValueError("Invalid user_id in session")

        # Get endpoint mapping
        mapping = SERVICE_MAPPING.get(tool_name)
        if not mapping:
            # If no service method found, check API config
            if tool.api_config:
                return await self._call_api(tool, params)
            raise ValueError(f"No handler found for tool: {tool_name}")

        method, endpoint_template = mapping

        # Substitute path parameters
        endpoint = endpoint_template
        path_params = set()
        for key, value in list(params.items()):
            placeholder = f"{{{key}}}"
            if placeholder in endpoint:
                endpoint = endpoint.replace(placeholder, str(value))
                path_params.add(key)

        # Remove path params from body/query params
        query_params = {k: v for k, v in params.items() if k not in path_params}

        # Make the HTTP call
        if method == "GET":
            result = await self._client.call_service(
                method=method,
                endpoint=endpoint,
                params=query_params,
                user_id=session.user_id,
                language=self._language,
            )
        else:
            result = await self._client.call_service(
                method=method,
                endpoint=endpoint,
                json_body=query_params,
                user_id=session.user_id,
                language=self._language,
            )

        if result.success:
            return result.data
        else:
            return {"error": result.error_code or "SERVICE_ERROR", "message": result.error}

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

    def _validate_params(self, params: dict, schema: list) -> dict:
        """
        Validate parameters against tool schema.

        Args:
            params: Parameters provided by LLM
            schema: Tool parameter schema (list of dicts with name, type, required, etc.)

        Returns:
            Validated and coerced parameters

        Raises:
            ValueError: If validation fails
        """
        validated = {}

        for param_def in schema:
            name = param_def.get("name")
            if not name:
                continue

            required = param_def.get("required", False)
            param_type = param_def.get("type", "string")

            # Check required parameters
            if required and name not in params:
                raise ValueError(f"Missing required parameter: {name}")

            # Validate and coerce if present
            if name in params:
                try:
                    validated[name] = self._coerce_type(params[name], param_type)
                except (ValueError, TypeError) as e:
                    raise ValueError(f"Invalid type for parameter '{name}': {e}")

        return validated

    def _coerce_type(self, value: Any, expected_type: str) -> Any:
        """
        Coerce value to expected type with validation.

        Args:
            value: The value to coerce
            expected_type: Expected type as string (string, number, integer, boolean, object, array)

        Returns:
            Coerced value

        Raises:
            ValueError: If coercion fails
        """
        # Type mapping
        type_map = {
            "string": str,
            "number": float,
            "integer": int,
            "boolean": bool,
            "object": dict,
            "array": list,
        }

        if expected_type not in type_map:
            # Unknown type, return as-is
            return value

        # Handle null/None
        if value is None:
            return None

        try:
            # Special handling for numbers
            if expected_type == "number":
                if isinstance(value, (int, float)):
                    return float(value)
                return float(value)

            # Special handling for integers
            if expected_type == "integer":
                if isinstance(value, bool):
                    raise ValueError("Cannot coerce boolean to integer")
                if isinstance(value, (int, float)):
                    return int(value)
                return int(float(value))

            # Special handling for booleans
            if expected_type == "boolean":
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    lower = value.lower()
                    if lower in ("true", "1", "yes", "y"):
                        return True
                    if lower in ("false", "0", "no", "n"):
                        return False
                    raise ValueError(f"Cannot coerce string '{value}' to boolean")
                return bool(value)

            # For object and array, validate type
            if expected_type == "object" and not isinstance(value, dict):
                raise ValueError(f"Expected object, got {type(value).__name__}")

            if expected_type == "array" and not isinstance(value, list):
                raise ValueError(f"Expected array, got {type(value).__name__}")

            # Default coercion
            return type_map[expected_type](value)

        except (ValueError, TypeError) as e:
            raise ValueError(f"Cannot coerce {value} to {expected_type}: {e}")

    def _sanitize_params(self, params: dict) -> dict:
        """
        Sanitize string parameters to prevent injection attacks.

        Args:
            params: Parameters to sanitize

        Returns:
            Sanitized parameters
        """
        sanitized = {}

        for key, value in params.items():
            if isinstance(value, str):
                # Remove null bytes (can cause issues with C libraries)
                value = value.replace('\x00', '')

                # Remove other control characters except newlines and tabs
                value = ''.join(char for char in value if char.isprintable() or char in '\n\t')

                # Strip excessive whitespace
                value = value.strip()

                # Limit string length to prevent DOS
                max_length = 10000
                if len(value) > max_length:
                    logger.warning(f"Truncating parameter '{key}' from {len(value)} to {max_length} chars")
                    value = value[:max_length]

            elif isinstance(value, dict):
                # Recursively sanitize nested dicts
                value = self._sanitize_params(value)

            elif isinstance(value, list):
                # Sanitize lists
                value = [
                    self._sanitize_params(item) if isinstance(item, dict)
                    else item.replace('\x00', '') if isinstance(item, str)
                    else item
                    for item in value
                ]

            sanitized[key] = value

        return sanitized


# Global executor instance
_tool_executor: Optional[ToolExecutor] = None


def get_tool_executor() -> ToolExecutor:
    """Get or create the tool executor singleton."""
    global _tool_executor
    if _tool_executor is None:
        _tool_executor = ToolExecutor()
    return _tool_executor
