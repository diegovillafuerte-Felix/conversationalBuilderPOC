"""Seed data for agents and tools."""

import json
import logging
from pathlib import Path
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent, Tool, ResponseTemplate
from app.models.user import UserContext
from app.models.subflow import Subflow, SubflowState
from app.core.config_loader import load_agent_config, load_all_agent_configs

# Path to sample data files
SAMPLE_DATA_DIR = Path(__file__).parent.parent / "config" / "sample_data"

logger = logging.getLogger(__name__)


def _get_string_value(value, fallback: str = "") -> str:
    """
    Extract string value from config field.

    Handles both:
    - New format: plain strings (e.g., "Send money to Mexico")
    - Legacy format: localized dicts (e.g., {"en": "...", "es": "..."})

    For legacy dicts, extracts English value as the canonical version.
    """
    if value is None:
        return fallback
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        # Legacy localized dict - prefer English
        return value.get("en", value.get("es", fallback))
    return fallback


async def seed_agents(db: AsyncSession) -> None:
    """Seed the database with initial agent configurations from JSON files."""

    # Check if agents already exist
    result = await db.execute(select(Agent).limit(1))
    if result.scalar_one_or_none():
        logger.info("Agents already seeded, skipping")
        return

    logger.info("Seeding agents from JSON configs...")

    # Define seeding order (parents before children)
    agent_order = ["felix", "remittances", "snpl", "wallet", "topups", "billpay"]

    # Keep track of created agents for parent references
    created_agents = {}

    for agent_id in agent_order:
        config = load_agent_config(agent_id)
        if not config:
            logger.warning(f"No config found for agent: {agent_id}")
            continue

        # Determine parent agent ID
        parent_agent_id = None
        parent_ref = config.get("parent_agent")
        if parent_ref and parent_ref in created_agents:
            parent_agent_id = created_agents[parent_ref].id

        # Create agent with config values (stored in DB) and full config for runtime
        agent = Agent(
            config_id=config.get("id", agent_id),
            name=_get_string_value(config.get("name"), agent_id),
            parent_agent_id=parent_agent_id,
            description=_get_string_value(config.get("description"), ""),
            system_prompt_addition=_get_string_value(config.get("system_prompt_addition")),
            model_config_json=config.get("model_config", {
                "model": "gpt-4o",
                "temperature": 0.7,
                "maxTokens": 1024,
            }),
            navigation_tools=config.get("navigation", {
                "canGoUp": False,
                "canGoHome": False,
                "canEscalate": True,
            }),
            context_requirements=config.get("context_requirements"),
            config_json=config,  # Store full config for runtime i18n
            is_active=True,
        )
        db.add(agent)
        await db.flush()
        created_agents[agent_id] = agent
        logger.info(f"Created agent: {agent.name}")

        # Create tools for this agent
        for tool_config in config.get("tools", []):
            tool = Tool(
                agent_id=agent.id,
                name=tool_config["name"],
                description=_get_string_value(tool_config.get("description"), ""),
                parameters=_process_parameters(tool_config.get("parameters", [])),
                requires_confirmation=tool_config.get("requires_confirmation", False),
                confirmation_template=_get_string_value(tool_config.get("confirmation_template")),
                side_effects=tool_config.get("side_effects", "none"),
                flow_transition=tool_config.get("flow_transition"),
                routing=_build_routing_config(tool_config),
                config_json=tool_config,  # Store full config for runtime i18n
            )
            db.add(tool)

        # Create subflows if any
        for subflow_config in config.get("subflows", []):
            subflow = Subflow(
                agent_id=agent.id,
                config_id=subflow_config.get("id", ""),
                name=_get_string_value(subflow_config.get("name"), subflow_config.get("id", "")),
                trigger_description=_get_string_value(subflow_config.get("trigger_description"), ""),
                initial_state=subflow_config.get("initial_state", ""),
                data_schema=subflow_config.get("data_schema", {}),
                timeout_config=_process_timeout_config(subflow_config.get("timeout_config", {})),
            )
            db.add(subflow)
            await db.flush()

            # Create states for this subflow
            for state_config in subflow_config.get("states", []):
                on_enter = state_config.get("on_enter")
                if on_enter and "message" in on_enter:
                    on_enter = {
                        "sendMessage": _get_string_value(on_enter["message"], "")
                    }

                state = SubflowState(
                    subflow_id=subflow.id,
                    state_id=state_config["id"],
                    name=_get_string_value(state_config.get("name"), state_config["id"]),
                    agent_instructions=_get_string_value(state_config.get("agent_instructions"), ""),
                    state_tools=state_config.get("state_tools", []),
                    transitions=state_config.get("transitions", []),
                    on_enter=on_enter,
                    is_final=state_config.get("is_final", False),
                    config_json=state_config,  # Store full config for runtime i18n
                )
                db.add(state)

        # Create response templates if any
        for template_config in config.get("response_templates", []):
            template = ResponseTemplate(
                agent_id=agent.id,
                name=_get_string_value(template_config.get("name"), ""),
                trigger_config=template_config.get("trigger_config", {}),
                template=_get_string_value(template_config.get("template"), ""),
                required_fields=template_config.get("required_fields", []),
                enforcement=template_config.get("enforcement", "suggested"),
            )
            db.add(template)

    await db.commit()
    logger.info("Agents seeded successfully from JSON configs!")


