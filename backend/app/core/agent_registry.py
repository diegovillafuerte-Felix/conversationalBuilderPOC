"""Agent registry for in-memory configuration management.

Replaces database queries and RoutingRegistry with a single source of truth
for agent configuration loaded from JSON files.
"""

import logging
from typing import Dict, List, Optional
from threading import Lock

from app.core.config_loader import load_agent_config, get_agent_ids, reload_configs
from app.core.config_types import (
    AgentConfig,
    SubflowConfig,
    SubflowStateConfig,
    ToolConfig,
)
from app.core.routing import RoutingConfig, RoutingType, RoutingResult

logger = logging.getLogger(__name__)


class AgentRegistryError(Exception):
    """Raised when registry initialization or validation fails."""
    pass


class AgentRegistry:
    """
    In-memory registry for all agent configurations.
    Replaces both DB queries and RoutingRegistry.
    """

    def __init__(self):
        self._agents: Dict[str, AgentConfig] = {}           # config_id -> agent
        self._tool_routing: Dict[str, RoutingConfig] = {}   # tool_name -> routing
        self._children: Dict[str, List[str]] = {}           # parent_id -> [child_ids]
        self._root_agent_id: Optional[str] = None
        self._initialized = False
        self._lock = Lock()  # For thread-safe reload

    def initialize(self) -> None:
        """Load all agents from JSON, build indexes, validate."""
        with self._lock:
            self._agents.clear()
            self._tool_routing.clear()
            self._children.clear()
            self._root_agent_id = None

            # Load all agent configs
            for agent_id in get_agent_ids():
                config_dict = load_agent_config(agent_id)
                if not config_dict:
                    logger.warning(f"Could not load config for agent: {agent_id}")
                    continue

                agent = AgentConfig.from_dict(config_dict)
                self._agents[agent.config_id] = agent

                # Build tool routing index
                for tool in agent.tools:
                    if tool.routing:
                        self._tool_routing[tool.name] = tool.routing

                # Track parent-child relationships
                if agent.parent_agent_id:
                    if agent.parent_agent_id not in self._children:
                        self._children[agent.parent_agent_id] = []
                    self._children[agent.parent_agent_id].append(agent.config_id)
                else:
                    self._root_agent_id = agent.config_id

            # Validate configuration
            errors = self.validate()
            if errors:
                for error in errors:
                    logger.error(f"Registry validation error: {error}")
                raise AgentRegistryError(
                    f"Registry validation failed with {len(errors)} error(s). First: {errors[0]}"
                )

            self._initialized = True
            logger.info(
                f"AgentRegistry initialized: {len(self._agents)} agents, "
                f"{len(self._tool_routing)} tool routes, root={self._root_agent_id}"
            )

    def validate(self) -> List[str]:
        """Validate all configurations. Returns list of errors."""
        errors = []

        for agent in self._agents.values():
            agent_tool_names = {t.name for t in agent.tools}

            # Validate state_tools reference real tools
            for subflow in agent.subflows:
                state_ids = set(subflow.states.keys())
                for state in subflow.states.values():
                    for tool_name in state.state_tools:
                        if tool_name not in agent_tool_names:
                            errors.append(
                                f"Agent '{agent.config_id}' / Flow '{subflow.config_id}' / "
                                f"State '{state.state_id}': references tool '{tool_name}' "
                                f"not in agent tools: {sorted(agent_tool_names)}"
                            )
                    for transition in state.transitions:
                        target = transition.get("target")
                        if target and target not in state_ids and target not in {
                            "exit",
                            "abandon",
                            "go_home",
                        }:
                            errors.append(
                                f"Agent '{agent.config_id}' / Flow '{subflow.config_id}' / "
                                f"State '{state.state_id}': transition target '{target}' does not exist"
                            )

                        transition_trigger = transition.get("transition_trigger")
                        if transition_trigger and transition_trigger not in {
                            "on_user_turn",
                            "on_tool_result",
                            "always",
                        }:
                            errors.append(
                                f"Agent '{agent.config_id}' / Flow '{subflow.config_id}' / "
                                f"State '{state.state_id}': invalid transition_trigger '{transition_trigger}'"
                            )

            # Validate routing targets exist
            for tool in agent.tools:
                if not tool.routing:
                    continue
                if tool.routing.type == RoutingType.ENTER_AGENT:
                    if tool.routing.target and tool.routing.target not in self._agents:
                        errors.append(
                            f"Tool '{tool.name}' routes to unknown agent: {tool.routing.target}"
                        )
                elif tool.routing.type == RoutingType.START_FLOW:
                    # Check that the target subflow exists in the current agent or cross_agent
                    target_agent_id = tool.routing.cross_agent or agent.config_id
                    target_agent = self._agents.get(target_agent_id)
                    if target_agent:
                        subflow_ids = {s.config_id for s in target_agent.subflows}
                        if tool.routing.target and tool.routing.target not in subflow_ids:
                            errors.append(
                                f"Tool '{tool.name}' routes to unknown subflow: {tool.routing.target}"
                            )

        return errors

    def reload(self) -> None:
        """Hot-reload configs from JSON files."""
        logger.info("Reloading AgentRegistry from JSON files...")
        reload_configs()  # Clear LRU cache
        self.initialize()

    # --- Agent lookups ---

    def get_agent(self, config_id: str) -> Optional[AgentConfig]:
        """Get agent by config_id."""
        return self._agents.get(config_id)

    def get_root_agent(self) -> Optional[AgentConfig]:
        """Get the root agent (no parent)."""
        if self._root_agent_id:
            return self._agents.get(self._root_agent_id)
        return None

    def get_children(self, parent_config_id: str) -> List[AgentConfig]:
        """Get child agents of a parent."""
        child_ids = self._children.get(parent_config_id, [])
        return [self._agents[cid] for cid in child_ids if cid in self._agents]

    def get_all_agents(self) -> List[AgentConfig]:
        """Get all agents."""
        return list(self._agents.values())

    # --- Subflow/state lookups ---

    def get_subflow(self, agent_id: str, subflow_id: str) -> Optional[SubflowConfig]:
        """Get subflow by agent and subflow config_ids."""
        agent = self._agents.get(agent_id)
        if agent:
            return agent.get_subflow(subflow_id)
        return None

    def get_flow_state(
        self, agent_id: str, subflow_id: str, state_id: str
    ) -> Optional[SubflowStateConfig]:
        """Get flow state by agent, subflow, and state ids."""
        subflow = self.get_subflow(agent_id, subflow_id)
        if subflow:
            return subflow.states.get(state_id)
        return None

    # --- Tool/routing lookups ---

    def get_tool(self, agent_id: str, tool_name: str) -> Optional[ToolConfig]:
        """Get tool by agent and tool name."""
        agent = self._agents.get(agent_id)
        if agent:
            return agent.get_tool(tool_name)
        return None

    def get_tool_routing(self, tool_name: str) -> RoutingConfig:
        """Get routing config for a tool. Returns SERVICE type if not found."""
        config = self._tool_routing.get(tool_name)
        if config is None:
            return RoutingConfig(type=RoutingType.SERVICE, target=None)
        return config

    def resolve_routing(self, tool_name: str) -> RoutingResult:
        """Resolve routing for a tool call. Returns target config objects."""
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
                target_id=agent.config_id,
                target_entity=agent
            )

        elif routing.type == RoutingType.START_FLOW:
            # For flows, the caller must provide current agent context
            # Return the routing target for the caller to resolve
            return RoutingResult(
                success=True,
                action=routing.type,
                target_id=routing.target,
                target_entity=None  # Subflow resolved by caller with agent context
            )

        elif routing.type == RoutingType.NAVIGATION:
            return RoutingResult(
                success=True,
                action=routing.type,
                target_id=routing.target,
                target_entity=None
            )

        else:  # SERVICE
            return RoutingResult(
                success=True,
                action=routing.type,
                target_id=None,
                target_entity=None
            )


# --- Singleton pattern ---

_registry: Optional[AgentRegistry] = None


def get_agent_registry() -> AgentRegistry:
    """Get the global AgentRegistry instance."""
    global _registry
    if _registry is None:
        raise RuntimeError(
            "AgentRegistry not initialized. Call initialize_agent_registry() first."
        )
    return _registry


def initialize_agent_registry() -> AgentRegistry:
    """Initialize the global AgentRegistry. Called at startup."""
    global _registry
    _registry = AgentRegistry()
    _registry.initialize()
    return _registry


def reset_agent_registry() -> None:
    """Reset the registry (for testing)."""
    global _registry
    _registry = None
