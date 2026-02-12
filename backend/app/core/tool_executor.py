"""Tool executor for handling tool calls from the LLM."""

import logging
import re
from typing import Optional, Any
from dataclasses import dataclass

from app.models.session import ConversationSession
from app.core.config_types import ToolConfig
from app.core.template_renderer import get_template_renderer
from app.clients.service_client import ServiceClient, get_service_client
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
        tool: ToolConfig,
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
            # Check if service returned an error in the data
            if isinstance(result, dict) and "error" in result:
                error_msg = result.get("message", result.get("error", "Service error"))
                return ToolResult(success=False, data=result, error=error_msg)
            normalized = self._normalize_result_payload(tool.name, result)
            return ToolResult(success=True, data=normalized)
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
            normalized = self._normalize_result_payload(tool_name, result.data)
            return ToolResult(success=True, data=normalized)
        else:
            return ToolResult(
                success=False,
                data={"error": result.error_code or "SERVICE_ERROR", "message": result.error},
                error=result.error,
            )

    async def _call_service(
        self, tool: ToolConfig, params: dict, session: ConversationSession
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

    async def _call_api(self, tool: ToolConfig, params: dict) -> Any:
        """Call an external API (placeholder for future implementation)."""
        # For POC, return mock success
        logger.warning(f"API call for {tool.name} not implemented, returning mock success")
        return {"status": "success", "message": "Mock API response"}

    def _render_confirmation(
        self, tool: ToolConfig, params: dict, session: ConversationSession
    ) -> str:
        """Render the confirmation message template."""
        template = tool.confirmation_template or f"¿Confirmas ejecutar {tool.name}?"

        flow_data = session.current_flow.get("stateData", {}) if session.current_flow else {}
        render_data = {
            **flow_data,
            **params,
        }
        renderer = get_template_renderer()
        rendered = renderer.render(template, render_data)

        unresolved = renderer.find_unresolved_placeholders(rendered)
        if unresolved:
            logger.warning(
                "Confirmation template for tool %s has unresolved placeholders: %s",
                tool.name,
                sorted(set(unresolved)),
            )
        return rendered

    def _normalize_result_payload(self, tool_name: str, payload: Any) -> Any:
        """Normalize transactional payloads to deterministic fields."""
        if not isinstance(payload, dict):
            return payload

        normalized = dict(payload)
        status = str(normalized.get("status", "")).lower()
        if not status:
            status = "success"

        transaction_id = (
            normalized.get("transaction_id")
            or normalized.get("transactionId")
            or normalized.get("transfer_id")
            or normalized.get("transferId")
            or normalized.get("topupId")
            or normalized.get("paymentId")
            or normalized.get("loan_id")
        )
        reference = (
            normalized.get("reference")
            or normalized.get("confirmationNumber")
            or normalized.get("confirmation_number")
            or transaction_id
        )

        amount = (
            normalized.get("amount")
            or normalized.get("amount_usd")
            or normalized.get("amountUsd")
            or normalized.get("usdCharged")
            or normalized.get("totalUsd")
            or normalized.get("amountPaid")
        )
        currency = (
            normalized.get("currency")
            or normalized.get("localCurrency")
            or normalized.get("from_currency")
            or ("USD" if amount is not None else None)
        )
        timestamp = (
            normalized.get("timestamp")
            or normalized.get("processedAt")
            or normalized.get("created_at")
            or normalized.get("createdAt")
        )

        if transaction_id:
            normalized["transaction_id"] = transaction_id
        if reference:
            normalized["reference"] = reference
        if amount is not None:
            normalized["amount"] = amount
        if currency:
            normalized["currency"] = currency
        if timestamp:
            normalized["timestamp"] = timestamp
        normalized["status"] = status
        normalized["_tool_name"] = tool_name

        return normalized

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
