"""Template renderer for response templates."""

import re
import logging
from typing import Optional, List
from app.models.agent import ResponseTemplate, Tool

logger = logging.getLogger(__name__)


class TemplateRenderer:
    """Renders templates with variable substitution."""

    def render(self, template: str, data: dict) -> str:
        """
        Render a template with data substitution.

        Supports {{variable}} syntax.
        """
        def replace_placeholder(match):
            key = match.group(1)
            # Support nested keys with dot notation (e.g., {{recipient.name}})
            keys = key.split(".")
            value = data
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return f"{{{{{key}}}}}"  # Return original if not found
            return str(value)

        rendered = re.sub(r"\{\{(\w+(?:\.\w+)*)\}\}", replace_placeholder, template)
        return rendered

    def find_matching_template(
        self,
        templates: List[ResponseTemplate],
        trigger_type: str,
        tool_name: Optional[str] = None,
        state_name: Optional[str] = None,
        error_code: Optional[str] = None,
    ) -> Optional[ResponseTemplate]:
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
        template: ResponseTemplate,
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


# Global renderer instance
_template_renderer: Optional[TemplateRenderer] = None


def get_template_renderer() -> TemplateRenderer:
    """Get or create the template renderer singleton."""
    global _template_renderer
    if _template_renderer is None:
        _template_renderer = TemplateRenderer()
    return _template_renderer
