"""Unified routing handler for the orchestrator."""

import logging
from typing import Optional, TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import ConversationSession
from app.core.config_types import AgentConfig, SubflowConfig
from app.core.routing import RoutingType, RoutingOutcome
from app.core.agent_registry import get_agent_registry
from app.core.state_manager import StateManager
from app.core.template_renderer import TemplateRenderer
from app.core.event_trace import EventCategory

if TYPE_CHECKING:
    from app.core.event_trace import EventTracer

logger = logging.getLogger(__name__)


class RoutingHandler:
    """
    Handles all routing actions uniformly.

    Consolidates logic for:
    - Entering child agents
    - Starting subflows
    - Navigation (up, home, escalate)
    """

    def __init__(
        self,
        db: AsyncSession,
        state_manager: StateManager,
        template_renderer: TemplateRenderer,
        tracer: Optional["EventTracer"] = None,
    ):
        self.db = db
        self.state_manager = state_manager
        self.template_renderer = template_renderer
        self.tracer = tracer

    async def handle_tool_routing(
        self,
        tool_name: str,
        tool_params: dict,
        session: ConversationSession,
        current_agent: AgentConfig,
    ) -> RoutingOutcome:
        """
        Handle routing for a tool call.

        Returns a RoutingOutcome indicating what the orchestrator should do next.
        """
        registry = get_agent_registry()
        # Get both the routing config (for cross_agent) and resolved result
        routing_config = registry.get_tool_routing(tool_name)
        result = registry.resolve_routing(tool_name)

        # SERVICE tools are not routing - let orchestrator handle normally
        if result.action == RoutingType.SERVICE:
            return RoutingOutcome(
                handled=False,
                state_changed=False,
                context_requirements=[],
                response_text=None
            )

        if not result.success:
            logger.error(f"Routing resolution failed for {tool_name}: {result.error}")
            return RoutingOutcome(
                handled=True,
                state_changed=False,
                context_requirements=[],
                response_text=None,
                error=result.error
            )

        if result.action == RoutingType.ENTER_AGENT:
            return await self._handle_enter_agent(result, session)

        elif result.action == RoutingType.START_FLOW:
            return await self._handle_start_flow(result, routing_config, session, current_agent, tool_params)

        elif result.action == RoutingType.NAVIGATION:
            return await self._handle_navigation(result, session, tool_params)

        else:
            logger.error(f"Unknown routing action: {result.action}")
            return RoutingOutcome(
                handled=True,
                state_changed=False,
                context_requirements=[],
                response_text=None,
                error=f"Unknown routing action: {result.action}"
            )

    async def _handle_enter_agent(
        self,
        result,
        session: ConversationSession,
    ) -> RoutingOutcome:
        """Handle entering a child agent."""
        agent = result.target_entity
        previous_agent_id = session.get_current_agent_id() if session.agent_stack else None

        await self.state_manager.push_agent(
            session,
            agent.config_id,
            f"User requested {agent.config_id}"
        )

        logger.info(f"Routing: entered agent {agent.config_id}")

        # Trace: agent changed
        if self.tracer:
            self.tracer.trace(
                EventCategory.AGENT,
                "agent_changed",
                f"Entered agent: {agent.config_id}",
                data={
                    "previous_agent_id": previous_agent_id,
                    "new_agent_id": agent.config_id,
                    "stack_depth": len(session.agent_stack)
                }
            )

        return RoutingOutcome(
            handled=True,
            state_changed=True,  # Agent changed
            context_requirements=agent.context_requirements or [],
            response_text=None
        )

    async def _handle_start_flow(
        self,
        result,
        routing_config,
        session: ConversationSession,
        current_agent: AgentConfig,
        tool_params: dict,
    ) -> RoutingOutcome:
        """Handle starting a subflow, including cross-agent flows."""
        registry = get_agent_registry()

        # Handle cross-agent flows: enter target agent first
        target_agent = current_agent
        if routing_config.cross_agent:
            cross_agent = registry.get_agent(routing_config.cross_agent)
            if cross_agent:
                await self.state_manager.push_agent(
                    session,
                    cross_agent.config_id,
                    f"Cross-agent flow: {result.target_id}"
                )
                target_agent = cross_agent
                logger.info(f"Routing: entered cross-agent {cross_agent.config_id} for flow {result.target_id}")

                # Trace: cross-agent transition
                if self.tracer:
                    self.tracer.trace(
                        EventCategory.AGENT,
                        "cross_agent_entered",
                        f"Entered cross-agent: {cross_agent.config_id}",
                        data={
                            "cross_agent_id": cross_agent.config_id,
                            "for_flow": result.target_id
                        }
                    )
            else:
                logger.warning(f"Cross-agent {routing_config.cross_agent} not found, starting flow in current agent")

        # Resolve the subflow from the target agent
        subflow = registry.get_subflow(target_agent.config_id, result.target_id)
        if not subflow:
            return RoutingOutcome(
                handled=True,
                state_changed=False,
                context_requirements=[],
                response_text=None,
                error=f"Subflow {result.target_id} not found in agent {target_agent.config_id}"
            )

        # Extract initial data from tool parameters
        initial_data = self._extract_flow_initial_data(tool_params, subflow)

        await self.state_manager.enter_subflow(session, subflow, initial_data)

        logger.info(f"Routing: started flow {subflow.config_id} with initial_data keys: {list(initial_data.keys())}")

        # Trace: flow started
        if self.tracer:
            self.tracer.trace(
                EventCategory.FLOW,
                "flow_started",
                f"Started flow: {subflow.config_id}",
                data={
                    "flow_config_id": subflow.config_id,
                    "initial_state": subflow.initial_state,
                    "initial_data_keys": list(initial_data.keys()),
                    "agent_id": target_agent.config_id
                }
            )

        return RoutingOutcome(
            handled=True,
            state_changed=True,  # Flow started
            context_requirements=target_agent.context_requirements or [],
            response_text=None
        )

    def _extract_flow_initial_data(self, tool_params: dict, subflow: SubflowConfig) -> dict:
        """Extract flow-relevant parameters from tool call."""
        if not tool_params:
            return {}

        initial_data = {}

        # If subflow has data_schema, use its keys directly from tool params
        if subflow.data_schema:
            for schema_key in subflow.data_schema:
                if schema_key in tool_params and tool_params[schema_key] is not None:
                    initial_data[schema_key] = tool_params[schema_key]

        # Fallback: hardcoded mappings for common params (including cross-agent renames)
        param_mappings = {
            "phone_number": "phone_number",
            "recipient_id": "recipient_id",
            "amount": "amount",
            "amount_usd": "amount_usd",
            "carrier_id": "carrier_id",
            "loan_id": "snpl_loan_id",
            "snpl_loan_id": "snpl_loan_id",
        }

        for param_key, data_key in param_mappings.items():
            if param_key in tool_params and tool_params[param_key] and data_key not in initial_data:
                initial_data[data_key] = tool_params[param_key]

        if initial_data:
            logger.info(f"Flow initial data keys: {list(initial_data.keys())}")

        return initial_data

    async def _handle_navigation(
        self,
        result,
        session: ConversationSession,
        tool_params: dict,
    ) -> RoutingOutcome:
        """Handle navigation actions."""
        action = result.target_id

        if action == "up_one_level":
            await self.state_manager.pop_agent(session)
            logger.info("Routing: navigated up one level")
            current_agent = self.state_manager.get_current_agent(session)
            return RoutingOutcome(
                handled=True,
                state_changed=True,  # Popped to parent agent
                context_requirements=current_agent.context_requirements if current_agent else [],
                response_text=None
            )

        elif action == "go_home":
            await self.state_manager.go_home(session)
            logger.info("Routing: navigated home")
            current_agent = self.state_manager.get_current_agent(session)
            return RoutingOutcome(
                handled=True,
                state_changed=True,  # Returned to root
                context_requirements=current_agent.context_requirements if current_agent else [],
                response_text=None
            )

        elif action == "escalate_to_human":
            reason = tool_params.get("reason", "User request")
            await self.state_manager.escalate(session, reason)
            logger.info(f"Routing: escalated to human - {reason}")
            return RoutingOutcome(
                handled=True,
                state_changed=False,  # No state change, conversation ends
                context_requirements=[],
                response_text="Entiendo. Te voy a conectar con un agente humano que podrá ayudarte mejor. Un momento por favor..."
            )

        else:
            logger.error(f"Unknown navigation action: {action}")
            return RoutingOutcome(
                handled=True,
                state_changed=False,
                context_requirements=[],
                response_text=None,
                error=f"Unknown navigation action: {action}"
            )
