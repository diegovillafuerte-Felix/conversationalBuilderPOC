"""
Context Enrichment - Eagerly loads all data needed for current state.

This module executes on_enter actions and fetches required context data
BEFORE the LLM is called, ensuring all necessary information is available.
"""

import logging
from typing import Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.session import ConversationSession
from app.models.agent import Agent, Tool
from app.models.subflow import Subflow, SubflowState
from app.core.tool_executor import ToolExecutor, ToolResult

logger = logging.getLogger(__name__)


class ContextEnrichment:
    """
    Enriches session state with data needed for current context.

    Executes on_enter actions (callTool, fetchContext) and fetches
    context requirements before the LLM is called.
    """

    def __init__(self, db: AsyncSession, tool_executor: ToolExecutor):
        self.db = db
        self.tool_executor = tool_executor

    async def enrich_state(
        self,
        session: ConversationSession,
        agent: Agent,
        context_requirements: list[str]
    ) -> Dict[str, Any]:
        """
        Fetch all required data upfront.

        Enrichment happens in three layers:
        1. Agent-level context requirements (from agent.context_requirements)
        2. Flow on_enter actions (if in a flow)
        3. Routing context requirements (from routing outcome)

        Args:
            session: Current conversation session
            agent: Current agent
            context_requirements: List of data keys to fetch

        Returns:
            Dict of enriched data to merge into session state
        """
        enriched_data = {}

        # LAYER 1: Agent-level context requirements
        # These ensure agents get baseline context even without a flow
        if agent.context_requirements:
            logger.info(f"Processing agent-level context requirements for {agent.config_id}")
            for req_config in agent.context_requirements:
                req_type = req_config.get("type")

                if req_type == "product_summary":
                    # Fetch product-specific summary data
                    product = req_config.get("productFilter")
                    if product == "topups":
                        # TopUps needs frequent numbers
                        data = await self._fetch_context_requirement(
                            "frequent_numbers", session, agent
                        )
                        if data:
                            enriched_data["frequentNumbersData"] = data
                            logger.info("Loaded frequent numbers for TopUps agent")

                    elif product == "remittances":
                        # Remittances needs recipient list
                        data = await self._fetch_context_requirement(
                            "recipient_list", session, agent
                        )
                        if data:
                            enriched_data["recipientList"] = data
                            logger.info("Loaded recipient list for Remittances agent")

                elif req_type == "recent_transactions":
                    # Could fetch recent transactions summary
                    pass

        # LAYER 2: Flow on_enter actions (if in a flow)
        if session.current_flow:
            flow_state = await self._get_current_flow_state(session)
            if flow_state and flow_state.on_enter:
                await self._execute_on_enter(
                    flow_state.on_enter,
                    session,
                    agent,
                    enriched_data
                )

        # LAYER 3: Routing context requirements
        for requirement in context_requirements:
            if requirement not in enriched_data:  # Don't duplicate
                data = await self._fetch_context_requirement(
                    requirement,
                    session,
                    agent
                )
                if data:
                    enriched_data[requirement] = data

        logger.info(f"Context enrichment complete: {len(enriched_data)} total items")
        return enriched_data

    async def _get_current_flow_state(
        self,
        session: ConversationSession
    ) -> Optional[SubflowState]:
        """Get the current flow state from database."""
        if not session.current_flow:
            return None

        flow_id = session.current_flow.get("flowId")
        state_id = session.current_flow.get("currentState")

        if not flow_id or not state_id:
            return None

        result = await self.db.execute(
            select(SubflowState)
            .where(SubflowState.subflow_id == flow_id)
            .where(SubflowState.state_id == state_id)
        )
        return result.scalar_one_or_none()

    async def _execute_on_enter(
        self,
        on_enter: Dict,
        session: ConversationSession,
        agent: Agent,
        enriched_data: Dict
    ):
        """Execute all on_enter actions (callTool, fetchContext)."""

        # Execute callTool actions
        if on_enter.get("callTool"):
            tool_config = on_enter["callTool"]
            await self._execute_on_enter_tool(tool_config, session, agent, enriched_data)

        # Execute fetchContext actions
        if on_enter.get("fetchContext"):
            context_keys = on_enter["fetchContext"]
            if isinstance(context_keys, str):
                context_keys = [context_keys]
            for context_key in context_keys:
                data = await self._fetch_context_requirement(
                    context_key,
                    session,
                    agent
                )
                enriched_data[context_key] = data

    async def _execute_on_enter_tool(
        self,
        tool_config: Dict,
        session: ConversationSession,
        agent: Agent,
        enriched_data: Dict
    ):
        """Execute a single tool from on_enter.callTool."""
        tool_name = tool_config.get("name")
        tool_params = tool_config.get("parameters", {})

        if not tool_name:
            logger.warning("on_enter.callTool missing 'name' field")
            return

        logger.info(f"Executing on_enter tool: {tool_name}")

        try:
            # Find the tool definition
            tool = None
            for t in agent.tools:
                if t.name == tool_name:
                    tool = t
                    break

            if not tool:
                logger.warning(f"Tool {tool_name} not found in agent {agent.config_id}")
                return

            # Execute the tool
            result = await self.tool_executor.execute(tool, tool_params, session)

            # Store result in enriched_data if successful
            if result and result.success and result.data:
                store_key = tool_config.get("storeAs", tool_name)
                enriched_data[store_key] = result.data
                logger.info(f"Stored on_enter tool result as '{store_key}'")
            else:
                logger.warning(f"on_enter tool {tool_name} failed or returned no data")

        except Exception as e:
            logger.error(f"Error executing on_enter tool {tool_name}: {e}", exc_info=True)

    async def _fetch_context_requirement(
        self,
        requirement: str,
        session: ConversationSession,
        agent: Agent
    ) -> Any:
        """
        Fetch a specific context requirement.

        This maps requirement keys to tool calls or data fetching logic.
        Examples: "frequent_numbers", "user_limits", "recipient_list"
        """
        logger.info(f"Fetching context requirement: {requirement}")

        # Map requirements to tool names
        requirement_to_tool = {
            "frequent_numbers": "get_frequent_numbers",
            "user_limits": "get_user_limits",
            "recipient_list": "list_recipients",
            "exchange_rates": "get_exchange_rate",
        }

        tool_name = requirement_to_tool.get(requirement)
        if not tool_name:
            logger.warning(f"Unknown context requirement: {requirement}")
            return None

        # Find and execute the tool
        tool = None
        for t in agent.tools:
            if t.name == tool_name:
                tool = t
                break

        if not tool:
            logger.warning(f"Tool {tool_name} for requirement '{requirement}' not found")
            return None

        try:
            result = await self.tool_executor.execute(tool, {}, session)
            if result and result.success:
                return result.data
            return None
        except Exception as e:
            logger.error(f"Error fetching context requirement {requirement}: {e}")
            return None