async def reseed_agents_from_json(db: AsyncSession) -> dict:
    """
    Force reseed all agents from JSON files.

    This deletes all existing agents and re-creates them from JSON.
    Use this to sync DB with JSON after config changes.

    Returns:
        Dict with counts of deleted and created entities
    """
    logger.info("Force reseeding agents from JSON configs...")

    # Delete in correct order (children before parents due to FK constraints)
    # SubflowStates reference Subflows
    await db.execute(delete(SubflowState))
    # Subflows and Tools reference Agents
    await db.execute(delete(Subflow))
    await db.execute(delete(Tool))
    await db.execute(delete(ResponseTemplate))
    # Finally delete Agents
    await db.execute(delete(Agent))
    await db.commit()
    logger.info("Deleted all existing agent configurations")

    # Now seed fresh from JSON (reuse existing logic)
    # We need to temporarily bypass the "already seeded" check
    agent_order = ["felix", "remittances", "snpl", "wallet", "topups", "billpay"]
    created_agents = {}
    stats = {"agents": 0, "tools": 0, "subflows": 0, "states": 0, "templates": 0}

    for agent_id in agent_order:
        config = load_agent_config(agent_id)
        if not config:
            logger.warning(f"No config found for agent: {agent_id}")
            continue

        parent_agent_id = None
        parent_ref = config.get("parent_agent")
        if parent_ref and parent_ref in created_agents:
            parent_agent_id = created_agents[parent_ref].id

        agent = Agent(
            config_id=config.get("id", agent_id),
            name=_get_string_value(config.get("name"), agent_id),
            parent_agent_id=parent_agent_id,
            description=_get_string_value(config.get("description"), ""),
            system_prompt_addition=_get_string_value(config.get("system_prompt_addition")),
            model_config_json=config.get("model_config", {
                "model": "gpt-4o",
                "temperature": 0.7,
                "maxTokens": 1024,
            }),
            navigation_tools=config.get("navigation", {
                "canGoUp": False,
                "canGoHome": False,
                "canEscalate": True,
            }),
            context_requirements=config.get("context_requirements"),
            config_json=config,
            is_active=True,
        )
        db.add(agent)
        await db.flush()
        created_agents[agent_id] = agent
        stats["agents"] += 1

        for tool_config in config.get("tools", []):
            tool = Tool(
                agent_id=agent.id,
                name=tool_config["name"],
                description=_get_string_value(tool_config.get("description"), ""),
                parameters=_process_parameters(tool_config.get("parameters", [])),
                requires_confirmation=tool_config.get("requires_confirmation", False),
                confirmation_template=_get_string_value(tool_config.get("confirmation_template")),
                side_effects=tool_config.get("side_effects", "none"),
                flow_transition=tool_config.get("flow_transition"),
                routing=_build_routing_config(tool_config),
                config_json=tool_config,
            )
            db.add(tool)
            stats["tools"] += 1

        for subflow_config in config.get("subflows", []):
            subflow = Subflow(
                agent_id=agent.id,
                config_id=subflow_config.get("id", ""),
                name=_get_string_value(subflow_config.get("name"), subflow_config.get("id", "")),
                trigger_description=_get_string_value(subflow_config.get("trigger_description"), ""),
                initial_state=subflow_config.get("initial_state", ""),
                data_schema=subflow_config.get("data_schema", {}),
                timeout_config=_process_timeout_config(subflow_config.get("timeout_config", {})),
            )
            db.add(subflow)
            await db.flush()
            stats["subflows"] += 1

            for state_config in subflow_config.get("states", []):
                on_enter = state_config.get("on_enter")
                if on_enter and "message" in on_enter:
                    on_enter = {
                        "sendMessage": _get_string_value(on_enter["message"], "")
                    }

                state = SubflowState(
                    subflow_id=subflow.id,
                    state_id=state_config["id"],
                    name=_get_string_value(state_config.get("name"), state_config["id"]),
                    agent_instructions=_get_string_value(state_config.get("agent_instructions"), ""),
                    state_tools=state_config.get("state_tools", []),
                    transitions=state_config.get("transitions", []),
                    on_enter=on_enter,
                    is_final=state_config.get("is_final", False),
                    config_json=state_config,
                )
                db.add(state)
                stats["states"] += 1

        for template_config in config.get("response_templates", []):
            template = ResponseTemplate(
                agent_id=agent.id,
                name=_get_string_value(template_config.get("name"), ""),
                trigger_config=template_config.get("trigger_config", {}),
                template=_get_string_value(template_config.get("template"), ""),
                required_fields=template_config.get("required_fields", []),
                enforcement=template_config.get("enforcement", "suggested"),
            )
            db.add(template)
            stats["templates"] += 1

    await db.commit()
    logger.info(f"Reseeded agents from JSON: {stats}")
    return stats


