"""Configuration loader for JSON config files."""

import json
import logging
from pathlib import Path
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent.parent / "config"


@lru_cache(maxsize=32)
def load_agent_config(agent_id: str) -> dict:
    """
    Load agent configuration from JSON.

    Args:
        agent_id: The agent identifier (e.g., "felix", "topups")

    Returns:
        Agent configuration dictionary
    """
    path = CONFIG_DIR / "agents" / f"{agent_id}.json"
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Agent config not found: {path}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {path}: {e}")
        return {}


def load_all_agent_configs() -> dict[str, dict]:
    """
    Load all agent configurations.

    Returns:
        Dictionary mapping agent_id to config
    """
    agents_dir = CONFIG_DIR / "agents"
    configs = {}

    if not agents_dir.exists():
        logger.warning(f"Agents config directory not found: {agents_dir}")
        return configs

    for path in agents_dir.glob("*.json"):
        agent_id = path.stem
        configs[agent_id] = load_agent_config(agent_id)

    return configs


@lru_cache(maxsize=1)
def load_prompts() -> dict:
    """
    Load prompt templates from JSON files.

    Returns:
        Dictionary with base prompts and section templates
    """
    prompts = {}

    # Load base system prompt
    base_path = CONFIG_DIR / "prompts" / "base_system.json"
    try:
        with open(base_path, encoding="utf-8") as f:
            prompts.update(json.load(f))
    except FileNotFoundError:
        logger.warning(f"Base system prompt not found: {base_path}")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {base_path}: {e}")

    # Load section templates
    sections_path = CONFIG_DIR / "prompts" / "sections.json"
    try:
        with open(sections_path, encoding="utf-8") as f:
            prompts["sections"] = json.load(f)
    except FileNotFoundError:
        logger.warning(f"Sections config not found: {sections_path}")
        prompts["sections"] = {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {sections_path}: {e}")
        prompts["sections"] = {}

    return prompts


@lru_cache(maxsize=1)
def load_service_messages() -> dict:
    """
    Load service message templates for i18n.

    Returns:
        Dictionary with localized message templates
    """
    path = CONFIG_DIR / "messages" / "services.json"
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Service messages not found: {path}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {path}: {e}")
        return {}


def reload_configs() -> None:
    """
    Clear all config caches to reload from disk.

    Call this after modifying JSON files to pick up changes
    without restarting the server.
    """
    load_agent_config.cache_clear()
    load_prompts.cache_clear()
    load_service_messages.cache_clear()
    logger.info("Configuration caches cleared")


def get_config_dir() -> Path:
    """Get the config directory path."""
    return CONFIG_DIR
