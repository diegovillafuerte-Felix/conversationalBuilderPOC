"""Configuration loader for JSON config files."""

import json
import logging
import re
from pathlib import Path
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent.parent / "config"
AGENTS_DIR = CONFIG_DIR / "agents"
_PLACEHOLDER_PATTERNS = (
    r"\{\{(\w+(?:\.\w+)*)\}\}",
    r"\$\{(\w+(?:\.\w+)*)\}",
    r"(?<!\{)\{(\w+(?:\.\w+)*)\}(?!\})",
)


def _extract_placeholders(template: str) -> set[str]:
    placeholders: set[str] = set()
    for pattern in _PLACEHOLDER_PATTERNS:
        placeholders.update(re.findall(pattern, template or ""))
    return placeholders


def _warn_unknown_placeholders(agent_id: str, config: dict) -> None:
    """Best-effort warnings for placeholders unlikely to resolve at runtime."""
    tools = config.get("tools", [])
    subflows = config.get("subflows", [])
    known_flow_keys = {
        key
        for subflow in subflows
        for key in (subflow.get("data_schema") or {}).keys()
    }
    runtime_keys = {
        "amount",
        "amount_usd",
        "recipient_name",
        "currency",
        "eta",
        "status",
        "reference",
        "transaction_id",
    }

    # Tool confirmation templates
    for tool in tools:
        template = tool.get("confirmation_template")
        if not template:
            continue
        placeholders = _extract_placeholders(template)
        if not placeholders:
            continue
        param_names = {param.get("name") for param in tool.get("parameters", [])}
        unknown = {
            placeholder
            for placeholder in placeholders
            if placeholder.split(".")[0] not in param_names
            and placeholder.split(".")[0] not in known_flow_keys
            and placeholder.split(".")[0] not in runtime_keys
        }
        if unknown:
            logger.warning(
                "Agent %s tool %s confirmation template has placeholders not in tool params: %s",
                agent_id,
                tool.get("name"),
                sorted(unknown),
            )

    # on_enter templates compared against subflow data schema keys
    for subflow in subflows:
        schema_keys = set((subflow.get("data_schema") or {}).keys())
        for state in subflow.get("states", []):
            on_enter = state.get("on_enter") or {}
            template = on_enter.get("message") or on_enter.get("sendMessage")
            if not isinstance(template, str):
                continue
            placeholders = _extract_placeholders(template)
            unknown = {
                placeholder
                for placeholder in placeholders
                if placeholder.split(".")[0] not in schema_keys
                and placeholder.split(".")[0] not in runtime_keys
            }
            if unknown:
                logger.warning(
                    "Agent %s flow %s state %s on_enter template has placeholders not in flow data_schema: %s",
                    agent_id,
                    subflow.get("id"),
                    state.get("id"),
                    sorted(unknown),
                )


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
            config = json.load(f)
            _warn_unknown_placeholders(agent_id, config)
            return config
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
