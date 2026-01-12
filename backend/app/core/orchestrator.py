"""Main orchestrator for handling conversation flow."""

import asyncio
import logging
import time
from typing import Optional, List, Any
from uuid import UUID
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.agent import Agent, Tool, ResponseTemplate
from app.models.session import ConversationSession
from app.models.user import UserContext
from app.models.conversation import ConversationMessage
from app.models.subflow import Subflow, SubflowState
from app.core.llm_client import LLMClient, LLMResponse, ToolCall, get_llm_client
from app.core.context_assembler import ContextAssembler, get_context_assembler
from app.core.state_manager import StateManager
from app.core.tool_executor import ToolExecutor, ToolResult, get_tool_executor
from app.core.template_renderer import TemplateRenderer, get_template_renderer
from app.core.routing import RoutingType, RoutingOutcome
from app.core.routing_registry import get_routing_registry
from app.core.routing_handler import RoutingHandler
from app.core.history_compactor import HistoryCompactor
from app.core.i18n import get_message
from app.core.config_loader import load_shadow_service_config
from app.core.shadow_service import (
    ShadowService,
    ShadowServiceConfig,
    ShadowResult,
    ShadowMessage,
)

logger = logging.getLogger(__name__)


@dataclass
class DebugLLMCall:
    """Debug information about an LLM call."""
    system_prompt: str
    messages: List[dict]
    tools_provided: List[str]
    model: str
    temperature: float
    raw_response: Optional[str] = None
    token_counts: Optional[dict] = None


@dataclass
class DebugInfo:
    """Debug information for developer view."""
    llm_call: Optional[DebugLLMCall] = None
    agent_stack: List[dict] = field(default_factory=list)
    flow_info: Optional[dict] = None
    context_sections: Optional[dict] = None
    processing_time_ms: Optional[int] = None


@dataclass
class OrchestratorResponse:
    """Response from the orchestrator."""

    session_id: UUID
    message: str
    agent_id: str
    agent_name: str
    tool_calls: List[dict]
    pending_confirmation: Optional[dict] = None
    flow_state: Optional[str] = None
    escalated: bool = False
    shadow_messages: List[ShadowMessage] = field(default_factory=list)
    debug: Optional[DebugInfo] = None