def _process_parameters(params: list) -> list:
    """Process tool parameters, extracting descriptions."""
    processed = []
    for param in params:
        p = {
            "name": param["name"],
            "type": param.get("type", "string"),
            "required": param.get("required", False),
        }
        # Get description (handles both string and legacy dict format)
        if "description" in param:
            p["description"] = _get_string_value(param["description"], "")
        if "validation" in param:
            p["validation"] = param["validation"]
        processed.append(p)
    return processed


def _process_timeout_config(timeout_config: dict) -> dict:
    """Process timeout config, extracting reminder message."""
    if not timeout_config:
        return {}

    result = {
        "durationMinutes": timeout_config.get("durationMinutes", 10),
        "onTimeout": timeout_config.get("onTimeout", "abandon"),
    }

    if "reminderMessage" in timeout_config:
        result["reminderMessage"] = _get_string_value(
            timeout_config["reminderMessage"], ""
        )

    return result


def _build_routing_config(tool_config: dict) -> dict | None:
    """
    Build routing config from tool definition.

    Handles both new explicit routing and legacy fields for backward compatibility.
    """
    # Check for explicit routing config first
    if "routing" in tool_config:
        return tool_config["routing"]

    # Legacy: infer from starts_flow
    if "starts_flow" in tool_config:
        return {
            "type": "start_flow",
            "target": tool_config["starts_flow"]
        }

    # Legacy: infer from tool name patterns
    name = tool_config["name"]

    if name.startswith("enter_"):
        return {
            "type": "enter_agent",
            "target": name.replace("enter_", "")
        }

    if name.startswith("start_flow_"):
        # Extract the flow name directly from tool name (don't add _flow suffix)
        # Tool: start_flow_recarga -> target: recarga
        # Tool: start_flow_send_money -> target: send_money_flow (if that's in config)
        inferred_flow = name.replace("start_flow_", "")
        logger.debug(
            f"Tool {name} inferred routing target: {inferred_flow}"
        )
        return {
            "type": "start_flow",
            "target": inferred_flow
        }

    if name in ["up_one_level", "go_home", "escalate_to_human"]:
        return {
            "type": "navigation",
            "target": name
        }

    # Default: service tool (no routing)
    return None


def load_sample_users() -> list:
    """Load sample users from JSON config file."""
    users_file = SAMPLE_DATA_DIR / "users.json"
    if not users_file.exists():
        logger.warning(f"Sample users file not found: {users_file}")
        return []

    with open(users_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("users", [])


async def seed_sample_users(db: AsyncSession) -> None:
    """Seed sample users from JSON config file."""
    sample_users = load_sample_users()

    if not sample_users:
        logger.warning("No sample users found to seed")
        return

    users_created = 0
    for user_data in sample_users:
        user_id = user_data.get("user_id")
        if not user_id:
            logger.warning("Sample user missing user_id, skipping")
            continue

        # Check if user already exists
        result = await db.execute(
            select(UserContext).where(UserContext.user_id == user_id)
        )
        if result.scalar_one_or_none():
            logger.debug(f"User {user_id} already exists, skipping")
            continue

        user = UserContext(
            user_id=user_id,
            profile=user_data.get("profile"),
            product_summaries=user_data.get("product_summaries"),
            behavioral_summary=user_data.get("behavioral_summary"),
        )
        db.add(user)
        users_created += 1
        logger.info(f"Created sample user: {user_id}")

    if users_created > 0:
        await db.commit()
        logger.info(f"Seeded {users_created} sample user(s) successfully!")
    else:
        logger.info("All sample users already exist, skipping")


async def run_seeds(db: AsyncSession) -> None:
    """Run all seed functions."""
    await seed_agents(db)
    await seed_sample_users(db)
