"""Internationalization (i18n) utilities for localized messages."""

import logging
from typing import Any, Optional, Union

from app.core.config_loader import load_service_messages, load_prompts

logger = logging.getLogger(__name__)

# Supported languages
SUPPORTED_LANGUAGES = {"en", "es"}
DEFAULT_LANGUAGE = "es"


def get_localized(
    obj: Union[dict, str, None],
    language: str = DEFAULT_LANGUAGE,
    fallback: str = ""
) -> str:
    """
    Get a localized string from a {en: ..., es: ...} dictionary.

    Args:
        obj: Either a string (returned as-is) or a dict with language keys
        language: Target language code ("en" or "es")
        fallback: Value to return if key not found

    Returns:
        Localized string
    """
    if obj is None:
        return fallback

    if isinstance(obj, str):
        return obj

    if isinstance(obj, dict):
        # Try requested language, fall back to Spanish, then fallback value
        return obj.get(language) or obj.get(DEFAULT_LANGUAGE) or fallback

    return fallback


def get_message(
    key: str,
    language: str = DEFAULT_LANGUAGE,
    **kwargs: Any
) -> str:
    """
    Get a localized message from the service messages config.

    Args:
        key: Dot-notation key (e.g., "topups.topup_success")
        language: Target language code ("en" or "es")
        **kwargs: Template variables for string formatting

    Returns:
        Formatted message in the requested language

    Example:
        >>> get_message("topups.topup_success", "en", phone_number="+52...")
        "✅ Top-up sent successfully!\\n📱 Number: +52..."
    """
    messages = load_service_messages()

    # Navigate to the message using dot notation
    parts = key.split(".")
    value = messages
    for part in parts:
        if isinstance(value, dict):
            value = value.get(part, {})
        else:
            value = {}

    if not value:
        logger.warning(f"Missing message key: {key}")
        return f"[Missing: {key}]"

    # Get language version (fallback to Spanish)
    template = get_localized(value, language, f"[Missing: {key}.{language}]")

    # Format with kwargs
    try:
        return template.format(**kwargs)
    except KeyError as e:
        logger.warning(f"Missing template variable in {key}: {e}")
        return template
    except Exception as e:
        logger.error(f"Error formatting message {key}: {e}")
        return template


def get_prompt_section(
    section_key: str,
    language: str = DEFAULT_LANGUAGE,
    **kwargs: Any
) -> str:
    """
    Get a localized prompt section from the prompts config.

    Args:
        section_key: Section key (e.g., "scope_rule", "navigation")
        language: Target language code
        **kwargs: Template variables

    Returns:
        Formatted prompt section
    """
    prompts = load_prompts()
    sections = prompts.get("sections", {})

    section = sections.get(section_key)
    if not section:
        logger.warning(f"Missing prompt section: {section_key}")
        return ""

    template = get_localized(section, language)

    try:
        return template.format(**kwargs)
    except KeyError as e:
        logger.warning(f"Missing template variable in section {section_key}: {e}")
        return template
    except Exception as e:
        logger.error(f"Error formatting section {section_key}: {e}")
        return template


def get_base_system_prompt(language: str = DEFAULT_LANGUAGE) -> str:
    """
    Get the base system prompt in the specified language.

    Args:
        language: Target language code

    Returns:
        Base system prompt
    """
    prompts = load_prompts()
    base_prompt = prompts.get("base_system_prompt", {})
    return get_localized(base_prompt, language, "")


def get_language_directive(language: str = DEFAULT_LANGUAGE) -> str:
    """
    Get the language directive that instructs the LLM to respond in a specific language.

    Args:
        language: Target language code

    Returns:
        Formatted language directive
    """
    prompts = load_prompts()
    directive = prompts.get("language_directive", {})
    template = get_localized(directive, language, "")

    # Format with the language name
    lang_name = "English" if language == "en" else "Spanish"
    try:
        return template.format(language=lang_name)
    except KeyError:
        return template


def normalize_language(language: Optional[str]) -> str:
    """
    Normalize a language code to a supported value.

    Args:
        language: Language code (may be None or invalid)

    Returns:
        Normalized language code (always "en" or "es")
    """
    if not language:
        return DEFAULT_LANGUAGE

    lang = language.lower().strip()

    # Handle common variations
    if lang in {"en", "english", "eng"}:
        return "en"
    if lang in {"es", "spanish", "español", "spa"}:
        return "es"

    # Default to Spanish for unknown codes
    return DEFAULT_LANGUAGE