class Orchestrator:
    """Main orchestrator for handling user messages."""

    def __init__(
        self,
        db: AsyncSession,
        llm_client: Optional[LLMClient] = None,
        context_assembler: Optional[ContextAssembler] = None,
        tool_executor: Optional[ToolExecutor] = None,
        template_renderer: Optional[TemplateRenderer] = None,
        shadow_service: Optional[ShadowService] = None,
    ):
        self.db = db
        self.llm_client = llm_client or get_llm_client()
        self.context_assembler = context_assembler or get_context_assembler()
        self.tool_executor = tool_executor or get_tool_executor()
        self.template_renderer = template_renderer or get_template_renderer()
        self.state_manager = StateManager(db)
        self.routing_handler: Optional[RoutingHandler] = None

        # Initialize context enrichment
        from app.core.context_enrichment import ContextEnrichment
        self.context_enrichment = ContextEnrichment(db, self.tool_executor)

        # Initialize shadow service
        if shadow_service:
            self.shadow_service = shadow_service
        else:
            shadow_config_dict = load_shadow_service_config()
            shadow_config = ShadowServiceConfig.from_dict(shadow_config_dict)
            self.shadow_service = ShadowService(self.llm_client, shadow_config)

    async def handle_message(
        self,
        user_message: str,
        user_id: str,
        session_id: Optional[UUID] = None,
    ) -> OrchestratorResponse:
        """
        Handle a user message with three-phase flow.

        Phase 1: Routing & State Changes
        Phase 2: Context Enrichment (after state changes)
        Phase 3: LLM Response Generation
        """
        start_time = time.time()

        # === SETUP ===
        root_agent = await self._get_root_agent()
        if not root_agent:
            raise ValueError("No root agent configured")

        session = await self.state_manager.get_or_create_session(
            session_id, user_id, str(root_agent.id)
        )

        # Check for pending confirmation
        if session.pending_confirmation:
            return await self._handle_confirmation_response(session, user_message)

        # Get current agent
        agent = await self.state_manager.get_current_agent(session)
        if not agent:
            agent = root_agent
            session.agent_stack = [
                {
                    "agentId": str(root_agent.id),
                    "enteredAt": "now",
                    "entryReason": "Session start",
                }
            ]

        # Load agent's tools, subflows, and response templates
        await self.db.refresh(agent, ["tools", "subflows", "response_templates"])

        # Get user context and set language
        user_context = await self._get_user_context(user_id)
        language = user_context.get_language() if user_context else "es"
        self.tool_executor.set_language(language)

        # === PHASE 2: CONTEXT ENRICHMENT ===
        # Run enrichment if state just changed or entering a new flow state
        if self._should_enrich_context(session):
            try:
                enriched_data = await self.context_enrichment.enrich_state(
                    session=session,
                    agent=agent,
                    context_requirements=[]
                )
                await self._merge_enriched_data(session, enriched_data)
                await self.db.commit()
                logger.info(f"Context enrichment completed: {len(enriched_data)} items")
            except Exception as e:
                logger.error(f"Context enrichment failed (non-blocking): {e}")

        # === PHASE 3: LLM RESPONSE GENERATION ===

        # Get recent messages
        recent_messages = await self._get_recent_messages(session.session_id)

        # Check for history compaction
        compactor = HistoryCompactor(self.db)
        compacted_history = None
        if await compactor.should_compact(str(session.session_id)):
            await compactor.compact_history(user_id, str(session.session_id))
            recent_messages = await self._get_recent_messages(session.session_id)

        compacted_history = await compactor.get_compacted_history(user_id)

        # Get current flow state
        flow_state = await self.state_manager.get_current_flow_state(session)

        # Assemble context with enriched data
        context = self.context_assembler.assemble(
            session=session,
            user_message=user_message,
            agent=agent,
            user_context=user_context,
            recent_messages=recent_messages,
            compacted_history=compacted_history,
            current_flow_state=flow_state,
        )

        logger.debug(f"Context assembled: {context.token_counts}")

        # Call LLM and shadow service in parallel
        async def run_main_llm():
            return await self.llm_client.complete(
                system_prompt=context.system_prompt,
                messages=context.messages,
                tools=context.tools if context.tools else None,
                model=context.model,
                temperature=context.temperature,
                max_tokens=context.max_tokens,
            )

        async def run_shadow_service():
            try:
                return await self.shadow_service.evaluate(
                    user_message=user_message,
                    session=session,
                    user_context=user_context,
                    recent_messages=recent_messages,
                    language=language,
                )
            except Exception as e:
                logger.error(f"Shadow service error (non-blocking): {e}")
                return ShadowResult()

        llm_response, shadow_result = await asyncio.gather(
            run_main_llm(),
            run_shadow_service(),
        )

        # Check for shadow activation (takeover) - can recurse, this is intentional
        if shadow_result.has_activation:
            activation = shadow_result.activation
            logger.info(
                f"Shadow takeover: {activation.subagent_id} -> {activation.target_agent_id} "
                f"(intent: {activation.intent})"
            )
            await self.state_manager.push_agent(
                session,
                activation.target_agent_id,
                reason=f"Shadow takeover: {activation.intent}",
                preserve_flow=True,
            )
            # Recurse with new agent context (intentional for shadow takeover)
            return await self.handle_message(user_message, user_id, session.session_id)

        # Capture debug info
        debug_llm_call = DebugLLMCall(
            system_prompt=context.system_prompt,
            messages=context.messages,
            tools_provided=[t["name"] for t in context.tools] if context.tools else [],
            model=context.model,
            temperature=context.temperature,
            raw_response=llm_response.text,
            token_counts=context.token_counts,
        )

        # Process tool calls
        tool_call_records = []
        response_text = llm_response.text

        for tool_call in llm_response.tool_calls:
            result = await self._process_tool_call(session, agent, tool_call)
            tool_call_records.append({
                "name": tool_call.name,
                "params": tool_call.parameters,
                "result": result.data if result else None,
            })

            # Check for routing outcome
            if result and result.data and isinstance(result.data, dict):
                routing_outcome_data = result.data.get("_routing_outcome")
                if routing_outcome_data:
                    routing_outcome = RoutingOutcome.from_dict(routing_outcome_data)

                    # NO RECURSION - enrichment happens on next message
                    if routing_outcome.state_changed:
                        # State changed, enrichment will trigger on next user message
                        pass

                    if routing_outcome.response_text:
                        response_text = routing_outcome.response_text
                        break

                    continue

            # Check for confirmation requirement
            if result and result.requires_confirmation:
                await self.state_manager.set_pending_confirmation(
                    session,
                    tool_call.name,
                    tool_call.parameters,
                    result.confirmation_message,
                )
                response_text = result.confirmation_message
                break

            # Handle flow transitions
            if result and result.success and session.current_flow:
                tool = await self._get_tool_by_name(agent, tool_call.name)
                if tool and tool.flow_transition:
                    transition_result = await self._handle_flow_transition(
                        session, agent, tool, result
                    )
                    if transition_result:
                        response_text = transition_result
                        break

        # Record messages
        await self._record_messages(session, user_message, response_text, tool_call_records, agent)

        # Update session
        await self.state_manager.increment_message_count(session)
        await self.db.commit()

        # Build debug info
        processing_time_ms = int((time.time() - start_time) * 1000)
        debug_info = DebugInfo(
            llm_call=debug_llm_call,
            agent_stack=session.agent_stack or [],
            flow_info=session.current_flow,
            context_sections=context.token_counts,
            processing_time_ms=processing_time_ms,
        )

        # Update shadow cooldowns
        if shadow_result.has_messages:
            triggered_ids = [m.subagent_id for m in shadow_result.messages]
            self.shadow_service.update_cooldowns(session, triggered_ids)

        return OrchestratorResponse(
            session_id=session.session_id,
            message=response_text,
            agent_id=str(agent.id),
            agent_name=agent.name,
            tool_calls=tool_call_records,
            pending_confirmation=session.pending_confirmation,
            flow_state=session.current_flow.get("currentState") if session.current_flow else None,
            escalated=session.status == "escalated",
            shadow_messages=shadow_result.messages,
            debug=debug_info,
        )

    async def _handle_confirmation_response(
        self, session: ConversationSession, user_message: str
    ) -> OrchestratorResponse:
        """Handle a response to a pending confirmation."""
        agent = await self.state_manager.get_current_agent(session)
        await self.db.refresh(agent, ["tools", "response_templates"])

        # Check if confirmation expired
        if self.state_manager.is_confirmation_expired(session):
            await self.state_manager.clear_pending_confirmation(session)
            return await self.handle_message(user_message, session.user_id, session.session_id)

        # Classify user response
        is_confirmed = self.tool_executor.classify_user_confirmation(user_message)

        if is_confirmed is True:
            # Execute the confirmed tool
            pending = session.pending_confirmation
            tool = await self._get_tool_by_name(agent, pending["toolName"])

            if tool:
                result = await self.tool_executor.execute(
                    tool, pending["toolParams"], session, skip_confirmation=True
                )

                # Clear confirmation
                await self.state_manager.clear_pending_confirmation(session)

                if result.success:
                    # LLM handles formatting now
                    response_text = "✅ Operación completada exitosamente. ¿En qué más puedo ayudarte?"

                    # Handle flow transition if applicable
                    if session.current_flow and tool.flow_transition:
                        transition_result = await self._handle_flow_transition(
                            session, agent, tool, result
                        )
                        if transition_result:
                            response_text = transition_result
                else:
                    response_text = f"Lo siento, hubo un error: {result.error}"
            else:
                # Tool not found, execute as mock
                result = await self.tool_executor.execute_mock(
                    pending["toolName"], pending["toolParams"], session.user_id
                )
                await self.state_manager.clear_pending_confirmation(session)
                response_text = "Listo, la operación se completó exitosamente."

        elif is_confirmed is False:
            # User declined
            await self.state_manager.clear_pending_confirmation(session)
            response_text = "Entendido, he cancelado la operación. ¿En qué más puedo ayudarte?"

        else:
            # Unclear response, ask again
            response_text = f"No entendí tu respuesta. {session.pending_confirmation['displayMessage']}\n\n¿Confirmas? (Sí/No)"

        # Record the exchange
        await self._record_messages(session, user_message, response_text, [], agent)
        await self.state_manager.increment_message_count(session)
        await self.db.commit()

        return OrchestratorResponse(
            session_id=session.session_id,
            message=response_text,
            agent_id=str(agent.id),
            agent_name=agent.name,
            tool_calls=[],
            pending_confirmation=session.pending_confirmation,
            escalated=session.status == "escalated",
        )

    async def _handle_flow_transition(
        self,
        session: ConversationSession,
        agent: Agent,
        tool: Tool,
        result: ToolResult,
    ) -> Optional[str]:
        """
        Handle flow state transition after tool execution.

        Returns a response message if a transition occurred, None otherwise.
        """
        if not session.current_flow or not tool.flow_transition:
            return None

        flow_transition = tool.flow_transition
        target_state_id = None

        if result.success and flow_transition.get("onSuccess"):
            target_state_id = flow_transition["onSuccess"]
        elif not result.success and flow_transition.get("onError"):
            target_state_id = flow_transition["onError"]

        if not target_state_id:
            return None

        # Get the target state definition
        target_state = await self.state_manager.get_flow_state(
            session.current_flow["flowId"], target_state_id
        )

        if not target_state:
            logger.warning(f"Target state {target_state_id} not found in flow")
            return None

        # Update flow data from tool result
        if result.data and isinstance(result.data, dict):
            await self.state_manager.update_flow_data(session, result.data)

        # Perform the transition
        await self.state_manager.transition_state(session, target_state_id, target_state)

        # Handle on_enter actions for the new state
        response_text = None
        if target_state.on_enter:
            response_text = await self._handle_on_enter(target_state, session, agent)

        return response_text

    async def _handle_on_enter(
        self,
        state: SubflowState,
        session: ConversationSession,
        agent: Agent,
    ) -> Optional[str]:
        """Handle on_enter actions when entering a state."""
        if not state.on_enter:
            return None

        on_enter = state.on_enter
        response_text = None

        # Handle callTool action (execute tool automatically on state entry)
        if on_enter.get("callTool"):
            tool_config = on_enter["callTool"]
            tool_name = tool_config.get("name")
            tool_params = tool_config.get("parameters", {})

            if tool_name:
                logger.info(f"Executing on_enter tool: {tool_name}")
                try:
                    # Create a ToolCall object
                    from app.core.llm_client import ToolCall
                    tool_call = ToolCall(name=tool_name, parameters=tool_params)

                    # Execute the tool
                    result = await self._process_tool_call(session, agent, tool_call)

                    # Store result in flow data if specified
                    if result and result.success and tool_config.get("storeAs"):
                        flow_data = session.current_flow.get("stateData", {}) if session.current_flow else {}
                        flow_data[tool_config["storeAs"]] = result.data
                        await self.state_manager.update_flow_data(session, flow_data)

                    # Store the raw data - formatting will be handled by templates or LLM
                    if result and result.success and result.data:
                        # Let the message template or LLM handle formatting
                        pass

                except Exception as e:
                    logger.error(f"Error executing on_enter tool {tool_name}: {e}")

        # Handle message action (check both "message" and "sendMessage" keys)
        template = on_enter.get("message") or on_enter.get("sendMessage")
        if template:
            # Handle language-specific templates (e.g., {"en": "...", "es": "..."})
            if isinstance(template, dict) and ("en" in template or "es" in template):
                user_context = await self._get_user_context(session.user_id)
                language = user_context.get_language() if user_context else "es"
                template = template.get(language) or template.get("es") or template.get("en") or ""

            # Render template with flow data
            flow_data = session.current_flow.get("stateData", {}) if session.current_flow else {}
            rendered_message = self.template_renderer.render(template, flow_data)

            # Combine with tool response if both exist
            if response_text:
                response_text = f"{response_text}\n\n{rendered_message}"
            else:
                response_text = rendered_message

        # Handle fetchContext action (just log for now, context is re-assembled on next message)
        if on_enter.get("fetchContext"):
            logger.info(f"State {state.name} requests additional context: {on_enter['fetchContext']}")

        return response_text

    def _should_enrich_context(self, session: ConversationSession) -> bool:
        """
        Determine if context enrichment should run.

        Returns True if:
        - In a flow and this is the first message in current state
        - Session metadata indicates state just changed
        """
        if not session.current_flow:
            return False

        # Check if state just changed (no enrichment done for current state yet)
        if not session.session_metadata:
            return True

        last_enrichment_state = session.session_metadata.get("last_enrichment_state")
        current_state = session.current_flow.get("currentState")

        return last_enrichment_state != current_state

    async def _merge_enriched_data(
        self, session: ConversationSession, enriched_data: dict
    ):
        """Merge enriched data into session.current_flow.stateData."""
        if not session.current_flow:
            return

        if "stateData" not in session.current_flow:
            session.current_flow["stateData"] = {}

        session.current_flow["stateData"].update(enriched_data)

        # Mark that enrichment was done for this state
        if not session.session_metadata:
            session.session_metadata = {}
        session.session_metadata["last_enrichment_state"] = session.current_flow.get("currentState")


    async def _process_tool_call(
        self, session: ConversationSession, agent: Agent, tool_call: ToolCall
    ) -> Optional[ToolResult]:
        """Process a single tool call."""
        tool_name = tool_call.name

        # Handle change_language tool
        if tool_name == "change_language":
            language = tool_call.parameters.get("language", "es")
            # Validate language
            if language not in ["en", "es"]:
                language = "es"

            # Update user context
            user_context = await self._get_user_context(session.user_id)
            if user_context:
                if user_context.profile is None:
                    user_context.profile = {}
                user_context.profile["language"] = language
                await self.db.commit()

            # Update tool executor language
            self.tool_executor.set_language(language)

            # Return localized confirmation
            message = get_message("language.changed", language)
            return ToolResult(success=True, data={"_message": message, "language": language})

        # Try routing first (handles navigation, agent entry, flow start)
        routing_handler = await self._ensure_routing_handler()
        routing_outcome = await routing_handler.handle_tool_routing(
            tool_name, tool_call.parameters, session, agent
        )

        if routing_outcome.handled:
            # Return a special result that signals the orchestrator
            if routing_outcome.error:
                logger.error(f"Routing error for {tool_name}: {routing_outcome.error}")
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"Routing failed: {routing_outcome.error}"
                )
            return ToolResult(
                success=True,
                data={"_routing_outcome": routing_outcome.to_dict()}
            )

        # Not a routing tool - find and execute the tool definition
        tool = await self._get_tool_by_name(agent, tool_name)

        if tool:
            return await self.tool_executor.execute(
                tool, tool_call.parameters, session
            )

        # If no tool found, try mock execution (for service tools without DB definition)
        return await self.tool_executor.execute_mock(
            tool_name, tool_call.parameters, session.user_id
        )


    async def _get_root_agent(self) -> Optional[Agent]:
        """Get the root orchestrator agent."""
        result = await self.db.execute(
            select(Agent)
            .where(Agent.parent_agent_id.is_(None))
            .where(Agent.is_active.is_(True))
            .options(selectinload(Agent.tools))
        )
        return result.scalar_one_or_none()

    async def _get_child_agent(self, parent: Agent, child_name: str) -> Optional[Agent]:
        """Get a child agent by name or config ID - optimized with single query."""
        from sqlalchemy import func

        # Normalize name for comparison (remove hyphens, underscores, spaces)
        def normalize(s: str) -> str:
            return s.lower().replace("-", "").replace("_", "").replace(" ", "")

        normalized_child = normalize(child_name)

        # First try: Direct config_id match (most common case) using PostgreSQL JSON operators
        result = await self.db.execute(
            select(Agent)
            .where(Agent.parent_agent_id == parent.id)
            .where(Agent.is_active.is_(True))
            .where(
                func.lower(func.replace(func.replace(func.replace(
                    func.json_extract_path_text(Agent.config_json, 'id'),
                    '-', ''), '_', ''), ' ', '')) == normalized_child
            )
            .options(
                selectinload(Agent.tools),
                selectinload(Agent.subflows),
                selectinload(Agent.response_templates),
            )
            .limit(1)
        )
        agent = result.scalar_one_or_none()
        if agent:
            return agent

        # Fallback: Name matching (only if config_id failed)
        result = await self.db.execute(
            select(Agent)
            .where(Agent.parent_agent_id == parent.id)
            .where(Agent.is_active.is_(True))
            .where(func.lower(Agent.name).contains(normalized_child))
            .options(
                selectinload(Agent.tools),
                selectinload(Agent.subflows),
                selectinload(Agent.response_templates),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_tool_by_name(self, agent: Agent, tool_name: str) -> Optional[Tool]:
        """Get a tool by name from an agent."""
        for tool in agent.tools:
            if tool.name == tool_name:
                return tool
        return None

    async def _get_subflow_by_name(self, agent: Agent, flow_name: str) -> Optional[Subflow]:
        """Get a subflow by name (legacy - kept for backward compatibility)."""
        for subflow in agent.subflows:
            if flow_name.lower() in subflow.name.lower():
                return subflow
        return None

    async def _ensure_routing_handler(self) -> RoutingHandler:
        """Lazy initialization of routing handler."""
        if self.routing_handler is None:
            registry = await get_routing_registry(self.db)
            self.routing_handler = RoutingHandler(
                db=self.db,
                routing_registry=registry,
                state_manager=self.state_manager,
                template_renderer=self.template_renderer,
            )
        return self.routing_handler

    async def _get_user_context(self, user_id: str) -> Optional[UserContext]:
        """Get user context if available."""
        result = await self.db.execute(
            select(UserContext).where(UserContext.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def _get_recent_messages(
        self, session_id: UUID, limit: int = 20
    ) -> List[ConversationMessage]:
        """Get recent messages for a session."""
        result = await self.db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.session_id == session_id)
            .order_by(ConversationMessage.created_at.desc())
            .limit(limit)
        )
        messages = result.scalars().all()
        return list(reversed(messages))  # Return in chronological order

    async def _record_messages(
        self,
        session: ConversationSession,
        user_message: str,
        assistant_message: str,
        tool_calls: List[dict],
        agent: Agent,
    ) -> None:
        """Record messages to the database."""
        # User message
        user_msg = ConversationMessage(
            session_id=session.session_id,
            user_id=session.user_id,
            role="user",
            content=user_message,
        )
        self.db.add(user_msg)

        # Assistant message
        assistant_msg = ConversationMessage(
            session_id=session.session_id,
            user_id=session.user_id,
            role="assistant",
            content=assistant_message,
            msg_metadata={
                "agentId": str(agent.id),
                "agentName": agent.name,
                "toolsCalled": tool_calls,
                "flowState": session.current_flow.get("currentState") if session.current_flow else None,
            },
        )
        self.db.add(assistant_msg)
