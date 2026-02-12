"""Main orchestrator for handling conversation flow."""

import asyncio
import json
import logging
import re
import time
from typing import Optional, List, Any
from uuid import UUID
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import ConversationSession
from app.models.user import UserContext
from app.models.conversation import ConversationMessage
from app.core.llm_client import LLMClient, LLMResponse, ToolCall, get_llm_client
from app.core.context_assembler import ContextAssembler, AssembledContext, get_context_assembler
from app.core.config_types import PromptMode
from app.core.state_manager import StateManager
from app.core.tool_executor import ToolExecutor, ToolResult, get_tool_executor
from app.core.template_renderer import TemplateRenderer, get_template_renderer
from app.core.routing import RoutingType, RoutingOutcome
from app.core.routing_handler import RoutingHandler
from app.core.agent_registry import get_agent_registry
from app.core.config_types import (
    AgentConfig,
    ToolConfig,
    SubflowConfig,
    SubflowStateConfig,
    TransitionTrigger,
)  # PromptMode imported above
from app.core.history_compactor import HistoryCompactor
from app.core.event_trace import EventTracer, EventCategory, EventLevel
from app.core.context_enrichment import evaluate_condition

logger = logging.getLogger(__name__)
MAX_CHAIN_STEPS = 3


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
    routing_path: List[dict] = field(default_factory=list)
    chain_iterations: int = 0
    stable_state_reached: bool = False
    event_trace: List[dict] = field(default_factory=list)


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
    debug: Optional[DebugInfo] = None


@dataclass
class ChainState:
    """Tracks state during routing chain execution."""
    iteration: int = 0
    routing_occurred: bool = False
    stable_state_reached: bool = False
    confirmation_pending: bool = False
    error: Optional[str] = None
    routing_path: List[dict] = field(default_factory=list)
    last_llm_response: Optional[LLMResponse] = None
    last_tool_calls: List[dict] = field(default_factory=list)
    pending_context_requirements: List[dict] = field(default_factory=list)


