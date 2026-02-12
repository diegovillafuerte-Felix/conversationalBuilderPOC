"""Template renderer for response templates."""

import re
import logging
from typing import Optional, List
from app.core.config_types import ResponseTemplateConfig

logger = logging.getLogger(__name__)


class TemplateRenderer:
    """Renders templates with variable substitution."""

    def render(self, template: str, data: dict) -> str:
        """
        Render a template with data substitution.

        Supports `{{variable}}`, `{variable}`, and `${variable}` placeholder syntax.
        """
        rendered = template

        # Replace most explicit form first to avoid overlaps.
        rendered = self._replace_placeholders(
            rendered,
            r"\{\{(\w+(?:\.\w+)*)\}\}",
            "{{{{{key}}}}}",
            data,
        )
        rendered = self._replace_placeholders(
            rendered,
            r"\$\{(\w+(?:\.\w+)*)\}",
            "${{{key}}}",
            data,
        )
        rendered = self._replace_placeholders(
            rendered,
            r"(?<!\{)\{(\w+(?:\.\w+)*)\}(?!\})",
            "{{{key}}}",
            data,
        )

        # Strip any remaining unresolved placeholders so users don't see raw {var} text
        rendered = re.sub(r"\{\{(\w+(?:\.\w+)*)\}\}", "", rendered)
        rendered = re.sub(r"\$\{(\w+(?:\.\w+)*)\}", "", rendered)
        rendered = re.sub(r"(?<!\{)\{(\w+(?:\.\w+)*)\}(?!\})", "", rendered)

        return rendered

    def _replace_placeholders(
        self,
        template: str,
        pattern: str,
        missing_format: str,
        data: dict,
    ) -> str:
        """Replace placeholders matching a pattern."""

        def replace_placeholder(match):
            key = match.group(1)
            value, found = self._resolve_template_key(data, key)
            if not found:
                return missing_format.format(key=key)
            return str(value)

        return re.sub(pattern, replace_placeholder, template)

    def _resolve_template_key(self, data: dict, key: str) -> tuple[object, bool]:
        """Resolve nested dictionary keys via dot notation."""
        keys = key.split(".")
        value = data
        for part in keys:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return None, False
        return value, True

    def find_unresolved_placeholders(self, template: str) -> list[str]:
        """Find placeholders that remained unresolved after rendering."""
        placeholders = []
        patterns = (
            r"\{\{(\w+(?:\.\w+)*)\}\}",
            r"\$\{(\w+(?:\.\w+)*)\}",
            r"(?<!\{)\{(\w+(?:\.\w+)*)\}(?!\})",
        )
        for pattern in patterns:
            placeholders.extend(re.findall(pattern, template))
        return placeholders

    def find_matching_template(
        self,
        templates: List[ResponseTemplateConfig],
        trigger_type: str,
        tool_name: Optional[str] = None,
        state_name: Optional[str] = None,
        error_code: Optional[str] = None,
    ) -> Optional[ResponseTemplateConfig]:
        """
        Find a matching response template based on trigger conditions.

        Args:
            templates: List of ResponseTemplate objects to search
            trigger_type: Type of trigger (tool_success, tool_error, state_entry, confirmation)
            tool_name: Name of the tool (for tool_success/tool_error triggers)
            state_name: Name of the state (for state_entry trigger)
            error_code: Error code (for tool_error trigger)

        Returns:
            Matching ResponseTemplate or None
        """
        for template in templates:
            config = template.trigger_config
            if config.get("type") != trigger_type:
                continue

            # Check additional conditions based on trigger type
            if trigger_type in ["tool_success", "tool_error"]:
                if config.get("toolName") and config.get("toolName") != tool_name:
                    continue

            if trigger_type == "tool_error":
                if config.get("errorCode") and config.get("errorCode") != error_code:
                    continue

            if trigger_type == "state_entry":
                if config.get("stateName") and config.get("stateName") != state_name:
                    continue

            return template

        return None

    def apply_template(
        self,
        template: ResponseTemplateConfig,
        data: dict,
    ) -> Optional[str]:
        """
        Apply a response template with data.

        Args:
            template: The ResponseTemplate to apply
            data: Data to substitute into the template

        Returns:
            Rendered string if all required fields are present, None otherwise
        """
        # Check required fields
        if template.required_fields:
            for field in template.required_fields:
                keys = field.split(".")
                value = data
                found = True
                for k in keys:
                    if isinstance(value, dict) and k in value:
                        value = value[k]
                    else:
                        found = False
                        break
                if not found:
                    logger.warning(f"Template {template.name} missing required field: {field}")
                    return None

        return self.render(template.template, data)

    def format_recipient_list(self, recipients: list) -> str:
        """
        Format a list of recipients into a numbered string.

        Args:
            recipients: List of recipient dicts with 'name', 'country_name', 'default_delivery_method'

        Returns:
            Formatted numbered list string
        """
        if not recipients:
            return ""

        lines = []
        for i, recipient in enumerate(recipients, 1):
            line = f"{i}. {recipient['name']} - {recipient['country_name']} ({recipient['default_delivery_method']})"
            lines.append(line)

        return "\n".join(lines)

    def format_phone_list(self, numbers: list) -> str:
        """
        Format a list of phone numbers into a numbered string.

        Args:
            numbers: List of phone number dicts with 'nickname', 'phoneNumber', 'carrier'

        Returns:
            Formatted numbered list string
        """
        if not numbers:
            return ""

        lines = []
        for i, num in enumerate(numbers, 1):
            carrier = num.get('carrier', '').capitalize()
            line = f"{i}. {num['nickname']}: {num['phoneNumber']} ({carrier})"
            lines.append(line)

        return "\n".join(lines)

    def format_list(self, items: list, formatter: Optional[callable] = None) -> str:
        """
        Format a generic list into a numbered string.

        Args:
            items: List of items to format
            formatter: Optional callable to format each item. If None, uses str()

        Returns:
            Formatted numbered list string
        """
        if not items:
            return ""

        if formatter is None:
            formatter = str

        lines = []
        for i, item in enumerate(items, 1):
            lines.append(f"{i}. {formatter(item)}")

        return "\n".join(lines)


# Global renderer instance
_template_renderer: Optional[TemplateRenderer] = None


def get_template_renderer() -> TemplateRenderer:
    """Get or create the template renderer singleton."""
    global _template_renderer
    if _template_renderer is None:
        _template_renderer = TemplateRenderer()
    return _template_renderer
