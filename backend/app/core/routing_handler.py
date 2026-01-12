"""Unified routing handler for the orchestrator."""

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import ConversationSession
from app.models.agent import Agent
from app.core.routing import RoutingType, RoutingOutcome
from app.core.routing_registry import RoutingRegistry
from app.core.state_manager import StateManager
from app.core.template_renderer import TemplateRenderer

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
        routing_registry: RoutingRegistry,
        state_manager: StateManager,
        template_renderer: TemplateRenderer,
    ):
        self.db = db
        self.registry = routing_registry
        self.state_manager = state_manager
        self.template_renderer = template_renderer

    async def handle_tool_routing(
        self,
        tool_name: str,
        tool_params: dict,
        session: ConversationSession,
        current_agent: Agent,
    ) -> RoutingOutcome:
        """
        Handle routing for a tool call.

        Returns a RoutingOutcome indicating what the orchestrator should do next.
        """
        # Get both the routing config (for cross_agent) and resolved result
        routing_config = self.registry.get_tool_routing(tool_name)
        result = self.registry.resolve_routing(tool_name)

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
            return await self._handle_start_flow(result, routing_config, session, current_agent)

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

        await self.state_manager.push_agent(
            session,
            result.target_id,
            f"User requested {agent.config_id}"
        )

        logger.info(f"Routing: entered agent {agent.config_id}")

        return RoutingOutcome(
            handled=True,
            state_changed=True,  # Agent changed
            context_requirements=[],
            response_text=None
        )

    async def _handle_start_flow(
        self,
        result,
        routing_config,
        session: ConversationSession,
        current_agent: Agent,
    ) -> RoutingOutcome:
        """Handle starting a subflow, including cross-agent flows."""
        subflow = result.target_entity

        # Handle cross-agent flows: enter target agent first
        if routing_config.cross_agent:
            cross_agent = self.registry.get_agent(routing_config.cross_agent)
            if cross_agent:
                await self.state_manager.push_agent(
                    session,
                    str(cross_agent.id),
                    f"Cross-agent flow: {subflow.config_id}"
                )
                logger.info(f"Routing: entered cross-agent {cross_agent.config_id} for flow {subflow.config_id}")
            else:
                logger.warning(f"Cross-agent {routing_config.cross_agent} not found, starting flow in current agent")

        await self.state_manager.enter_subflow(session, subflow)

        logger.info(f"Routing: started flow {subflow.config_id}")

        return RoutingOutcome(
            handled=True,
            state_changed=True,  # Flow started
            context_requirements=[],  # on_enter will handle requirements via enrichment
            response_text=None
        )

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
            return RoutingOutcome(
                handled=True,
                state_changed=True,  # Popped to parent agent
                context_requirements=[],
                response_text=None
            )

        elif action == "go_home":
            await self.state_manager.go_home(session)
            logger.info("Routing: navigated home")
            return RoutingOutcome(
                handled=True,
                state_changed=True,  # Returned to root
                context_requirements=[],
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

