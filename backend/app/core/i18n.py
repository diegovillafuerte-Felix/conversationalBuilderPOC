"""Internationalization (i18n) utilities - simplified for English-only prompts."""

import logging
from typing import Optional

from app.core.config_loader import load_prompts

logger = logging.getLogger(__name__)

# Supported languages
SUPPORTED_LANGUAGES = {"en", "es"}
DEFAULT_LANGUAGE = "es"

# Language display names for the language directive
LANGUAGE_DISPLAY_NAMES = {
    "en": {"en": "English", "es": "Inglés"},
    "es": {"en": "Spanish", "es": "Español"}
}


def get_language_display_name(language_code: str, in_language: str = "en") -> str:
    """Get the display name for a language code."""
    return LANGUAGE_DISPLAY_NAMES.get(language_code, {}).get(in_language, language_code)


def get_language_directive(language: str = DEFAULT_LANGUAGE) -> str:
    """
    Get the language directive that instructs the LLM to respond in a specific language.

    This is the ONLY language-related injection in the system prompts.
    All other prompts are in English; this directive tells the LLM what language
    to respond in based on the user's preference.

    Args:
        language: Target language code ("en" or "es")

    Returns:
        Formatted language directive
    """
    prompts = load_prompts()
    template = prompts.get("language_directive", "")

    # Handle legacy format (dict with en/es keys) or new format (plain string)
    if isinstance(template, dict):
        template = template.get("en", "")

    # Get the display name in the target language for clarity
    language_display = get_language_display_name(language, language)

    try:
        return template.format(language=language.upper(), language_display=language_display)
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
