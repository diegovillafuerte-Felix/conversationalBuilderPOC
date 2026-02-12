"""Context assembler for building LLM prompts with token budgets."""

import json
import logging
from typing import Optional, List
from dataclasses import dataclass

import tiktoken

from app.config import get_settings
from app.models.session import ConversationSession
from app.models.user import UserContext
from app.models.conversation import ConversationMessage
from app.core.config_loader import load_prompts
from app.core.config_types import AgentConfig, ToolConfig, SubflowStateConfig, PromptMode
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
        agent: AgentConfig,
        user_context: Optional[UserContext] = None,
        recent_messages: Optional[List[ConversationMessage]] = None,
        compacted_history: Optional[str] = None,
        current_flow_state: Optional[SubflowStateConfig] = None,
        context_requirements: Optional[List[dict]] = None,
        mode: PromptMode = PromptMode.FULL,
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
            mode: Context assembly mode (FULL or ROUTING)

        Returns:
            AssembledContext with system prompt, messages, tools, and config
        """
        # Determine user's language preference
        language = DEFAULT_LANGUAGE
        if user_context:
            language = user_context.get_language()

        # ROUTING mode: minimal context for routing decisions
        if mode == PromptMode.ROUTING:
            return self._build_routing_context(agent, user_message, language)

        token_counts = {}

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

        # Explicit context requirements (config-driven deterministic enrichment)
        effective_requirements = context_requirements if context_requirements is not None else agent.context_requirements
        if user_context and effective_requirements:
            requirements_section = self._build_context_requirements_section(
                user_context=user_context,
                requirements=effective_requirements,
            )
            if requirements_section:
                requirements_section = truncate_to_tokens(
                    requirements_section, self.budgets["product_context"]
                )
                sections.append(requirements_section)
                token_counts["context_requirements"] = count_tokens(requirements_section)

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
        model_cfg = agent.model_config or {}
        model = model_cfg.get("model", settings.default_model)
        temperature = model_cfg.get("temperature", settings.default_temperature)
        max_tokens = model_cfg.get("maxTokens", settings.default_max_tokens)

        return AssembledContext(
            system_prompt=system_prompt,
            messages=messages,
            tools=tools,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            token_counts=token_counts,
        )

    def _build_agent_section(self, agent: AgentConfig) -> str:
        """Build the agent role section."""
        prompts = load_prompts()
        role_template = prompts.get("sections", {}).get(
            "your_current_role", "\n## Your Current Role\n{description}"
        )

        # Get agent description from config
        description = agent.description
        section = role_template.format(description=description)

        # Add system prompt addition
        if agent.system_prompt_addition:
            section += f"\n\n{agent.system_prompt_addition}"

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
        self, user_context: UserContext, agent: AgentConfig
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

    def _build_context_requirements_section(
        self,
        user_context: UserContext,
        requirements: List[dict],
    ) -> Optional[str]:
        """Build deterministic context blocks requested by agent config."""
        if not requirements:
            return None

        lines: List[str] = ["\n## Required Context"]

        for requirement in requirements:
            req_type = requirement.get("type")
            if req_type == "product_summary":
                product_key = requirement.get("productFilter")
                summary = (user_context.product_summaries or {}).get(product_key)
                if summary:
                    lines.append(f"- Product summary ({product_key}): {summary}")
                continue

            if req_type == "behavioral_summary":
                if user_context.behavioral_summary:
                    lines.append(f"- Behavioral summary: {user_context.behavioral_summary}")
                continue

            if req_type == "profile_fields":
                fields = requirement.get("fields", [])
                if not isinstance(fields, list):
                    continue
                profile = user_context.profile or {}
                extracted = {field: profile.get(field) for field in fields if field in profile}
                if extracted:
                    lines.append(f"- Profile fields: {extracted}")
                continue

        if len(lines) == 1:
            return None

        return "\n".join(lines)

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
        self, session: ConversationSession, state: SubflowStateConfig
    ) -> str:
        """Build the current flow state section."""
        flow = session.current_flow or {}
        prompts = load_prompts()

        flow_template = prompts.get("sections", {}).get(
            "flow_state",
            "\n## Current Flow State\nFlow: {flow_id}\nState: {state_id}\n\n### Instructions for this state:\n{instructions}"
        )

        # Get instructions from config
        instructions = state.agent_instructions

        section = flow_template.format(
            flow_id=flow.get('flowId', 'unknown'),
            state_id=flow.get('currentState', 'unknown'),
            instructions=instructions
        )

        # Append collected stateData so the LLM can see what's been gathered
        state_data = flow.get('stateData', {}) or {}
        visible_data = {k: v for k, v in state_data.items() if not k.startswith('_')}
        if visible_data:
            collected_template = prompts.get("sections", {}).get(
                "collected_data", "\nCollected data: {data}"
            )
            section += collected_template.format(data=json.dumps(visible_data, default=str))

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

    def _build_navigation_section(self, agent: AgentConfig) -> str:
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
        self, agent: AgentConfig, current_flow_state: Optional[SubflowStateConfig] = None
    ) -> List[dict]:
        """
        Build the tools array for OpenAI.

        Tool selection priority:
        1. If in flow with state_tools: ONLY those tools (plus navigation)
        2. If in flow without state_tools: ONLY navigation tools
        3. If not in flow AND agent has default_tools: use default_tools whitelist
        4. If not in flow AND no default_tools: all agent tools (plus navigation)
        """
        tools = []

        if current_flow_state:
            # IN A FLOW STATE - use whitelist-only mode
            state_tools = current_flow_state.state_tools

            if state_tools:
                # Whitelist mode: only tools explicitly listed in state_tools
                allowed_names = set(state_tools)
                agent_tool_names = [t.name for t in agent.tools]
                logger.debug(
                    f"Flow state {current_flow_state.state_id}: resolving state_tools {state_tools} "
                    f"against agent tools {agent_tool_names}"
                )

                for tool in agent.tools:
                    if tool.name in allowed_names:
                        tools.append(tool.to_openai_tool())

                logger.debug(f"Flow state {current_flow_state.state_id}: {len(tools)} whitelisted tools")

                # FAIL-SAFE: If whitelist resolved to ZERO tools, something is wrong
                # Fall back to all agent tools rather than leaving LLM with only navigation
                if not tools and agent.tools:
                    logger.warning(
                        f"TOOL RESOLUTION FAILED: state_tools {state_tools} resolved to 0 tools. "
                        f"Agent {agent.config_id} has tools: {agent_tool_names}. "
                        f"Falling back to all agent tools as safety net."
                    )
                    for tool in agent.tools:
                        tools.append(tool.to_openai_tool())
            else:
                # Empty state_tools - only navigation will be available
                logger.warning(
                    f"Flow state {current_flow_state.state_id} has no state_tools defined - "
                    "only navigation tools will be available"
                )
        elif agent.default_tools:
            # NOT IN FLOW - use default_tools whitelist if defined
            tools = self._resolve_state_tools(agent.default_tools, agent)
            logger.debug(
                f"Agent {agent.config_id}: using default_tools whitelist, "
                f"{len(tools)} of {len(agent.tools)} tools"
            )
        else:
            # NOT IN A FLOW, NO WHITELIST - all agent tools available
            for tool in agent.tools:
                tools.append(tool.to_openai_tool())

        # Add navigation tools (always available)
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

    def _resolve_state_tools(
        self, state_tools: List, agent: AgentConfig
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
                tool = agent.get_tool(tool_ref)
                if tool:
                    resolved.append(tool.to_openai_tool())
                else:
                    logger.warning(
                        f"State tool '{tool_ref}' not found in agent {agent.config_id}"
                    )
            elif isinstance(tool_ref, dict):
                # It's an inline tool definition - convert using ToolConfig
                inline_tool = ToolConfig.from_dict(tool_ref)
                resolved.append(inline_tool.to_openai_tool())
            else:
                logger.warning(f"Unknown state_tools entry type: {type(tool_ref)}")
        return resolved

    def _build_routing_context(
        self, agent: AgentConfig, user_message: str, language: str
    ) -> AssembledContext:
        """
        Build minimal context for routing decisions only.

        This mode is used during routing chain iterations (after the first)
        when the LLM only needs to make a routing decision, not handle
        the full conversation. Reduces tokens by ~80%.

        Includes:
        - Minimal system prompt (~50 tokens)
        - Brief agent capabilities (first line of description)
        - Language directive (required)
        - Single user message (no history)
        - Only routing tools (tools with routing config)
        """
        token_counts = {}

        # Minimal system prompt
        system_prompt = "You are routing a user request. Call the appropriate tool to handle it."
        token_counts["base_prompt"] = count_tokens(system_prompt)

        # Brief agent capabilities (first line only)
        description_first_line = agent.description.split("\n")[0] if agent.description else ""
        if description_first_line:
            system_prompt += f"\n\nCapabilities: {description_first_line}"
            token_counts["agent_description"] = count_tokens(description_first_line)

        # Add language directive
        language_directive = get_language_directive(language)
        system_prompt += f"\n\n{language_directive}"
        token_counts["language_directive"] = count_tokens(language_directive)

        token_counts["total_system"] = count_tokens(system_prompt)

        # Single user message only (no history)
        messages = [{"role": "user", "content": user_message}]
        token_counts["messages"] = count_tokens(user_message)

        # Only routing tools
        tools = self._build_routing_tools(agent)
        token_counts["tools"] = count_tokens(str(tools))

        # Use agent's model config
        model_cfg = agent.model_config or {}
        model = model_cfg.get("model", settings.default_model)
        temperature = model_cfg.get("temperature", settings.default_temperature)
        max_tokens = model_cfg.get("maxTokens", settings.default_max_tokens)

        logger.debug(
            f"ROUTING mode context: {token_counts['total_system']} system tokens, "
            f"{len(tools)} routing tools"
        )

        return AssembledContext(
            system_prompt=system_prompt,
            messages=messages,
            tools=tools,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            token_counts=token_counts,
        )

    def _build_routing_tools(self, agent: AgentConfig) -> List[dict]:
        """
        Build tools array containing only routing tools.

        Routing tools are those with a non-None routing config (enter_agent,
        start_flow, navigation). This excludes service tools like get_exchange_rate.
        """
        tools = []
        tool_names_added = set()

        for tool in agent.tools:
            if tool.routing is not None:
                tools.append(tool.to_openai_tool())
                tool_names_added.add(tool.name)

        # Add navigation tools if not already present (from agent tools with routing)
        nav = agent.navigation_tools or {}
        prompts = load_prompts()
        sections_config = prompts.get("sections", {})

        # go_home for non-root agents (if not already added)
        if agent.parent_agent_id is not None and "go_home" not in tool_names_added:
            go_home_desc = sections_config.get(
                "go_home_tool",
                "Transfer the conversation to the main assistant."
            )
            tools.append({
                "name": "go_home",
                "description": go_home_desc,
                "input_schema": {"type": "object", "properties": {}},
            })

        if nav.get("canGoUp") and "up_one_level" not in tool_names_added:
            tools.append({
                "name": "up_one_level",
                "description": "Go back to the previous agent/menu",
                "input_schema": {"type": "object", "properties": {}},
            })

        if nav.get("canEscalate") and "escalate_to_human" not in tool_names_added:
            tools.append({
                "name": "escalate_to_human",
                "description": "Escalate to a human agent",
                "input_schema": {
                    "type": "object",
                    "properties": {"reason": {"type": "string"}},
                    "required": ["reason"],
                },
            })

        return tools


# Global assembler instance
_context_assembler: Optional[ContextAssembler] = None


def get_context_assembler() -> ContextAssembler:
    """Get or create the context assembler singleton."""
    global _context_assembler
    if _context_assembler is None:
        _context_assembler = ContextAssembler()
    return _context_assembler
