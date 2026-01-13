"""Context assembler for building LLM prompts with token budgets."""

import logging
from typing import Optional, List
from dataclasses import dataclass

import tiktoken

from app.config import get_settings
from app.models.agent import Agent, Tool
from app.models.session import ConversationSession
from app.models.user import UserContext
from app.models.conversation import ConversationMessage
from app.models.subflow import Subflow, SubflowState
from app.core.config_loader import load_prompts
from app.core.i18n import (
    get_language_directive,
    DEFAULT_LANGUAGE,
)

logger = logging.getLogger(__name__)
settings = get_settings()

# Use cl100k_base encoding (GPT-4 tokenizer)
_encoding = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Count tokens in a text string."""
    return len(_encoding.encode(text))


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate text to fit within token limit."""
    tokens = _encoding.encode(text)
    if len(tokens) <= max_tokens:
        return text
    truncated_tokens = tokens[:max_tokens]
    return _encoding.decode(truncated_tokens)


@dataclass
class AssembledContext:
    """Result of context assembly."""

    system_prompt: str
    messages: List[dict]  # OpenAI message format
    tools: List[dict]  # OpenAI tool format
    model: str
    temperature: float
    max_tokens: int
    token_counts: dict[str, int]  # Token count per section for debugging


class ContextAssembler:
    """Assembles context for LLM calls with token budget management."""

    def __init__(self):
        self.budgets = {
            "system_prompt": settings.token_budget_system_prompt,
            "user_profile": settings.token_budget_user_profile,
            "product_context": settings.token_budget_product_context,
            "conversation_recent": settings.token_budget_conversation_recent,
            "conversation_compacted": settings.token_budget_conversation_compacted,
            "current_state": settings.token_budget_current_state,
            "tool_definitions": settings.token_budget_tool_definitions,
            "buffer": settings.token_budget_buffer,
        }

    def assemble(
        self,
        session: ConversationSession,
        user_message: str,
        agent: Agent,
        user_context: Optional[UserContext] = None,
        recent_messages: Optional[List[ConversationMessage]] = None,
        compacted_history: Optional[str] = None,
        current_flow_state: Optional[SubflowState] = None,
    ) -> AssembledContext:
        """
        Assemble the full context for an LLM call.

        Args:
            session: Current conversation session
            user_message: The user's current message
            agent: The current agent handling the conversation
            user_context: Optional user context data
            recent_messages: Recent messages for context
            compacted_history: Summarized older history
            current_flow_state: Current state if in a subflow

        Returns:
            AssembledContext with system prompt, messages, tools, and config
        """
        token_counts = {}

        # Determine user's language preference
        language = DEFAULT_LANGUAGE
        if user_context:
            language = user_context.get_language()

        # 1. Build system prompt sections
        sections = []

        # Base system prompt (from JSON config) - always in English
        prompts = load_prompts()
        base_prompt = prompts.get("base_system_prompt", "")
        sections.append(base_prompt)
        token_counts["base_prompt"] = count_tokens(base_prompt)

        # Agent description - always in English
        agent_section = self._build_agent_section(agent)
        agent_section = truncate_to_tokens(
            agent_section, self.budgets["system_prompt"] - token_counts["base_prompt"]
        )
        sections.append(agent_section)
        token_counts["agent_description"] = count_tokens(agent_section)

        # User profile - always in English
        if user_context:
            user_section = self._build_user_section(user_context)
            user_section = truncate_to_tokens(user_section, self.budgets["user_profile"])
            sections.append(user_section)
            token_counts["user_profile"] = count_tokens(user_section)

        # Product context (if in a product agent) - always in English
        if user_context and agent.parent_agent_id:
            product_section = self._build_product_context(user_context, agent)
            if product_section:
                product_section = truncate_to_tokens(
                    product_section, self.budgets["product_context"]
                )
                sections.append(product_section)
                token_counts["product_context"] = count_tokens(product_section)

        # Compacted history - always in English
        if compacted_history:
            history_template = prompts.get("sections", {}).get(
                "previous_history", "\n## Previous Conversation History\n{history}"
            )
            history_section = history_template.format(history=compacted_history)
            history_section = truncate_to_tokens(
                history_section, self.budgets["conversation_compacted"]
            )
            sections.append(history_section)
            token_counts["compacted_history"] = count_tokens(history_section)

        # Current flow state - always in English
        if session.current_flow and current_flow_state:
            state_section = self._build_flow_state_section(session, current_flow_state)
            state_section = truncate_to_tokens(state_section, self.budgets["current_state"])
            sections.append(state_section)
            token_counts["flow_state"] = count_tokens(state_section)

        # Agent-enriched data (if not in a flow) - always in English
        if not session.current_flow and session.session_metadata:
            agent_data = session.session_metadata.get("agent_enriched_data")
            if agent_data:
                agent_data_section = self._format_agent_enriched_data(agent_data)
                sections.append(agent_data_section)
                token_counts["agent_enriched_data"] = count_tokens(agent_data_section)

        # Pending confirmation - always in English
        if session.pending_confirmation:
            confirm_section = self._build_confirmation_section(session)
            sections.append(confirm_section)
            token_counts["pending_confirmation"] = count_tokens(confirm_section)

        # Build navigation instructions - always in English
        nav_section = self._build_navigation_section(agent)
        sections.append(nav_section)
        token_counts["navigation"] = count_tokens(nav_section)

        # Add language directive at the very end (ULTRA IMPORTANT)
        language_directive = get_language_directive(language)
        sections.append(language_directive)
        token_counts["language_directive"] = count_tokens(language_directive)

        # Combine system prompt
        system_prompt = "\n".join(sections)
        token_counts["total_system"] = count_tokens(system_prompt)

        # 2. Build messages array
        messages = []

        # Add recent conversation messages
        if recent_messages:
            for msg in recent_messages:
                messages.append({
                    "role": msg.role if msg.role != "system" else "user",
                    "content": msg.content,
                })

        # Add current user message
        messages.append({
            "role": "user",
            "content": user_message,
        })
        token_counts["messages"] = sum(count_tokens(m["content"]) for m in messages)

        # 3. Build tools array - always in English
        tools = self._build_tools(agent, current_flow_state)
        token_counts["tools"] = count_tokens(str(tools))

        # 4. Get model config
        model_config = agent.model_config_json or {}
        model = model_config.get("model", settings.default_model)
        temperature = model_config.get("temperature", settings.default_temperature)
        max_tokens = model_config.get("maxTokens", settings.default_max_tokens)

        return AssembledContext(
            system_prompt=system_prompt,
            messages=messages,
            tools=tools,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            token_counts=token_counts,
        )

    def _build_agent_section(self, agent: Agent) -> str:
        """Build the agent role section."""
        prompts = load_prompts()
        role_template = prompts.get("sections", {}).get(
            "your_current_role", "\n## Your Current Role\n{description}"
        )

        # Get agent description - now a plain string
        description = agent.description
        if agent.config_json and "description" in agent.config_json:
            desc = agent.config_json["description"]
            # Handle both plain string and legacy dict format during transition
            if isinstance(desc, str):
                description = desc
            elif isinstance(desc, dict):
                description = desc.get("en", description)

        section = role_template.format(description=description)

        # Add system prompt addition
        if agent.system_prompt_addition:
            addition = agent.system_prompt_addition
            if agent.config_json and "system_prompt_addition" in agent.config_json:
                spa = agent.config_json["system_prompt_addition"]
                # Handle both plain string and legacy dict format during transition
                if isinstance(spa, str):
                    addition = spa
                elif isinstance(spa, dict):
                    addition = spa.get("en", addition)
            section += f"\n\n{addition}"

        return section

    def _build_user_section(self, user_context: UserContext) -> str:
        """Build the user profile section."""
        prompts = load_prompts()
        sections_config = prompts.get("sections", {})

        name = user_context.get_preferred_name()

        user_template = sections_config.get(
            "user_section", "\n## User\nName: {name}"
        )
        sections = [user_template.format(name=name)]

        if user_context.behavioral_summary:
            context_template = sections_config.get(
                "user_context", "\n## User Context\n{behavioral_summary}"
            )
            sections.append(context_template.format(behavioral_summary=user_context.behavioral_summary))

        return "\n".join(sections)

    def _build_product_context(
        self, user_context: UserContext, agent: Agent
    ) -> Optional[str]:
        """Build product-specific context based on the agent."""
        if not user_context.product_summaries:
            return None

        # Map agent names to product summary keys
        agent_to_product = {
            "remittances": "remittances",
            "credit": "credit",
            "wallet": "wallet",
            "topups": "topups",
            "billpay": "billPay",
        }

        prompts = load_prompts()
        product_template = prompts.get("sections", {}).get(
            "product_context", "\n## {agent_name} Context\n{summary}"
        )

        agent_name_lower = agent.name.lower()
        for key, product_key in agent_to_product.items():
            if key in agent_name_lower:
                summary = user_context.product_summaries.get(product_key)
                if summary:
                    formatted_summary = self._format_product_summary(product_key, summary)
                    return product_template.format(
                        agent_name=agent.name,
                        summary=formatted_summary
                    )

        return None

    def _format_product_summary(self, product: str, summary: dict) -> str:
        """Format a product summary for the prompt."""
        prompts = load_prompts()
        labels = prompts.get("sections", {}).get("product_labels", {})
        lines = []

        if product == "remittances":
            remit_labels = labels.get("remittances", {})
            if "lifetimeCount" in summary:
                label = remit_labels.get("lifetime_count", "Total transfers")
                lines.append(f"- {label}: {summary['lifetimeCount']}")
            if "lastTransactionAt" in summary:
                label = remit_labels.get("last_transaction", "Last transfer")
                lines.append(f"- {label}: {summary['lastTransactionAt']}")
            if "frequentRecipients" in summary:
                recipients = summary["frequentRecipients"]
                if recipients:
                    names = [r.get("name", "Unknown") for r in recipients[:3]]
                    label = remit_labels.get("frequent_recipients", "Frequent recipients")
                    lines.append(f"- {label}: {', '.join(names)}")

        elif product == "credit":
            credit_labels = labels.get("credit", {})
            if "hasActiveCredit" in summary:
                label = credit_labels.get("active_credit", "Active credit")
                yes_no = credit_labels.get("yes" if summary["hasActiveCredit"] else "no", "Yes" if summary["hasActiveCredit"] else "No")
                lines.append(f"- {label}: {yes_no}")
            if "currentBalance" in summary:
                label = credit_labels.get("current_balance", "Current balance")
                lines.append(f"- {label}: ${summary['currentBalance']:.2f}")
            if "creditLimit" in summary:
                label = credit_labels.get("limit", "Limit")
                lines.append(f"- {label}: ${summary['creditLimit']:.2f}")

        elif product == "wallet":
            wallet_labels = labels.get("wallet", {})
            if "currentBalance" in summary:
                label = wallet_labels.get("balance", "Balance")
                lines.append(f"- {label}: ${summary['currentBalance']:.2f}")

        return "\n".join(lines) if lines else str(summary)

    def _build_flow_state_section(
        self, session: ConversationSession, state: SubflowState
    ) -> str:
        """Build the current flow state section."""
        flow = session.current_flow or {}
        prompts = load_prompts()

        flow_template = prompts.get("sections", {}).get(
            "flow_state",
            "\n## Current Flow State\nFlow: {flow_id}\nState: {state_id}\n\n### Instructions for this state:\n{instructions}"
        )

        # Get instructions - now a plain string
        instructions = state.agent_instructions
        if hasattr(state, 'config_json') and state.config_json:
            agent_instr = state.config_json.get("agent_instructions")
            if agent_instr:
                # Handle both plain string and legacy dict format during transition
                if isinstance(agent_instr, str):
                    instructions = agent_instr
                elif isinstance(agent_instr, dict):
                    instructions = agent_instr.get("en", instructions)

        section = flow_template.format(
            flow_id=flow.get('flowId', 'unknown'),
            state_id=flow.get('currentState', 'unknown'),
            instructions=instructions
        )

        # Add enriched context data section if available
        if flow.get("stateData"):
            section += self._format_enriched_data(flow['stateData'])

        return section

    def _format_enriched_data(self, state_data: dict) -> str:
        """
        Format enriched data for LLM visibility.
        Shows all eagerly-loaded data in a clear, structured format.
        """
        if not state_data:
            return ""

        import json

        section = "\n\n### Available Context Data\n\n"
        section += "The following data has been loaded for you to use in your response. "
        section += "**Do not call tools to fetch this data again** - it is already provided below. "
        section += "Format and present it naturally:\n\n"

        for key, value in state_data.items():
            section += f"**{key}:**\n"
            section += f"```json\n{json.dumps(value, indent=2, ensure_ascii=False)}\n```\n\n"

        return section

    def _format_agent_enriched_data(self, agent_data: dict) -> str:
        """
        Format agent-level enriched data for LLM visibility.
        Similar to _format_enriched_data but for agent-level context.
        """
        if not agent_data:
            return ""

        import json

        section = "\n## Agent Context Data\n\n"
        section += "The following data has been loaded for this agent to use in your response. "
        section += "**Do not call tools to fetch this data again** - it is already provided below. "
        section += "Format and present it naturally:\n\n"

        for key, value in agent_data.items():
            section += f"**{key}:**\n"
            section += f"```json\n{json.dumps(value, indent=2, ensure_ascii=False)}\n```\n\n"

        return section

    def _build_confirmation_section(self, session: ConversationSession) -> str:
        """Build the pending confirmation section."""
        pending = session.pending_confirmation
        prompts = load_prompts()

        confirm_template = prompts.get("sections", {}).get(
            "confirmation_pending",
            "\n## PENDING CONFIRMATION\nThe user must confirm the following action before you can proceed:\n{display_message}\n\nWait for explicit confirmation before executing {tool_name}."
        )

        return confirm_template.format(
            display_message=pending.get('displayMessage', ''),
            tool_name=pending.get('toolName', '')
        )

    def _build_navigation_section(self, agent: Agent) -> str:
        """Build navigation instructions based on agent capabilities."""
        nav = agent.navigation_tools or {}
        lines = []
        prompts = load_prompts()
        sections_config = prompts.get("sections", {})

        # Core instruction for all non-root agents about scope awareness
        if agent.parent_agent_id is not None:
            scope_rule = sections_config.get(
                "scope_rule",
                "\n## CRITICAL SCOPE RULE\nYou have a specific scope. If the user asks for anything outside that scope, call go_home immediately."
            )
            lines.append(scope_rule)

        nav_header = sections_config.get("navigation", "\n## Navigation")
        # Only add header if it's not already a full section
        if "go_home" not in nav_header and "escalate" not in nav_header:
            lines.append("\n## Navigation")

            # go_home is automatic for non-root agents
            if agent.parent_agent_id is not None:
                lines.append("- Use 'go_home' to transfer to main assistant")
            if nav.get("canGoUp"):
                lines.append("- Use 'up_one_level' to go back to previous menu")
            if nav.get("canEscalate"):
                lines.append("- Use 'escalate_to_human' if user needs to speak with a person")

        return "\n".join(lines)

    def _build_tools(
        self, agent: Agent, current_flow_state: Optional[SubflowState] = None
    ) -> List[dict]:
        """Build the tools array for OpenAI."""
        tools = []

        # Add agent-level tools
        for tool in agent.tools:
            tools.append(self._tool_to_openai(tool))

        # Add state-specific tools if in a flow
        if current_flow_state and current_flow_state.state_tools:
            resolved_state_tools = self._resolve_state_tools(
                current_flow_state.state_tools, agent
            )
            tools.extend(resolved_state_tools)

        # Add navigation tools
        nav = agent.navigation_tools or {}
        prompts = load_prompts()
        sections_config = prompts.get("sections", {})

        # go_home is a CORE SYSTEM TOOL - automatically available to all non-root agents
        if agent.parent_agent_id is not None:
            go_home_desc = sections_config.get(
                "go_home_tool",
                "Transfer the conversation to the main assistant. Use this when the user asks for something outside your scope."
            )
            tools.append({
                "name": "go_home",
                "description": go_home_desc,
                "input_schema": {"type": "object", "properties": {}},
            })

        # Optional navigation tools (configured per agent)
        if nav.get("canGoUp"):
            up_desc = sections_config.get(
                "up_one_level_tool",
                "Go back to the previous agent/menu"
            )
            tools.append({
                "name": "up_one_level",
                "description": up_desc,
                "input_schema": {"type": "object", "properties": {}},
            })

        if nav.get("canEscalate"):
            escalate_desc = sections_config.get(
                "escalate_to_human_tool",
                "Escalate to a human agent when the user requests it or when you cannot resolve the issue"
            )
            reason_desc = sections_config.get(
                "escalation_reason",
                "Reason for escalation"
            )
            tools.append({
                "name": "escalate_to_human",
                "description": escalate_desc,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "description": reason_desc,
                        }
                    },
                    "required": ["reason"],
                },
            })

        return tools

    def _tool_to_openai(self, tool: Tool) -> dict:
        """Convert a Tool model to OpenAI format."""
        properties = {}
        required = []

        # Get description - now a plain string
        description = tool.description
        if tool.config_json and "description" in tool.config_json:
            desc = tool.config_json["description"]
            # Handle both plain string and legacy dict format during transition
            if isinstance(desc, str):
                description = desc
            elif isinstance(desc, dict):
                description = desc.get("en", description)

        for param in tool.parameters:
            prop = {"type": param.get("type", "string")}
            param_desc = param.get("description", "")

            # Check for description in config_json (now plain strings)
            if tool.config_json:
                params_config = tool.config_json.get("parameters", [])
                for p in params_config:
                    if p.get("name") == param.get("name") and "description" in p:
                        pd = p["description"]
                        # Handle both plain string and legacy dict format during transition
                        if isinstance(pd, str):
                            param_desc = pd
                        elif isinstance(pd, dict):
                            param_desc = pd.get("en", param_desc)
                        break

            if param_desc:
                prop["description"] = param_desc

            properties[param["name"]] = prop
            if param.get("required", False):
                required.append(param["name"])

        return {
            "name": tool.name,
            "description": description,
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

    def _resolve_state_tools(
        self, state_tools: List, agent: Agent
    ) -> List[dict]:
        """
        Resolve state_tools which may be tool name strings or inline definitions.

        Args:
            state_tools: List of either tool name strings or inline tool dicts
            agent: Current agent to look up tool definitions

        Returns:
            List of resolved tool definitions in OpenAI format
        """
        resolved = []
        for tool_ref in state_tools:
            if isinstance(tool_ref, str):
                # It's a tool name reference - look up from agent's tools
                found = False
                for tool in agent.tools:
                    if tool.name == tool_ref:
                        resolved.append(self._tool_to_openai(tool))
                        found = True
                        break
                if not found:
                    logger.warning(
                        f"State tool '{tool_ref}' not found in agent {agent.config_id}"
                    )
            elif isinstance(tool_ref, dict):
                # It's an inline tool definition
                resolved.append(self._inline_tool_to_openai(tool_ref))
            else:
                logger.warning(f"Unknown state_tools entry type: {type(tool_ref)}")
        return resolved

    def _inline_tool_to_openai(self, tool_def: dict) -> dict:
        """Convert an inline tool definition to OpenAI format."""
        properties = {}
        required = []

        # Get description - now a plain string
        description = tool_def.get("description", "")
        # Handle both plain string and legacy dict format during transition
        if isinstance(description, dict):
            description = description.get("en", "")

        for param in tool_def.get("parameters", []):
            prop = {"type": param.get("type", "string")}
            param_desc = param.get("description", "")
            # Handle both plain string and legacy dict format during transition
            if isinstance(param_desc, dict):
                param_desc = param_desc.get("en", "")
            if param_desc:
                prop["description"] = param_desc
            properties[param["name"]] = prop
            if param.get("required", False):
                required.append(param["name"])

        return {
            "name": tool_def["name"],
            "description": description,
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }


# Global assembler instance
_context_assembler: Optional[ContextAssembler] = None


def get_context_assembler() -> ContextAssembler:
    """Get or create the context assembler singleton."""
    global _context_assembler
    if _context_assembler is None:
        _context_assembler = ContextAssembler()
    return _context_assembler