class Orchestrator:
    """Main orchestrator for handling user messages."""

    def __init__(
        self,
        db: AsyncSession,
        llm_client: Optional[LLMClient] = None,
        context_assembler: Optional[ContextAssembler] = None,
        tool_executor: Optional[ToolExecutor] = None,
        template_renderer: Optional[TemplateRenderer] = None,
    ):
        self.db = db
        self.llm_client = llm_client or get_llm_client()
        self.context_assembler = context_assembler or get_context_assembler()
        self.tool_executor = tool_executor or get_tool_executor()
        self.template_renderer = template_renderer or get_template_renderer()
        self.state_manager = StateManager(db)
        self.routing_handler: Optional[RoutingHandler] = None

    async def handle_message(
        self,
        user_message: str,
        user_id: str,
        session_id: Optional[UUID] = None,
    ) -> OrchestratorResponse:
        """
        Handle a user message with routing chain flow.

        Uses an iterative routing chain that continues until reaching a "stable state"
        (no routing tools called). This eliminates the need for users to send extra
        messages after agent/flow routing.

        Flow:
        1. Setup: Load session, agent, user context
        2. Routing Chain: Loop until stable state
           - Call LLM
           - Process tools, detect routing
           - If routing occurred, continue chain with new agent
        3. Final Response: Record messages, return
        """
        start_time = time.time()

        # Initialize event tracer for this request
        tracer = EventTracer(user_message=user_message)
        self._current_tracer = tracer  # Store for lazy-initialized components

        # Pass tracer to routing handler if exists
        if self.routing_handler:
            self.routing_handler.tracer = tracer

        # === PHASE 1: SETUP ===
        root_agent = self._get_root_agent()
        if not root_agent:
            tracer.error("no_root_agent", "No root agent configured")
            raise ValueError("No root agent configured")

        session = await self.state_manager.get_or_create_session(
            session_id, user_id, root_agent.config_id
        )
        tracer.trace(
            EventCategory.SESSION, "session_loaded",
            f"Session {session.session_id} for user {user_id}",
            data={"session_id": str(session.session_id), "user_id": user_id, "new": session_id is None}
        )

        # Check for pending confirmation
        if session.pending_confirmation:
            return await self._handle_confirmation_response(session, user_message)

        # Get current agent
        agent = self.state_manager.get_current_agent(session)
        if not agent:
            agent = root_agent
            session.agent_stack = [
                {
                    "agentId": root_agent.config_id,
                    "enteredAt": "now",
                    "entryReason": "Session start",
                }
            ]

        tracer.trace(
            EventCategory.AGENT, "agent_active",
            f"Current agent: {agent.name}",
            data={"agent_id": agent.config_id, "agent_name": agent.name, "stack_depth": len(session.agent_stack or [])}
        )

        # Get user context and set language
        user_context = await self._get_user_context(user_id)
        language = user_context.get_language() if user_context else "es"
        self.tool_executor.set_language(language)

        # Get recent messages (once, at the start)
        recent_messages = await self._get_recent_messages(session.session_id)

        # Check for history compaction
        compactor = HistoryCompactor(self.db)
        if await compactor.should_compact(str(session.session_id)):
            await compactor.compact_history(user_id, str(session.session_id))
            recent_messages = await self._get_recent_messages(session.session_id)

        compacted_history = await compactor.get_compacted_history(user_id)

        # === PHASE 2: ROUTING CHAIN ===
        chain_state = ChainState()
        response_text = None
        debug_llm_call = None
        all_tool_calls = []
        routing_occurred_previously = False  # Track if routing occurred in any previous iteration

        while True:
            chain_state.iteration += 1

            if chain_state.iteration > MAX_CHAIN_STEPS:
                tracer.warning(
                    EventCategory.ROUTING,
                    "chain_step_limit_reached",
                    f"Reached max routing chain steps ({MAX_CHAIN_STEPS})",
                    data={"max_steps": MAX_CHAIN_STEPS},
                )
                response_text = (
                    "Estoy teniendo problemas para completar esta ruta automáticamente. "
                    "¿Puedes reformular tu solicitud?"
                )
                break

            # Determine prompt mode: use ROUTING mode for subsequent iterations
            # after routing has occurred (minimal context for routing decisions)
            prompt_mode = PromptMode.FULL
            if (
                chain_state.iteration > 1
                and routing_occurred_previously
                and not chain_state.pending_context_requirements
            ):
                prompt_mode = PromptMode.ROUTING

            chain_state.routing_occurred = False  # Reset for this iteration

            tracer.trace(
                EventCategory.ROUTING, "chain_iteration_start",
                f"Chain iteration {chain_state.iteration}",
                data={"iteration": chain_state.iteration, "prompt_mode": prompt_mode.value}
            )

            # Get current agent (may have changed from previous iteration)
            agent = self.state_manager.get_current_agent(session)

            # Get current flow state
            flow_state = self.state_manager.get_current_flow_state(session)

            # Evaluate deterministic user-turn transitions before calling the LLM.
            # This enables states with no tools to advance based on declarative conditions.
            pre_llm_transition = await self._evaluate_state_transitions(
                session=session,
                agent=agent,
                transition_trigger=TransitionTrigger.ON_USER_TURN.value,
                tracer=tracer,
                user_message=user_message,
            )
            if pre_llm_transition is not None:
                chain_state.routing_occurred = True
                routing_occurred_previously = True
                await self.db.commit()
                await self.db.refresh(session)

                # If on_enter produced text, return it immediately.
                if pre_llm_transition:
                    response_text = pre_llm_transition
                    chain_state.stable_state_reached = True
                    break

                # Otherwise continue chain with refreshed state context.
                continue

            # Refresh flow state in case transition evaluation updated flow data.
            flow_state = self.state_manager.get_current_flow_state(session)
            effective_context_requirements = (
                chain_state.pending_context_requirements or agent.context_requirements
            )
            chain_state.pending_context_requirements = []

            # Assemble context (ROUTING mode uses minimal context)
            context = self.context_assembler.assemble(
                session=session,
                user_message=user_message,
                agent=agent,
                user_context=user_context,
                recent_messages=recent_messages,
                compacted_history=compacted_history,
                current_flow_state=flow_state,
                context_requirements=effective_context_requirements,
                mode=prompt_mode,
            )

            logger.info(f"Chain iteration {chain_state.iteration}: calling LLM for agent {agent.config_id}")

            # Call LLM
            llm_start = time.time()
            llm_id = tracer.trace(
                EventCategory.LLM, "llm_request",
                f"Calling {context.model} with {len(context.tools) if context.tools else 0} tools",
                data={
                    "model": context.model,
                    "tool_count": len(context.tools) if context.tools else 0,
                    "message_count": len(context.messages),
                    "temperature": context.temperature,
                    "system_prompt": context.system_prompt,
                    "messages": context.messages,
                    "tools": context.tools if context.tools else []
                }
            )
            llm_response = await self.llm_client.complete(
                system_prompt=context.system_prompt,
                messages=context.messages,
                tools=context.tools if context.tools else None,
                model=context.model,
                temperature=context.temperature,
                max_tokens=context.max_tokens,
            )
            llm_duration = int((time.time() - llm_start) * 1000)
            chain_state.last_llm_response = llm_response

            tracer.trace(
                EventCategory.LLM, "llm_response",
                f"Response: {len(llm_response.tool_calls)} tool calls, {llm_response.output_tokens} tokens",
                duration_ms=llm_duration,
                parent_id=llm_id,
                data={
                    "text": llm_response.text,
                    "tool_calls": [
                        {"id": tc.id, "name": tc.name, "parameters": tc.parameters}
                        for tc in llm_response.tool_calls
                    ],
                    "input_tokens": llm_response.input_tokens,
                    "output_tokens": llm_response.output_tokens,
                    "stop_reason": llm_response.stop_reason
                }
            )

            # Capture debug info from last LLM call
            debug_llm_call = DebugLLMCall(
                system_prompt=context.system_prompt,
                messages=context.messages,
                tools_provided=[t["name"] for t in context.tools] if context.tools else [],
                model=context.model,
                temperature=context.temperature,
                raw_response=llm_response.text,
                token_counts=context.token_counts,
            )

            # Process tools, detect routing
            response_text = await self._process_chain_tools(
                session, agent, llm_response, chain_state, context, tracer
            )
            all_tool_calls.extend(chain_state.last_tool_calls)

            # Exit conditions
            if chain_state.error:
                tracer.trace(
                    EventCategory.ERROR, "chain_error",
                    f"Chain error: {chain_state.error}",
                    level=EventLevel.ERROR,
                    data={"iteration": chain_state.iteration, "error": chain_state.error}
                )
                logger.error(f"Chain error at iteration {chain_state.iteration}: {chain_state.error}")
                response_text = "Lo siento, encontré un problema. ¿En qué más puedo ayudarte?"
                break

            if chain_state.confirmation_pending:
                tracer.trace(
                    EventCategory.TOOL, "confirmation_pending",
                    "Waiting for user confirmation",
                    data={"iteration": chain_state.iteration}
                )
                logger.info(f"Chain paused for confirmation at iteration {chain_state.iteration}")
                break

            if not chain_state.routing_occurred:
                chain_state.stable_state_reached = True
                tracer.trace(
                    EventCategory.ROUTING, "stable_state_reached",
                    f"Chain stable after {chain_state.iteration} iterations",
                    data={"iteration": chain_state.iteration}
                )
                logger.info(f"Chain reached stable state at iteration {chain_state.iteration}")
                break

            # Track that routing occurred (for ROUTING mode in next iteration)
            routing_occurred_previously = True

            if self._detect_chain_loop(chain_state):
                tracer.trace(
                    EventCategory.ERROR, "chain_loop_detected",
                    "Routing chain loop detected",
                    level=EventLevel.ERROR,
                    data={"iteration": chain_state.iteration, "path": chain_state.routing_path}
                )
                logger.error(f"Chain loop detected at iteration {chain_state.iteration}")
                response_text = "Parece que estamos en un bucle. ¿Podrías reformular tu solicitud?"
                break

        # === PHASE 3: FINAL RESPONSE ===

        # Ensure we have a response
        if not response_text:
            response_text = chain_state.last_llm_response.text if chain_state.last_llm_response else ""

        # Set response on tracer for turn grouping
        tracer.set_response(response_text)

        # Build debug info
        processing_time_ms = int((time.time() - start_time) * 1000)

        # Add final trace event
        tracer.trace(
            EventCategory.SESSION, "response_ready",
            f"Response ready after {processing_time_ms}ms",
            duration_ms=processing_time_ms,
            data={"iterations": chain_state.iteration, "stable": chain_state.stable_state_reached}
        )

        # Record messages with complete event trace payload
        await self._record_messages(
            session,
            user_message,
            response_text,
            all_tool_calls,
            agent,
            event_trace=tracer.to_list(),
        )

        # Update session
        await self.state_manager.increment_message_count(session)

        # Store routing path in session metadata for debugging
        if chain_state.routing_path:
            if not session.session_metadata:
                session.session_metadata = {}
            session.session_metadata["routing_path"] = chain_state.routing_path[-10:]  # Keep last 10

        await self.db.commit()

        debug_info = DebugInfo(
            llm_call=debug_llm_call,
            agent_stack=session.agent_stack or [],
            flow_info=session.current_flow,
            context_sections=context.token_counts if debug_llm_call else None,
            processing_time_ms=processing_time_ms,
            routing_path=chain_state.routing_path,
            chain_iterations=chain_state.iteration,
            stable_state_reached=chain_state.stable_state_reached,
            event_trace=tracer.to_list(),
        )

        return OrchestratorResponse(
            session_id=session.session_id,
            message=response_text,
            agent_id=agent.config_id,
            agent_name=agent.name,
            tool_calls=all_tool_calls,
            pending_confirmation=session.pending_confirmation,
            flow_state=session.current_flow.get("currentState") if session.current_flow else None,
            escalated=session.status == "escalated",
            debug=debug_info,
        )

    async def _handle_confirmation_response(
        self, session: ConversationSession, user_message: str
    ) -> OrchestratorResponse:
        """Handle a response to a pending confirmation."""
        agent = self.state_manager.get_current_agent(session)

        # Check if confirmation expired
        if self.state_manager.is_confirmation_expired(session):
            await self.state_manager.clear_pending_confirmation(session)
            return await self.handle_message(user_message, session.user_id, session.session_id)

        # Classify user response
        is_confirmed = self.tool_executor.classify_user_confirmation(user_message)

        if is_confirmed is True:
            # Execute the confirmed tool
            pending = session.pending_confirmation
            tool = self._get_tool_by_name(agent, pending["toolName"])

            if tool:
                result = await self.tool_executor.execute(
                    tool, pending["toolParams"], session, skip_confirmation=True
                )

                # Clear confirmation
                await self.state_manager.clear_pending_confirmation(session)

                if result.success:
                    response_text = self._render_tool_success_message(
                        agent=agent,
                        tool=tool,
                        result=result,
                    )

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
                if result.success:
                    response_text = self._render_fallback_success_message(result.data)
                else:
                    response_text = f"Lo siento, hubo un error: {result.error}"

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
            agent_id=agent.config_id,
            agent_name=agent.name,
            tool_calls=[],
            pending_confirmation=session.pending_confirmation,
            escalated=session.status == "escalated",
        )

    async def _handle_flow_transition(
        self,
        session: ConversationSession,
        agent: AgentConfig,
        tool: ToolConfig,
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
        target_state = self.state_manager.get_flow_state(
            session.current_flow["agentId"],
            session.current_flow["flowId"],
            target_state_id
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

    async def _evaluate_state_transitions(
        self,
        session: ConversationSession,
        agent: AgentConfig,
        transition_trigger: str,
        tracer: EventTracer,
        tool_name: Optional[str] = None,
        tool_result: Optional[dict] = None,
        user_message: Optional[str] = None,
    ) -> Optional[str]:
        """
        Evaluate declarative transitions for the current state.

        Transition filtering rules:
        1. transition_trigger must match requested trigger (or be ALWAYS)
        2. tool_trigger (if present) must match tool_name for tool-result evaluation
        3. condition must evaluate to true if present
        4. For user-turn transitions without condition, trigger text must match
           the current user message intent.

        Returns a response message if a transition occurred, None otherwise.
        """
        if not session.current_flow:
            return None

        # Get current flow state
        current_state = self._get_current_flow_state(session)
        if not current_state or not current_state.transitions:
            return None

        state_data = session.current_flow.get("stateData", {}) or {}
        tool_result_data = tool_result or {}

        # Enrich evaluation context with deterministic values extracted from user turn.
        user_turn_data = {}
        if transition_trigger == TransitionTrigger.ON_USER_TURN.value and user_message:
            user_turn_data = self._extract_user_turn_data(
                user_message=user_message,
                state_data=state_data,
                transitions=current_state.transitions,
            )
            if user_turn_data:
                await self.state_manager.update_flow_data(session, user_turn_data)
                state_data = session.current_flow.get("stateData", {}) or {}

        # Build evaluation context: stateData + tool result + user metadata
        eval_context = {
            **state_data,
            "_tool_result": tool_result_data,
            "_user_message": user_message or "",
        }
        if tool_name:
            eval_context[f"_result_{tool_name}"] = tool_result_data

        transitions_in_scope = 0
        for transition in current_state.transitions:
            configured_trigger = transition.get(
                "transition_trigger",
                TransitionTrigger.ALWAYS.value,
            )
            if configured_trigger not in {
                TransitionTrigger.ON_USER_TURN.value,
                TransitionTrigger.ON_TOOL_RESULT.value,
                TransitionTrigger.ALWAYS.value,
            }:
                configured_trigger = TransitionTrigger.ALWAYS.value

            if configured_trigger in {
                transition_trigger,
                TransitionTrigger.ALWAYS.value,
            }:
                transitions_in_scope += 1

        # Evaluate each transition in order (first match wins)
        for transition in current_state.transitions:
            configured_trigger = transition.get(
                "transition_trigger",
                TransitionTrigger.ALWAYS.value,
            )
            if configured_trigger not in {
                TransitionTrigger.ON_USER_TURN.value,
                TransitionTrigger.ON_TOOL_RESULT.value,
                TransitionTrigger.ALWAYS.value,
            }:
                configured_trigger = TransitionTrigger.ALWAYS.value

            if configured_trigger not in {
                transition_trigger,
                TransitionTrigger.ALWAYS.value,
            }:
                continue

            # Check tool_trigger match (if specified)
            transition_tool_trigger = transition.get("tool_trigger")
            if transition_trigger == TransitionTrigger.ON_TOOL_RESULT.value:
                if transition_tool_trigger and transition_tool_trigger != tool_name:
                    continue
            elif transition_tool_trigger:
                # User-turn evaluations should not trigger tool-specific transitions.
                continue

            # Evaluate condition (if specified)
            condition = transition.get("condition")
            condition_result = True
            if condition:
                condition_result = evaluate_condition(condition, eval_context)
                if not condition_result:
                    continue
            elif transition_trigger == TransitionTrigger.ON_USER_TURN.value:
                trigger_name = transition.get("trigger", "")
                if not self._match_user_turn_trigger(
                    trigger_name=trigger_name,
                    user_message=user_message or "",
                    state_data=state_data,
                    transitions_in_scope=transitions_in_scope,
                ):
                    continue

            # Transition matches!
            target_state_id = transition.get("target")
            if not target_state_id:
                logger.warning(f"Transition missing 'target' field: {transition}")
                continue

            trigger_name = transition.get("trigger", "unnamed")
            logger.info(
                f"Declarative transition triggered: {trigger_name} -> {target_state_id} "
                f"(trigger_type: {transition_trigger}, tool: {tool_name}, condition: {condition})"
            )

            # Trace the transition
            tracer.trace(
                EventCategory.FLOW,
                "declarative_transition_triggered",
                f"Transition '{trigger_name}' -> {target_state_id}",
                data={
                    "trigger": trigger_name,
                    "transition_trigger": configured_trigger,
                    "tool_name": tool_name,
                    "condition": condition,
                    "condition_result": condition_result,
                    "target_state": target_state_id,
                    "from_state": session.current_flow.get("currentState"),
                    "to_state": target_state_id,
                }
            )

            # Get the target state definition
            target_state = self.state_manager.get_flow_state(
                session.current_flow["agentId"],
                session.current_flow["flowId"],
                target_state_id
            )

            if not target_state:
                logger.warning(f"Target state {target_state_id} not found in flow")
                return None

            # Store the tool result in flow data before transitioning
            if tool_result_data:
                await self.state_manager.update_flow_data(session, tool_result_data)

            # Perform the transition
            await self.state_manager.transition_state(session, target_state_id, target_state)

            # Handle on_enter actions for the new state
            response_text = None
            if target_state.on_enter:
                response_text = await self._handle_on_enter(target_state, session, agent)

            return response_text if response_text else ""

        # No transition matched
        return None

    def _get_current_flow_state(self, session: ConversationSession) -> Optional[SubflowStateConfig]:
        """Get the current flow state configuration."""
        if not session.current_flow:
            return None

        agent_id = session.current_flow.get("agentId")
        flow_id = session.current_flow.get("flowId")
        state_id = session.current_flow.get("currentState")

        if not agent_id or not flow_id or not state_id:
            return None

        return self.state_manager.get_flow_state(agent_id, flow_id, state_id)

    def _extract_user_turn_data(
        self,
        user_message: str,
        state_data: dict,
        transitions: List[dict],
    ) -> dict:
        """Extract deterministic values from user input for condition evaluation."""
        extracted: dict[str, Any] = {}
        lower_message = user_message.lower()

        required_vars = self._collect_transition_variables(transitions)

        # Reuse confirmation classifier for common yes/no transitions.
        confirm_classification = self.tool_executor.classify_user_confirmation(user_message)
        if confirm_classification is True:
            for key in ("confirmed", "user_confirms", "approved", "accept", "accepted"):
                if key in required_vars and key not in state_data:
                    extracted[key] = True
            if "user_cancels" in required_vars and "user_cancels" not in state_data:
                extracted["user_cancels"] = False
        elif confirm_classification is False:
            for key in ("user_cancels", "cancelled", "declined", "rejected"):
                if key in required_vars and key not in state_data:
                    extracted[key] = True
            if "user_confirms" in required_vars and "user_confirms" not in state_data:
                extracted["user_confirms"] = False

        if "retry" in required_vars and "retry" not in state_data:
            retry_tokens = ("retry", "try again", "intenta", "intentar", "otra vez")
            extracted["retry"] = any(token in lower_message for token in retry_tokens)

        numeric_value = self._extract_first_number(user_message)
        if numeric_value is not None:
            if "amount" in required_vars and "amount" not in state_data:
                extracted["amount"] = numeric_value
            if "amount_usd" in required_vars and "amount_usd" not in state_data:
                extracted["amount_usd"] = numeric_value
            if "requested_amount" in required_vars and "requested_amount" not in state_data:
                extracted["requested_amount"] = numeric_value

            if "term_weeks" in required_vars and "term_weeks" not in state_data:
                int_value = int(numeric_value)
                if int_value in {4, 8, 12, 16, 20, 26}:
                    extracted["term_weeks"] = int_value

        return extracted

    @staticmethod
    def _collect_transition_variables(transitions: List[dict]) -> set[str]:
        """Collect variable names used in conditions."""
        variables: set[str] = set()
        token_pattern = re.compile(r"[A-Za-z_][A-Za-z0-9_\.]*")
        ignored = {
            "and",
            "or",
            "not",
            "in",
            "is",
            "none",
            "null",
            "true",
            "false",
            "stateData",
            "context",
        }

        for transition in transitions:
            condition = transition.get("condition")
            if not condition:
                continue
            for token in token_pattern.findall(condition):
                root = token.split(".")[0]
                if root.lower() in ignored:
                    continue
                if root.startswith("_"):
                    continue
                variables.add(root)
        return variables

    @staticmethod
    def _extract_first_number(user_message: str) -> Optional[float]:
        """Extract first numeric token from user text."""
        normalized = user_message.replace(",", "")
        match = re.search(r"\d+(?:\.\d+)?", normalized)
        if not match:
            return None
        try:
            return float(match.group(0))
        except ValueError:
            return None

    @staticmethod
    def _match_user_turn_trigger(
        trigger_name: str,
        user_message: str,
        state_data: dict,
        transitions_in_scope: int,
    ) -> bool:
        """
        Heuristic matcher for trigger labels when no explicit condition is provided.

        If only one candidate transition exists, allow it.
        If multiple candidates exist, only match clear intent labels.
        """
        if transitions_in_scope <= 1:
            return True

        normalized_trigger = (trigger_name or "").lower()
        message = (user_message or "").lower()

        if any(token in normalized_trigger for token in ("confirm", "approved", "accept")):
            return any(token in message for token in ("si", "sí", "yes", "confirm", "dale", "ok"))

        if any(token in normalized_trigger for token in ("cancel", "decline", "reject")):
            return any(token in message for token in ("no", "cancel", "decline", "rechaz"))

        if "retry" in normalized_trigger:
            return any(token in message for token in ("retry", "try again", "otra vez", "intenta"))

        if any(token in normalized_trigger for token in ("modify", "edit", "change", "update")):
            return any(token in message for token in ("change", "edit", "modify", "modificar", "cambiar"))

        if "amount" in normalized_trigger:
            return bool(re.search(r"\d", message))

        if "term" in normalized_trigger:
            return any(f" {weeks}" in f" {message}" for weeks in ("4", "8", "12", "16", "20", "26"))

        # For ambiguous multi-transition states, avoid implicit transition.
        return False

    def _render_tool_success_message(
        self,
        agent: AgentConfig,
        tool: ToolConfig,
        result: ToolResult,
    ) -> str:
        """Render deterministic success message using templates or normalized fields."""
        if isinstance(result.data, dict):
            template = self.template_renderer.find_matching_template(
                templates=agent.response_templates,
                trigger_type="tool_success",
                tool_name=tool.name,
            )
            if template:
                rendered = self.template_renderer.apply_template(template, result.data)
                if rendered:
                    return rendered

            return self._render_fallback_success_message(result.data)

        return "Operación completada exitosamente. ¿En qué más puedo ayudarte?"

    @staticmethod
    def _render_fallback_success_message(payload: Any) -> str:
        """Build deterministic fallback success text from transaction payload fields."""
        if not isinstance(payload, dict):
            return "Operación completada exitosamente. ¿En qué más puedo ayudarte?"

        reference = payload.get("reference") or payload.get("transaction_id")
        amount = payload.get("amount")
        currency = payload.get("currency")

        parts = ["Operación completada exitosamente."]
        if amount is not None and currency:
            parts.append(f"Monto: {amount} {currency}.")
        elif amount is not None:
            parts.append(f"Monto: {amount}.")

        if reference:
            parts.append(f"Referencia: {reference}.")

        parts.append("¿En qué más puedo ayudarte?")
        return " ".join(parts)

    async def _handle_on_enter(
        self,
        state: SubflowStateConfig,
        session: ConversationSession,
        agent: AgentConfig,
    ) -> Optional[str]:
        """Handle on_enter actions when entering a state."""
        if not state.on_enter:
            return None

        on_enter = state.on_enter
        response_text = None

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
            response_text = rendered_message

        return response_text

    def _detect_chain_loop(self, chain_state: ChainState) -> bool:
        """
        Detect if routing chain is looping.

        Returns True if the same (from_agent, tool) pair is visited twice.
        """
        if len(chain_state.routing_path) < 2:
            return False

        visited = set()
        for entry in chain_state.routing_path:
            key = (entry.get("from_agent"), entry.get("tool"))
            if key in visited:
                logger.warning(
                    f"Chain loop detected: {key} visited twice. "
                    f"Path: {chain_state.routing_path}"
                )
                return True
            visited.add(key)
        return False

    async def _process_chain_tools(
        self,
        session: ConversationSession,
        agent: AgentConfig,
        llm_response: LLMResponse,
        chain_state: ChainState,
        context: AssembledContext,
        tracer: EventTracer,
    ) -> Optional[str]:
        """
        Process tool calls within a routing chain iteration.

        Updates chain_state based on tool results:
        - Sets routing_occurred=True if state changed
        - Sets confirmation_pending=True if confirmation needed
        - Sets error if routing failed

        For service tools (non-routing), executes them and feeds results back to
        the LLM via complete_with_tool_results so it can generate a natural response.

        Returns response text if chain should end with a message.
        """
        response_text = llm_response.text
        chain_state.last_tool_calls = []

        # Track service tool calls for feedback loop
        service_tool_calls: list[ToolCall] = []
        service_tool_results: list[dict] = []

        for tool_call in llm_response.tool_calls:
            tool_start = time.time()
            tool_id = tracer.trace(
                EventCategory.TOOL, "tool_started",
                f"Executing: {tool_call.name}",
                data={"tool_name": tool_call.name, "params": tool_call.parameters}
            )

            result = await self._process_tool_call(session, agent, tool_call)
            tool_duration = int((time.time() - tool_start) * 1000)

            chain_state.last_tool_calls.append({
                "name": tool_call.name,
                "params": tool_call.parameters,
                "result": result.data if result else None,
            })

            # Check for routing outcome
            if result and result.data and isinstance(result.data, dict):
                routing_outcome_data = result.data.get("_routing_outcome")
                if routing_outcome_data:
                    routing_outcome = RoutingOutcome.from_dict(routing_outcome_data)

                    # Trace routing classification
                    tracer.trace(
                        EventCategory.ROUTING, "tool_classified",
                        f"Tool {tool_call.name} is ROUTING type",
                        parent_id=tool_id,
                        data={
                            "routing_type": routing_outcome.routing_type if hasattr(routing_outcome, 'routing_type') else "routing",
                            "state_changed": routing_outcome.state_changed,
                            "target": routing_outcome.target_id if hasattr(routing_outcome, 'target_id') else None
                        }
                    )

                    # Track routing path for loop detection
                    from datetime import datetime
                    chain_state.routing_path.append({
                        "iteration": chain_state.iteration,
                        "from_agent": agent.config_id,
                        "tool": tool_call.name,
                        "state_changed": routing_outcome.state_changed,
                        "timestamp": datetime.utcnow().isoformat()
                    })

                    if routing_outcome.error:
                        tracer.trace(
                            EventCategory.ROUTING, "routing_error",
                            f"Routing failed: {routing_outcome.error}",
                            level=EventLevel.ERROR,
                            parent_id=tool_id,
                            data={"error": routing_outcome.error}
                        )
                        chain_state.error = routing_outcome.error
                        return None

                    if routing_outcome.state_changed:
                        tracer.trace(
                            EventCategory.ROUTING, "routing_executed",
                            f"State changed by {tool_call.name}",
                            duration_ms=tool_duration,
                            parent_id=tool_id,
                            data={"state_changed": True}
                        )
                        chain_state.routing_occurred = True
                        chain_state.pending_context_requirements = routing_outcome.context_requirements or []
                        await self.db.commit()

                        # Refresh session and get new agent
                        await self.db.refresh(session)

                        # Break tool loop to continue chain with new agent context
                        return None

                    if routing_outcome.response_text:
                        return routing_outcome.response_text

                    # Routing tool handled but no state change - continue processing
                    continue

            # Check for confirmation requirement
            if result and result.requires_confirmation:
                await self.state_manager.set_pending_confirmation(
                    session,
                    tool_call.name,
                    tool_call.parameters,
                    result.confirmation_message,
                )
                chain_state.confirmation_pending = True
                return result.confirmation_message

            # Handle flow transitions (explicit tool-level flow_transition)
            if result and session.current_flow:
                tool = self._get_tool_by_name(agent, tool_call.name)
                if tool and tool.flow_transition:
                    transition_result = await self._handle_flow_transition(
                        session, agent, tool, result
                    )
                    if transition_result:
                        return transition_result

            # Handle declarative state transitions (state-level transitions list)
            if result and session.current_flow:
                tool_result_data = result.data if isinstance(result.data, dict) else {}
                tool_result_data = dict(tool_result_data)
                tool_result_data.setdefault("success", result.success)
                tool_result_data.setdefault("tool_success", result.success)
                if "topup" in tool_call.name:
                    tool_result_data.setdefault("topup_success", result.success)

                transition_result = await self._evaluate_state_transitions(
                    session=session,
                    agent=agent,
                    transition_trigger=TransitionTrigger.ON_TOOL_RESULT.value,
                    tracer=tracer,
                    tool_name=tool_call.name,
                    tool_result=tool_result_data,
                )
                if transition_result is not None:  # Empty string means transition occurred
                    # Signal that state changed so chain continues with new context
                    chain_state.routing_occurred = True
                    await self.db.commit()
                    await self.db.refresh(session)
                    return transition_result if transition_result else None

            # This is a service tool - track it for feedback loop
            tracer.trace(
                EventCategory.TOOL, "tool_classified",
                f"Tool {tool_call.name} is SERVICE type",
                parent_id=tool_id,
                data={"routing_type": "SERVICE"}
            )

            # Log tool completion with full result data
            tracer.trace(
                EventCategory.TOOL, "tool_complete",
                f"{tool_call.name}: {'success' if result and result.success else 'failed'}",
                level=EventLevel.INFO if result and result.success else EventLevel.ERROR,
                duration_ms=tool_duration,
                parent_id=tool_id,
                data={
                    "success": result.success if result else False,
                    "result_data": result.data if result else None,
                    "error": result.error if result and not result.success else None
                }
            )

            service_tool_calls.append(tool_call)
            service_tool_results.append({
                "tool_call_id": tool_call.id,
                "content": result.data if result and result.success else {
                    "error": result.error if result else "Unknown error"
                }
            })

        # If we have service tool results and no routing occurred, feed results back to LLM
        if service_tool_calls and service_tool_results and not chain_state.routing_occurred:
            logger.info(f"Feeding {len(service_tool_results)} tool results back to LLM")

            # Build messages including the assistant message with tool calls
            messages_with_tool_calls = context.messages.copy()
            messages_with_tool_calls.append({
                "role": "assistant",
                "content": llm_response.text or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.parameters)
                        }
                    }
                    for tc in service_tool_calls
                ]
            })

            tracer.trace(
                EventCategory.LLM, "tool_feedback_started",
                f"Feeding {len(service_tool_results)} results back to LLM",
                data={
                    "tool_count": len(service_tool_results),
                    "tool_results": service_tool_results,
                    "messages_with_tool_calls": messages_with_tool_calls,
                    "system_prompt": context.system_prompt
                }
            )

            try:
                feedback_start = time.time()
                # Don't pass tools - force LLM to respond with text, not more tool calls
                continuation_response = await self.llm_client.complete_with_tool_results(
                    system_prompt=context.system_prompt,
                    messages=messages_with_tool_calls,
                    tools=[],  # Empty to force text response
                    tool_results=service_tool_results,
                )
                feedback_duration = int((time.time() - feedback_start) * 1000)
                tracer.trace(
                    EventCategory.LLM, "tool_feedback_complete",
                    f"Continuation response received",
                    duration_ms=feedback_duration,
                    data={
                        "text": continuation_response.text,
                        "output_tokens": continuation_response.output_tokens,
                        "input_tokens": continuation_response.input_tokens
                    }
                )
                chain_state.last_llm_response = continuation_response
                return continuation_response.text
            except Exception as e:
                tracer.trace(
                    EventCategory.ERROR, "tool_feedback_failed",
                    f"Feedback failed: {str(e)}",
                    level=EventLevel.ERROR,
                    data={"error": str(e)}
                )
                logger.error(f"Tool result feedback failed: {e}")
                # Fall back to original response
                return response_text

        return response_text

    async def _process_tool_call(
        self, session: ConversationSession, agent: AgentConfig, tool_call: ToolCall
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
            message = "Language changed to English" if language == "en" else "Idioma cambiado a Español"
            return ToolResult(success=True, data={"_message": message, "language": language})

        # Try routing first (handles navigation, agent entry, flow start)
        routing_handler = self._ensure_routing_handler()
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
        tool = self._get_tool_by_name(agent, tool_name)

        if tool:
            return await self.tool_executor.execute(
                tool, tool_call.parameters, session
            )

        # If no tool found, try mock execution (for service tools without DB definition)
        return await self.tool_executor.execute_mock(
            tool_name, tool_call.parameters, session.user_id
        )


    def _get_root_agent(self) -> Optional[AgentConfig]:
        """Get the root orchestrator agent (sync - no DB)."""
        return get_agent_registry().get_root_agent()

    def _get_child_agent(self, parent: AgentConfig, child_name: str) -> Optional[AgentConfig]:
        """Get a child agent by name or config ID (sync - no DB)."""
        # Normalize name for comparison
        def normalize(s: str) -> str:
            return s.lower().replace("-", "").replace("_", "").replace(" ", "")

        normalized_child = normalize(child_name)

        children = get_agent_registry().get_children(parent.config_id)
        for child in children:
            if normalize(child.config_id) == normalized_child:
                return child
            if normalized_child in normalize(child.name):
                return child
        return None

    def _get_tool_by_name(self, agent: AgentConfig, tool_name: str) -> Optional[ToolConfig]:
        """Get a tool by name from an agent (sync - no DB)."""
        return agent.get_tool(tool_name)

    def _get_subflow_by_name(self, agent: AgentConfig, flow_name: str) -> Optional[SubflowConfig]:
        """Get a subflow by name (sync - no DB)."""
        for subflow in agent.subflows:
            if flow_name.lower() in subflow.name.lower():
                return subflow
        return None

    def _ensure_routing_handler(self) -> RoutingHandler:
        """Lazy initialization of routing handler (sync - no DB)."""
        tracer = getattr(self, '_current_tracer', None)
        if self.routing_handler is None:
            self.routing_handler = RoutingHandler(
                db=self.db,
                state_manager=self.state_manager,
                template_renderer=self.template_renderer,
                tracer=tracer,
            )
        elif tracer:
            # Update tracer for existing handler (in case it changed)
            self.routing_handler.tracer = tracer
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
        agent: AgentConfig,
        event_trace: Optional[List[dict]] = None,
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
                "agentId": agent.config_id,
                "agentName": agent.name,
                "toolsCalled": tool_calls,
                "flowState": session.current_flow.get("currentState") if session.current_flow else None,
                "eventTrace": event_trace or [],
            },
        )
        self.db.add(assistant_msg)
