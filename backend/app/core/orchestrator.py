"""Main orchestrator for handling conversation flow."""

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
from app.core.history_compactor import HistoryCompactor
from app.core.i18n import get_message

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
    ):
        self.db = db
        self.llm_client = llm_client or get_llm_client()
        self.context_assembler = context_assembler or get_context_assembler()
        self.tool_executor = tool_executor or get_tool_executor()
        self.template_renderer = template_renderer or get_template_renderer()
        self.state_manager = StateManager(db)

    async def handle_message(
        self,
        user_message: str,
        user_id: str,
        session_id: Optional[UUID] = None,
    ) -> OrchestratorResponse:
        """
        Handle a user message and return the response.

        This is the main entry point for conversation handling.
        """
        start_time = time.time()

        # 1. Get or create session
        root_agent = await self._get_root_agent()
        if not root_agent:
            raise ValueError("No root agent configured")

        session = await self.state_manager.get_or_create_session(
            session_id, user_id, str(root_agent.id)
        )

        # 2. Check for pending confirmation
        if session.pending_confirmation:
            return await self._handle_confirmation_response(session, user_message)

        # 3. Get current agent
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

        # 4. Load agent's tools, subflows, and response templates
        await self.db.refresh(agent, ["tools", "subflows", "response_templates"])

        # 5. Get user context (optional) and set language for services
        user_context = await self._get_user_context(user_id)
        if user_context:
            language = user_context.get_language()
            self.tool_executor.set_language(language)

        # 6. Get recent messages
        recent_messages = await self._get_recent_messages(session.session_id)

        # 6.5. Check for history compaction
        compactor = HistoryCompactor(self.db)
        if await compactor.should_compact(str(session.session_id)):
            await compactor.compact_history(user_id, str(session.session_id))
            # Reload recent messages after compaction
            recent_messages = await self._get_recent_messages(session.session_id)

        # Get compacted history for context
        compacted_history = await compactor.get_compacted_history(user_id)

        # 7. Get current flow state if in a flow
        flow_state = await self.state_manager.get_current_flow_state(session)

        # 8. Assemble context
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

        # 9. Call LLM
        llm_response = await self.llm_client.complete(
            system_prompt=context.system_prompt,
            messages=context.messages,
            tools=context.tools if context.tools else None,
            model=context.model,
            temperature=context.temperature,
            max_tokens=context.max_tokens,
        )

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

        # 10. Process tool calls
        tool_call_records = []
        response_text = llm_response.text

        for tool_call in llm_response.tool_calls:
            result = await self._process_tool_call(session, agent, tool_call)
            tool_call_records.append({
                "name": tool_call.name,
                "params": tool_call.parameters,
                "result": result.data if result else None,
            })

            # Check for special actions
            if result and result.data:
                action = result.data.get("action") if isinstance(result.data, dict) else None

                if action == "enter_agent":
                    # Navigate to child agent
                    target_agent = result.data.get("agent")
                    child_agent = await self._get_child_agent(agent, target_agent)
                    if child_agent:
                        await self.state_manager.push_agent(
                            session, str(child_agent.id), f"User requested {target_agent}"
                        )
                        # Recursively handle with new agent
                        return await self.handle_message(user_message, user_id, session.session_id)

                elif action == "up_one_level":
                    await self.state_manager.pop_agent(session)
                    return await self.handle_message(user_message, user_id, session.session_id)

                elif action == "go_home":
                    await self.state_manager.go_home(session)
                    return await self.handle_message(user_message, user_id, session.session_id)

                elif action == "escalate_to_human":
                    await self.state_manager.escalate(session, tool_call.parameters.get("reason", "User request"))
                    response_text = "Entiendo. Te voy a conectar con un agente humano que podrá ayudarte mejor. Un momento por favor..."
                    break

                elif action == "start_flow":
                    flow_name = result.data.get("flow")
                    subflow = await self._get_subflow_by_name(agent, flow_name)
                    if subflow:
                        await self.state_manager.enter_subflow(session, subflow)
                        # Handle on_enter for initial state
                        initial_state = await self.state_manager.get_flow_state(
                            str(subflow.id), subflow.initial_state
                        )
                        if initial_state and initial_state.on_enter:
                            on_enter_msg = await self._handle_on_enter(initial_state, session, agent)
                            if on_enter_msg:
                                response_text = on_enter_msg
                                break
                        return await self.handle_message(user_message, user_id, session.session_id)

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

            # Handle flow transitions for successful tool calls
            if result and result.success and session.current_flow:
                tool = await self._get_tool_by_name(agent, tool_call.name)
                if tool and tool.flow_transition:
                    transition_result = await self._handle_flow_transition(
                        session, agent, tool, result
                    )
                    if transition_result:
                        response_text = transition_result
                        break

            # Try to apply response template for successful tool execution
            if result and result.success and not result.requires_confirmation:
                template_response = await self._apply_response_template(
                    agent, "tool_success", tool_call.name, result.data
                )
                if template_response:
                    response_text = template_response
                    break

                # Check if tool result has a _message field to use as response
                if isinstance(result.data, dict) and result.data.get("_message"):
                    response_text = result.data["_message"]
                    break

        # 11. Record messages
        await self._record_messages(session, user_message, response_text, tool_call_records, agent)

        # 12. Update session
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

        return OrchestratorResponse(
            session_id=session.session_id,
            message=response_text,
            agent_id=str(agent.id),
            agent_name=agent.name,
            tool_calls=tool_call_records,
            pending_confirmation=session.pending_confirmation,
            flow_state=session.current_flow.get("currentState") if session.current_flow else None,
            escalated=session.status == "escalated",
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
                    # Try to apply response template first
                    template_response = await self._apply_response_template(
                        agent, "tool_success", tool.name, result.data
                    )
                    if template_response:
                        response_text = template_response
                    else:
                        response_text = self._format_success_response(tool, result.data)

                    # Handle flow transition if applicable
                    if session.current_flow and tool.flow_transition:
                        transition_result = await self._handle_flow_transition(
                            session, agent, tool, result
                        )
                        if transition_result:
                            response_text = transition_result
                else:
                    # Try error template
                    template_response = await self._apply_response_template(
                        agent, "tool_error", tool.name, {"error": result.error}
                    )
                    if template_response:
                        response_text = template_response
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

        # Handle sendMessage action
        if on_enter.get("sendMessage"):
            template = on_enter["sendMessage"]
            # Render template with flow data
            flow_data = session.current_flow.get("stateData", {}) if session.current_flow else {}
            response_text = self.template_renderer.render(template, flow_data)

        # Handle fetchContext action (just log for now, context is re-assembled on next message)
        if on_enter.get("fetchContext"):
            logger.info(f"State {state.name} requests additional context: {on_enter['fetchContext']}")

        return response_text

    async def _apply_response_template(
        self,
        agent: Agent,
        trigger_type: str,
        tool_name: Optional[str],
        data: dict,
    ) -> Optional[str]:
        """Try to apply a matching response template."""
        if not agent.response_templates:
            return None

        template = self.template_renderer.find_matching_template(
            agent.response_templates,
            trigger_type=trigger_type,
            tool_name=tool_name,
        )

        if not template:
            return None

        # Only apply mandatory templates automatically
        if template.enforcement != "mandatory":
            return None

        return self.template_renderer.apply_template(template, data or {})

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

        # Check for navigation tools first
        if tool_name in ["up_one_level", "go_home", "escalate_to_human"]:
            return await self.tool_executor.execute_mock(
                tool_name, tool_call.parameters, session.user_id
            )

        # Check for agent entry tools
        if tool_name.startswith("enter_"):
            return await self.tool_executor.execute_mock(
                tool_name, tool_call.parameters, session.user_id
            )

        # Check for flow start tools
        if tool_name.startswith("start_flow_"):
            return await self.tool_executor.execute_mock(
                tool_name, tool_call.parameters, session.user_id
            )

        # Find the tool definition
        tool = await self._get_tool_by_name(agent, tool_name)

        if tool:
            return await self.tool_executor.execute(
                tool, tool_call.parameters, session
            )

        # If no tool found, try mock execution
        return await self.tool_executor.execute_mock(
            tool_name, tool_call.parameters, session.user_id
        )

    def _format_success_response(self, tool: Tool, data: dict) -> str:
        """Format a success response for a tool execution."""
        # Basic formatting - can be enhanced with response templates
        if tool.name == "create_transfer":
            return (
                f"✅ ¡Listo! Tu envío está en camino.\n\n"
                f"📍 Confirmación: {data.get('transferId', 'N/A')}\n"
                f"👤 Para: {data.get('recipient', {}).get('name', 'N/A')}\n"
                f"💰 Cantidad: ${data.get('amountMxn', 0):.2f} MXN\n"
                f"⏰ Llegada: {data.get('arrivalMessage', 'pronto')}\n\n"
                f"¿Necesitas algo más?"
            )
        elif tool.name == "make_payment":
            return (
                f"✅ ¡Pago realizado!\n\n"
                f"💰 Monto: ${data.get('amount', 0):.2f}\n"
                f"📊 Nuevo saldo: ${data.get('newBalance', 0):.2f}\n\n"
                f"¿Algo más en lo que pueda ayudarte?"
            )
        elif tool.name == "send_topup":
            return (
                f"✅ ¡Recarga enviada!\n\n"
                f"📱 Número: {data.get('phoneNumber', 'N/A')}\n"
                f"💰 Monto: ${data.get('localAmount', 0):.2f} {data.get('localCurrency', 'MXN')}\n\n"
                f"¿Necesitas algo más?"
            )
        elif tool.name == "pay_bill":
            return (
                f"✅ ¡Pago de servicio completado!\n\n"
                f"🏢 Servicio: {data.get('billerName', 'N/A')}\n"
                f"💰 Monto: ${data.get('amountPaid', 0):.2f} MXN\n"
                f"📝 Confirmación: {data.get('confirmationNumber', 'N/A')}\n\n"
                f"¿Algo más?"
            )
        else:
            return "✅ Operación completada exitosamente. ¿En qué más puedo ayudarte?"

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
        """Get a child agent by name."""
        result = await self.db.execute(
            select(Agent)
            .where(Agent.parent_agent_id == parent.id)
            .where(Agent.is_active.is_(True))
            .options(
                selectinload(Agent.tools),
                selectinload(Agent.subflows),
                selectinload(Agent.response_templates),
            )
        )
        agents = result.scalars().all()

        # Normalize name for comparison (remove hyphens, underscores, spaces)
        def normalize(s: str) -> str:
            return s.lower().replace("-", "").replace("_", "").replace(" ", "")

        normalized_child = normalize(child_name)
        for agent in agents:
            if normalized_child in normalize(agent.name):
                return agent
        return None

    async def _get_tool_by_name(self, agent: Agent, tool_name: str) -> Optional[Tool]:
        """Get a tool by name from an agent."""
        for tool in agent.tools:
            if tool.name == tool_name:
                return tool
        return None

    async def _get_subflow_by_name(self, agent: Agent, flow_name: str) -> Optional[Subflow]:
        """Get a subflow by name."""
        for subflow in agent.subflows:
            if flow_name.lower() in subflow.name.lower():
                return subflow
        return None

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
