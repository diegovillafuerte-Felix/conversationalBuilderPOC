"""Seed data for agents and tools."""

import json
import logging
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent, Tool, ResponseTemplate
from app.models.user import UserContext
from app.models.subflow import Subflow, SubflowState
from app.core.config_loader import load_agent_config, load_all_agent_configs
from app.core.i18n import get_localized, DEFAULT_LANGUAGE

# Path to sample data files
SAMPLE_DATA_DIR = Path(__file__).parent.parent / "config" / "sample_data"

logger = logging.getLogger(__name__)


async def seed_agents(db: AsyncSession) -> None:
    """Seed the database with initial agent configurations from JSON files."""

    # Check if agents already exist
    result = await db.execute(select(Agent).limit(1))
    if result.scalar_one_or_none():
        logger.info("Agents already seeded, skipping")
        return

    logger.info("Seeding agents from JSON configs...")

    # Define seeding order (parents before children)
    agent_order = ["felix", "remittances", "credit", "wallet", "topups", "billpay"]

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

        # Create agent with Spanish defaults (stored in DB) but full config for runtime
        agent = Agent(
            name=get_localized(config.get("name", {}), DEFAULT_LANGUAGE, agent_id),
            parent_agent_id=parent_agent_id,
            description=get_localized(config.get("description", {}), DEFAULT_LANGUAGE, ""),
            system_prompt_addition=get_localized(config.get("system_prompt_addition", {}), DEFAULT_LANGUAGE),
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
                description=get_localized(tool_config.get("description", {}), DEFAULT_LANGUAGE, ""),
                parameters=_process_parameters(tool_config.get("parameters", [])),
                requires_confirmation=tool_config.get("requires_confirmation", False),
                confirmation_template=get_localized(tool_config.get("confirmation_template", {}), DEFAULT_LANGUAGE),
                side_effects=tool_config.get("side_effects", "none"),
                flow_transition=tool_config.get("flow_transition"),
                config_json=tool_config,  # Store full config for runtime i18n
            )
            db.add(tool)

        # Create subflows if any
        for subflow_config in config.get("subflows", []):
            subflow = Subflow(
                agent_id=agent.id,
                name=get_localized(subflow_config.get("name", {}), DEFAULT_LANGUAGE, subflow_config.get("id", "")),
                trigger_description=get_localized(subflow_config.get("trigger_description", {}), DEFAULT_LANGUAGE, ""),
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
                        "sendMessage": get_localized(on_enter["message"], DEFAULT_LANGUAGE, "")
                    }

                state = SubflowState(
                    subflow_id=subflow.id,
                    state_id=state_config["id"],
                    name=get_localized(state_config.get("name", {}), DEFAULT_LANGUAGE, state_config["id"]),
                    agent_instructions=get_localized(state_config.get("agent_instructions", {}), DEFAULT_LANGUAGE, ""),
                    state_tools=state_config.get("tools", []),
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
                name=get_localized(template_config.get("name", {}), DEFAULT_LANGUAGE, ""),
                trigger_config=template_config.get("trigger_config", {}),
                template=get_localized(template_config.get("template", {}), DEFAULT_LANGUAGE, ""),
                required_fields=template_config.get("required_fields", []),
                enforcement=template_config.get("enforcement", "suggested"),
            )
            db.add(template)

    await db.commit()
    logger.info("Agents seeded successfully from JSON configs!")


def _process_parameters(params: list) -> list:
    """Process tool parameters, extracting Spanish descriptions as default."""
    processed = []
    for param in params:
        p = {
            "name": param["name"],
            "type": param.get("type", "string"),
            "required": param.get("required", False),
        }
        # Get Spanish description as default
        if "description" in param:
            p["description"] = get_localized(param["description"], DEFAULT_LANGUAGE, "")
        if "validation" in param:
            p["validation"] = param["validation"]
        processed.append(p)
    return processed


def _process_timeout_config(timeout_config: dict) -> dict:
    """Process timeout config, extracting Spanish reminder message."""
    if not timeout_config:
        return {}

    result = {
        "durationMinutes": timeout_config.get("durationMinutes", 10),
        "onTimeout": timeout_config.get("onTimeout", "abandon"),
    }

    if "reminderMessage" in timeout_config:
        result["reminderMessage"] = get_localized(
            timeout_config["reminderMessage"], DEFAULT_LANGUAGE, ""
        )

    return result


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
