"""Routing registry for validating and caching routing mappings."""

import logging
from typing import Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.agent import Agent, Tool
from app.models.subflow import Subflow
from app.core.routing import RoutingConfig, RoutingType, RoutingResult

logger = logging.getLogger(__name__)


class RoutingRegistryError(Exception):
    """Raised when routing configuration is invalid."""
    pass


class RoutingRegistry:
    """
    Validates and caches routing mappings at startup.

    Provides fast lookups for:
    - Agent config_id -> Agent entity
    - Subflow config_id -> Subflow entity
    - Tool name -> RoutingConfig
    """

    def __init__(self):
        self._agents: Dict[str, Agent] = {}  # config_id -> Agent
        self._subflows: Dict[str, Subflow] = {}  # config_id -> Subflow
        self._tool_routing: Dict[str, RoutingConfig] = {}  # tool_name -> RoutingConfig
        self._initialized = False

    async def initialize(self, db: AsyncSession) -> None:
        """
        Load and validate all routing configurations.

        Called at application startup.
        Raises RoutingRegistryError if validation fails.
        """
        errors = []

        # Load all active agents with their tools
        result = await db.execute(
            select(Agent)
            .where(Agent.is_active == True)
            .options(selectinload(Agent.tools))
        )
        for agent in result.scalars().all():
            if not agent.config_id:
                errors.append(f"Agent {agent.id} ({agent.name}) missing config_id")
                continue
            if agent.config_id in self._agents:
                errors.append(f"Duplicate agent config_id: {agent.config_id}")
                continue
            self._agents[agent.config_id] = agent

            # Load tool routing configs
            for tool in agent.tools:
                routing_config = RoutingConfig.from_dict(tool.routing)
                self._tool_routing[tool.name] = routing_config

        # Load all subflows
        result = await db.execute(select(Subflow))
        for subflow in result.scalars().all():
            if not subflow.config_id:
                errors.append(f"Subflow {subflow.id} ({subflow.name}) missing config_id")
                continue
            if subflow.config_id in self._subflows:
                errors.append(f"Duplicate subflow config_id: {subflow.config_id}")
                continue
            self._subflows[subflow.config_id] = subflow

        # Validate that all routing targets exist
        for tool_name, routing in self._tool_routing.items():
            if routing.type == RoutingType.ENTER_AGENT:
                if routing.target and routing.target not in self._agents:
                    errors.append(
                        f"Tool '{tool_name}' routes to unknown agent: {routing.target}"
                    )
            elif routing.type == RoutingType.START_FLOW:
                if routing.target and routing.target not in self._subflows:
                    errors.append(
                        f"Tool '{tool_name}' routes to unknown subflow: {routing.target}"
                    )
                # Validate cross-agent target if specified
                if routing.cross_agent and routing.cross_agent not in self._agents:
                    errors.append(
                        f"Tool '{tool_name}' has unknown cross_agent: {routing.cross_agent}"
                    )

        if errors:
            for error in errors:
                logger.error(f"Routing validation error: {error}")
            raise RoutingRegistryError(
                f"Routing validation failed with {len(errors)} error(s). "
                f"First error: {errors[0]}"
            )

        self._initialized = True
        logger.info(
            f"Routing registry initialized: {len(self._agents)} agents, "
            f"{len(self._subflows)} subflows, {len(self._tool_routing)} tool routes"
        )

    def get_agent(self, config_id: str) -> Optional[Agent]:
        """Get agent by config_id."""
        return self._agents.get(config_id)

    def get_subflow(self, config_id: str) -> Optional[Subflow]:
        """Get subflow by config_id."""
        return self._subflows.get(config_id)

    def get_tool_routing(self, tool_name: str) -> RoutingConfig:
        """
        Get routing config for a tool.

        Returns SERVICE type if tool not found (allows mock execution).
        """
        config = self._tool_routing.get(tool_name)
        if config is None:
            logger.warning(
                f"Unknown tool '{tool_name}' - defaulting to SERVICE type. "
                f"This may indicate a missing tool definition or configuration error."
            )
            return RoutingConfig(type=RoutingType.SERVICE, target=None)
        return config

    def resolve_routing(self, tool_name: str) -> RoutingResult:
        """
        Resolve routing for a tool call.

        Returns a RoutingResult with the target entity loaded.
        """
        routing = self.get_tool_routing(tool_name)

        if routing.type == RoutingType.ENTER_AGENT:
            agent = self.get_agent(routing.target) if routing.target else None
            if not agent:
                return RoutingResult(
                    success=False,
                    action=routing.type,
                    target_id=None,
                    target_entity=None,
                    error=f"Agent not found: {routing.target}"
                )
            return RoutingResult(
                success=True,
                action=routing.type,
                target_id=str(agent.id),
                target_entity=agent
            )

        elif routing.type == RoutingType.START_FLOW:
            subflow = self.get_subflow(routing.target) if routing.target else None
            if not subflow:
                return RoutingResult(
                    success=False,
                    action=routing.type,
                    target_id=None,
                    target_entity=None,
                    error=f"Subflow not found: {routing.target}"
                )
            return RoutingResult(
                success=True,
                action=routing.type,
                target_id=str(subflow.id),
                target_entity=subflow
            )

        elif routing.type == RoutingType.NAVIGATION:
            return RoutingResult(
                success=True,
                action=routing.type,
                target_id=routing.target,  # "up_one_level", "go_home", "escalate_to_human"
                target_entity=None
            )

        else:  # SERVICE
            return RoutingResult(
                success=True,
                action=routing.type,
                target_id=None,
                target_entity=None
            )


# Global singleton
_routing_registry: Optional[RoutingRegistry] = None


async def get_routing_registry(db: AsyncSession) -> RoutingRegistry:
    """Get or initialize the routing registry."""
    global _routing_registry
    if _routing_registry is None:
        _routing_registry = RoutingRegistry()
        await _routing_registry.initialize(db)
    return _routing_registry


async def initialize_routing_registry(db: AsyncSession) -> RoutingRegistry:
    """Force (re)initialize the routing registry. Called at startup."""
    global _routing_registry
    _routing_registry = RoutingRegistry()
    await _routing_registry.initialize(db)
    return _routing_registry


def reset_routing_registry() -> None:
    """Reset the routing registry (for testing)."""
    global _routing_registry
    _routing_registry = None
