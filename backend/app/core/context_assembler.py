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
    get_localized,
    get_base_system_prompt,
    get_prompt_section,
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

        # Base system prompt (from JSON config)
        base_prompt = get_base_system_prompt(language)
        sections.append(base_prompt)
        token_counts["base_prompt"] = count_tokens(base_prompt)

        # Agent description
        agent_section = self._build_agent_section(agent, language)
        agent_section = truncate_to_tokens(
            agent_section, self.budgets["system_prompt"] - token_counts["base_prompt"]
        )
        sections.append(agent_section)
        token_counts["agent_description"] = count_tokens(agent_section)

        # User profile
        if user_context:
            user_section = self._build_user_section(user_context, language)
            user_section = truncate_to_tokens(user_section, self.budgets["user_profile"])
            sections.append(user_section)
            token_counts["user_profile"] = count_tokens(user_section)

        # Product context (if in a product agent)
        if user_context and agent.parent_agent_id:
            product_section = self._build_product_context(user_context, agent, language)
            if product_section:
                product_section = truncate_to_tokens(
                    product_section, self.budgets["product_context"]
                )
                sections.append(product_section)
                token_counts["product_context"] = count_tokens(product_section)

        # Compacted history
        if compacted_history:
            prompts = load_prompts()
            history_template = get_localized(
                prompts.get("sections", {}).get("previous_history", {}),
                language,
                "\n## Previous Conversation History\n{history}"
            )
            history_section = history_template.format(history=compacted_history)
            history_section = truncate_to_tokens(
                history_section, self.budgets["conversation_compacted"]
            )
            sections.append(history_section)
            token_counts["compacted_history"] = count_tokens(history_section)

        # Current flow state
        if session.current_flow and current_flow_state:
            state_section = self._build_flow_state_section(session, current_flow_state, language)
            state_section = truncate_to_tokens(state_section, self.budgets["current_state"])
            sections.append(state_section)
            token_counts["flow_state"] = count_tokens(state_section)

        # Pending confirmation
        if session.pending_confirmation:
            confirm_section = self._build_confirmation_section(session, language)
            sections.append(confirm_section)
            token_counts["pending_confirmation"] = count_tokens(confirm_section)

        # Build navigation instructions
        nav_section = self._build_navigation_section(agent, language)
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

        # 3. Build tools array
        tools = self._build_tools(agent, current_flow_state, language)
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

    def _build_agent_section(self, agent: Agent, language: str) -> str:
        """Build the agent role section."""
        prompts = load_prompts()
        role_template = get_localized(
            prompts.get("sections", {}).get("your_current_role", {}),
            language,
            "\n## Your Current Role\n{description}"
        )

        # Get localized agent description if available in config_json
        description = agent.description
        if agent.config_json and "description" in agent.config_json:
            description = get_localized(agent.config_json["description"], language, description)

        section = role_template.format(description=description)

        # Add system prompt addition
        if agent.system_prompt_addition:
            addition = agent.system_prompt_addition
            if agent.config_json and "system_prompt_addition" in agent.config_json:
                addition = get_localized(
                    agent.config_json["system_prompt_addition"], language, addition
                )
            section += f"\n\n{addition}"

        return section

    def _build_user_section(self, user_context: UserContext, language: str) -> str:
        """Build the user profile section."""
        prompts = load_prompts()
        sections_config = prompts.get("sections", {})

        name = user_context.get_preferred_name()

        user_template = get_localized(
            sections_config.get("user_section", {}),
            language,
            "\n## User\nName: {name}"
        )
        sections = [user_template.format(name=name)]

        if user_context.behavioral_summary:
            context_template = get_localized(
                sections_config.get("user_context", {}),
                language,
                "\n## User Context\n{behavioral_summary}"
            )
            sections.append(context_template.format(behavioral_summary=user_context.behavioral_summary))

        return "\n".join(sections)

    def _build_product_context(
        self, user_context: UserContext, agent: Agent, language: str
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
        product_template = get_localized(
            prompts.get("sections", {}).get("product_context", {}),
            language,
            "\n## {agent_name} Context\n{summary}"
        )

        agent_name_lower = agent.name.lower()
        for key, product_key in agent_to_product.items():
            if key in agent_name_lower:
                summary = user_context.product_summaries.get(product_key)
                if summary:
                    formatted_summary = self._format_product_summary(product_key, summary, language)
                    return product_template.format(
                        agent_name=agent.name,
                        summary=formatted_summary
                    )

        return None

    def _format_product_summary(self, product: str, summary: dict, language: str) -> str:
        """Format a product summary for the prompt."""
        prompts = load_prompts()
        labels = prompts.get("sections", {}).get("product_labels", {})
        lines = []

        if product == "remittances":
            remit_labels = labels.get("remittances", {})
            if "lifetimeCount" in summary:
                label = get_localized(remit_labels.get("lifetime_count", {}), language, "Total transfers")
                lines.append(f"- {label}: {summary['lifetimeCount']}")
            if "lastTransactionAt" in summary:
                label = get_localized(remit_labels.get("last_transaction", {}), language, "Last transfer")
                lines.append(f"- {label}: {summary['lastTransactionAt']}")
            if "frequentRecipients" in summary:
                recipients = summary["frequentRecipients"]
                if recipients:
                    names = [r.get("name", "Unknown") for r in recipients[:3]]
                    label = get_localized(remit_labels.get("frequent_recipients", {}), language, "Frequent recipients")
                    lines.append(f"- {label}: {', '.join(names)}")

        elif product == "credit":
            credit_labels = labels.get("credit", {})
            if "hasActiveCredit" in summary:
                label = get_localized(credit_labels.get("active_credit", {}), language, "Active credit")
                yes_no = get_localized(credit_labels.get("yes" if summary["hasActiveCredit"] else "no", {}), language, "Yes" if summary["hasActiveCredit"] else "No")
                lines.append(f"- {label}: {yes_no}")
            if "currentBalance" in summary:
                label = get_localized(credit_labels.get("current_balance", {}), language, "Current balance")
                lines.append(f"- {label}: ${summary['currentBalance']:.2f}")
            if "creditLimit" in summary:
                label = get_localized(credit_labels.get("limit", {}), language, "Limit")
                lines.append(f"- {label}: ${summary['creditLimit']:.2f}")

        elif product == "wallet":
            wallet_labels = labels.get("wallet", {})
            if "currentBalance" in summary:
                label = get_localized(wallet_labels.get("balance", {}), language, "Balance")
                lines.append(f"- {label}: ${summary['currentBalance']:.2f}")

        return "\n".join(lines) if lines else str(summary)

    def _build_flow_state_section(
        self, session: ConversationSession, state: SubflowState, language: str
    ) -> str:
        """Build the current flow state section."""
        flow = session.current_flow or {}
        prompts = load_prompts()

        flow_template = get_localized(
            prompts.get("sections", {}).get("flow_state", {}),
            language,
            "\n## Current Flow State\nFlow: {flow_id}\nState: {state_id}\n\n### Instructions for this state:\n{instructions}"
        )

        # Get localized instructions if available in state config
        instructions = state.agent_instructions
        if hasattr(state, 'config_json') and state.config_json:
            agent_instr = state.config_json.get("agent_instructions", {})
            if isinstance(agent_instr, dict):
                instructions = get_localized(agent_instr, language, instructions)

        section = flow_template.format(
            flow_id=flow.get('flowId', 'unknown'),
            state_id=flow.get('currentState', 'unknown'),
            instructions=instructions
        )

        if flow.get("stateData"):
            collected_template = get_localized(
                prompts.get("sections", {}).get("collected_data", {}),
                language,
                "\nCollected data: {data}"
            )
            section += collected_template.format(data=flow['stateData'])

        return section

    def _build_confirmation_section(self, session: ConversationSession, language: str) -> str:
        """Build the pending confirmation section."""
        pending = session.pending_confirmation
        prompts = load_prompts()

        confirm_template = get_localized(
            prompts.get("sections", {}).get("confirmation_pending", {}),
            language,
            "\n## PENDING CONFIRMATION\nThe user must confirm the following action before you can proceed:\n{display_message}\n\nWait for explicit confirmation before executing {tool_name}."
        )

        return confirm_template.format(
            display_message=pending.get('displayMessage', ''),
            tool_name=pending.get('toolName', '')
        )

    def _build_navigation_section(self, agent: Agent, language: str) -> str:
        """Build navigation instructions based on agent capabilities."""
        nav = agent.navigation_tools or {}
        lines = []
        prompts = load_prompts()
        sections_config = prompts.get("sections", {})

        # Core instruction for all non-root agents about scope awareness
        if agent.parent_agent_id is not None:
            scope_rule = get_localized(
                sections_config.get("scope_rule", {}),
                language,
                "\n## CRITICAL SCOPE RULE\nYou have a specific scope. If the user asks for anything outside that scope, call go_home immediately."
            )
            lines.append(scope_rule)

        nav_header = get_localized(
            sections_config.get("navigation", {}),
            language,
            "\n## Navigation"
        )
        # Only add header if it's not already a full section
        if "go_home" not in nav_header and "escalate" not in nav_header:
            lines.append("\n## Navigation" if language == "en" else "\n## Navegación")

            # go_home is automatic for non-root agents
            if agent.parent_agent_id is not None:
                go_home_text = "Use 'go_home' to transfer to main assistant" if language == "en" else "Usa 'go_home' para transferir al asistente principal"
                lines.append(f"- {go_home_text}")
            if nav.get("canGoUp"):
                up_text = "Use 'up_one_level' to go back to previous menu" if language == "en" else "Usa 'up_one_level' para volver al menú anterior"
                lines.append(f"- {up_text}")
            if nav.get("canEscalate"):
                escalate_text = "Use 'escalate_to_human' if user needs to speak with a person" if language == "en" else "Usa 'escalate_to_human' si el usuario necesita hablar con una persona"
                lines.append(f"- {escalate_text}")

        return "\n".join(lines)

    def _build_tools(
        self, agent: Agent, current_flow_state: Optional[SubflowState] = None, language: str = DEFAULT_LANGUAGE
    ) -> List[dict]:
        """Build the tools array for OpenAI."""
        tools = []

        # Add agent-level tools
        for tool in agent.tools:
            tools.append(self._tool_to_openai(tool, language))

        # Add state-specific tools if in a flow
        if current_flow_state and current_flow_state.state_tools:
            for tool_def in current_flow_state.state_tools:
                tools.append(self._inline_tool_to_openai(tool_def, language))

        # Add navigation tools
        nav = agent.navigation_tools or {}
        prompts = load_prompts()
        sections_config = prompts.get("sections", {})

        # go_home is a CORE SYSTEM TOOL - automatically available to all non-root agents
        if agent.parent_agent_id is not None:
            go_home_desc = get_localized(
                sections_config.get("go_home_tool", {}),
                language,
                "Transfer the conversation to the main assistant. Use this when the user asks for something outside your scope."
            )
            tools.append({
                "name": "go_home",
                "description": go_home_desc,
                "input_schema": {"type": "object", "properties": {}},
            })

        # Optional navigation tools (configured per agent)
        if nav.get("canGoUp"):
            up_desc = get_localized(
                sections_config.get("up_one_level_tool", {}),
                language,
                "Go back to the previous agent/menu"
            )
            tools.append({
                "name": "up_one_level",
                "description": up_desc,
                "input_schema": {"type": "object", "properties": {}},
            })

        if nav.get("canEscalate"):
            escalate_desc = get_localized(
                sections_config.get("escalate_to_human_tool", {}),
                language,
                "Escalate to a human agent when the user requests it or when you cannot resolve the issue"
            )
            reason_desc = get_localized(
                sections_config.get("escalation_reason", {}),
                language,
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

    def _tool_to_openai(self, tool: Tool, language: str) -> dict:
        """Convert a Tool model to OpenAI format with localization."""
        properties = {}
        required = []

        # Get localized description
        description = tool.description
        if tool.config_json and "description" in tool.config_json:
            description = get_localized(tool.config_json["description"], language, description)

        for param in tool.parameters:
            prop = {"type": param.get("type", "string")}
            param_desc = param.get("description", "")

            # Check for localized description in config_json
            if tool.config_json:
                params_config = tool.config_json.get("parameters", [])
                for p in params_config:
                    if p.get("name") == param.get("name") and "description" in p:
                        param_desc = get_localized(p["description"], language, param_desc)
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

    def _inline_tool_to_openai(self, tool_def: dict, language: str = DEFAULT_LANGUAGE) -> dict:
        """Convert an inline tool definition to OpenAI format."""
        properties = {}
        required = []

        # Get localized description
        description = tool_def.get("description", "")
        if isinstance(description, dict):
            description = get_localized(description, language, "")

        for param in tool_def.get("parameters", []):
            prop = {"type": param.get("type", "string")}
            param_desc = param.get("description", "")
            if isinstance(param_desc, dict):
                param_desc = get_localized(param_desc, language, "")
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
