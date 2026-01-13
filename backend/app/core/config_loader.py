"""Configuration loader for JSON config files."""

import json
import logging
from pathlib import Path
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent.parent / "config"
AGENTS_DIR = CONFIG_DIR / "agents"


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
def load_confirmation_templates() -> dict:
    """
    Load confirmation templates for financial transactions.

    Returns:
        Dictionary with template configurations including enabled flags
    """
    path = CONFIG_DIR / "confirmation_templates.json"
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Confirmation templates not found: {path}")
        return {"templates": {}}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {path}: {e}")
        return {"templates": {}}


def get_confirmation_template(template_id: str) -> Optional[dict]:
    """
    Get a specific confirmation template if enabled.

    Args:
        template_id: The template identifier (e.g., "transfer_confirmation")

    Returns:
        Template dict with 'template' string if enabled, None if disabled or not found
    """
    config = load_confirmation_templates()
    template = config.get("templates", {}).get(template_id)

    if template and template.get("enabled", True):
        return template
    return None


def reload_configs() -> None:
    """
    Clear all config caches to reload from disk.

    Call this after modifying JSON files to pick up changes
    without restarting the server.
    """
    load_agent_config.cache_clear()
    load_prompts.cache_clear()
    load_confirmation_templates.cache_clear()
    load_shadow_service_config.cache_clear()
    logger.info("Configuration caches cleared")


def get_config_dir() -> Path:
    """Get the config directory path."""
    return CONFIG_DIR


# ============== JSON Write Functions ==============

def get_agent_ids() -> list[str]:
    """
    Get list of all agent IDs from JSON files.

    Returns:
        List of agent IDs (filenames without .json extension)
    """
    if not AGENTS_DIR.exists():
        return []
    return sorted([f.stem for f in AGENTS_DIR.glob("*.json")])


def save_agent_config(agent_id: str, config: dict) -> bool:
    """
    Save agent config to JSON file.

    Args:
        agent_id: The agent identifier
        config: The configuration dictionary to save

    Returns:
        True if saved successfully

    Raises:
        ValueError: If config is invalid
        IOError: If file cannot be written
    """
    if not isinstance(config, dict):
        raise ValueError("Config must be a dictionary")

    # Ensure agents directory exists
    AGENTS_DIR.mkdir(parents=True, exist_ok=True)

    filepath = AGENTS_DIR / f"{agent_id}.json"

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        # Clear cache so next read gets fresh data
        load_agent_config.cache_clear()
        logger.info(f"Saved agent config: {agent_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to save agent config {agent_id}: {e}")
        raise


def delete_agent_config(agent_id: str) -> bool:
    """
    Delete agent config JSON file.

    Args:
        agent_id: The agent identifier to delete

    Returns:
        True if deleted, False if not found
    """
    filepath = AGENTS_DIR / f"{agent_id}.json"

    if not filepath.exists():
        return False

    try:
        filepath.unlink()
        load_agent_config.cache_clear()
        logger.info(f"Deleted agent config: {agent_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete agent config {agent_id}: {e}")
        raise


def agent_exists(agent_id: str) -> bool:
    """
    Check if an agent config file exists.

    Args:
        agent_id: The agent identifier

    Returns:
        True if config file exists
    """
    filepath = AGENTS_DIR / f"{agent_id}.json"
    return filepath.exists()


# ============== Shadow Service Config ==============

SHADOW_SERVICE_PATH = CONFIG_DIR / "shadow_service.json"


@lru_cache(maxsize=1)
def load_shadow_service_config() -> dict:
    """
    Load shadow service configuration from JSON.

    Returns:
        Shadow service configuration dictionary
    """
    try:
        with open(SHADOW_SERVICE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Shadow service config not found: {SHADOW_SERVICE_PATH}")
        return {
            "enabled": False,
            "global_cooldown_messages": 3,
            "max_messages_per_response": 1,
            "subagents": [],
        }
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {SHADOW_SERVICE_PATH}: {e}")
        return {
            "enabled": False,
            "global_cooldown_messages": 3,
            "max_messages_per_response": 1,
            "subagents": [],
        }


def save_shadow_service_config(config: dict) -> bool:
    """
    Save shadow service config to JSON file.

    Args:
        config: The configuration dictionary to save

    Returns:
        True if saved successfully

    Raises:
        ValueError: If config is invalid
        IOError: If file cannot be written
    """
    if not isinstance(config, dict):
        raise ValueError("Config must be a dictionary")

    try:
        with open(SHADOW_SERVICE_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        # Clear cache so next read gets fresh data
        load_shadow_service_config.cache_clear()
        logger.info("Saved shadow service config")
        return True
    except Exception as e:
        logger.error(f"Failed to save shadow service config: {e}")
        raise


def get_shadow_subagent_config(subagent_id: str) -> Optional[dict]:
    """
    Get configuration for a specific shadow subagent.

    Args:
        subagent_id: The subagent identifier (e.g., "financial_advisor", "campaigns")

    Returns:
        Subagent configuration dictionary or None if not found
    """
    config = load_shadow_service_config()
    for subagent in config.get("subagents", []):
        if subagent.get("id") == subagent_id:
            return subagent
    return None


def update_shadow_subagent_config(subagent_id: str, updates: dict) -> bool:
    """
    Update configuration for a specific shadow subagent.

    Args:
        subagent_id: The subagent identifier
        updates: Dictionary of fields to update

    Returns:
        True if updated successfully, False if subagent not found
    """
    config = load_shadow_service_config()
    for i, subagent in enumerate(config.get("subagents", [])):
        if subagent.get("id") == subagent_id:
            config["subagents"][i].update(updates)
            save_shadow_service_config(config)
            return True
    return False


def add_shadow_subagent(subagent_config: dict) -> bool:
    """
    Add a new shadow subagent configuration.

    Args:
        subagent_config: Configuration for the new subagent

    Returns:
        True if added successfully

    Raises:
        ValueError: If subagent with same ID already exists
    """
    config = load_shadow_service_config()
    subagent_id = subagent_config.get("id")

    if not subagent_id:
        raise ValueError("Subagent config must have an 'id' field")

    # Check for duplicate
    for existing in config.get("subagents", []):
        if existing.get("id") == subagent_id:
            raise ValueError(f"Subagent with id '{subagent_id}' already exists")

    if "subagents" not in config:
        config["subagents"] = []

    config["subagents"].append(subagent_config)
    save_shadow_service_config(config)
    return True


def delete_shadow_subagent(subagent_id: str) -> bool:
    """
    Delete a shadow subagent configuration.

    Args:
        subagent_id: The subagent identifier to delete

    Returns:
        True if deleted, False if not found
    """
    config = load_shadow_service_config()
    original_count = len(config.get("subagents", []))

    config["subagents"] = [
        s for s in config.get("subagents", [])
        if s.get("id") != subagent_id
    ]

    if len(config["subagents"]) < original_count:
        save_shadow_service_config(config)
        return True
    return False
