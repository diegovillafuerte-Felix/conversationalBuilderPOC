"""
Shadow Subagents - Base class and implementations for shadow subagents
that evaluate conversations and inject contextual messages.
"""
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Dict, Any

from app.core.llm_client import LLMClient
from app.core.shadow_service import SubagentConfig, SubagentResult
from app.models.session import ConversationSession
from app.models.user import UserContext

logger = logging.getLogger(__name__)


class ShadowSubagent(ABC):
    """
    Base class for shadow subagents. Each subagent evaluates conversations
    and can inject contextual messages or trigger activation.
    """

    def __init__(self, llm_client: LLMClient, config: SubagentConfig):
        self.llm_client = llm_client
        self.config = config

    @abstractmethod
    async def evaluate(
        self,
        user_message: str,
        session: ConversationSession,
        user_context: Optional[UserContext],
        recent_messages: List[Any],
        language: str = "en",
    ) -> SubagentResult:
        """
        Evaluate the conversation and return a result.

        Args:
            user_message: The user's message
            session: Current conversation session
            user_context: User profile and context
            recent_messages: Recent conversation history
            language: Language code (en/es)

        Returns:
            SubagentResult with relevance score, optional message, and activation info
        """
        pass

    def _build_system_prompt(self, language: str, additional_context: str = "") -> str:
        """Build the system prompt for the subagent LLM call."""
        tone = self.config.tone.get(language, self.config.tone.get("en", ""))
        prompt_addition = self.config.system_prompt_addition.get(
            language, self.config.system_prompt_addition.get("en", "")
        )

        return f"""You are a shadow advisor that evaluates conversations to provide helpful, contextual tips.

Your tone should be: {tone}

{prompt_addition}

{additional_context}

You must respond with a JSON object in this exact format:
{{
    "relevance_score": <number 0-100>,
    "message": "<your tip or null if not relevant>",
    "activation_detected": <boolean>,
    "activation_intent": "<intent category or null>"
}}

Guidelines:
- relevance_score: How relevant is providing a tip right now? (0 = not at all, 100 = extremely relevant)
- message: A helpful tip/suggestion. Keep it under {self.config.max_tip_length} characters. Set to null if relevance < 50.
- activation_detected: True if the user is explicitly asking for deeper help in your domain
- activation_intent: The category of intent if activation is detected (e.g., "budgeting_help", "savings_advice")

Valid activation intents: {json.dumps(self.config.activation_intents)}

Be conservative with your relevance scores. Only score high (>80) when your tip would be genuinely valuable.
"""

    def _build_conversation_context(
        self,
        user_message: str,
        recent_messages: List[Any],
        max_messages: int = 10,
    ) -> str:
        """Build conversation context string from recent messages."""
        context_parts = []

        # Add recent messages
        for msg in recent_messages[-max_messages:]:
            role = getattr(msg, 'role', 'unknown')
            content = getattr(msg, 'content', str(msg))
            context_parts.append(f"{role}: {content}")

        # Add current message
        context_parts.append(f"user: {user_message}")

        return "\n".join(context_parts)

    async def _call_llm(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Call the LLM and parse the JSON response."""
        try:
            response = await self.llm_client.complete(
                system_prompt=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=500,
            )

            # Parse JSON response
            response_text = response.get("content", "{}") if isinstance(response, dict) else str(response)

            # Try to extract JSON from the response
            try:
                # Handle case where response might have markdown code blocks
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0]
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0]

                return json.loads(response_text.strip())
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON from subagent response: {response_text[:200]}")
                return {
                    "relevance_score": 0,
                    "message": None,
                    "activation_detected": False,
                    "activation_intent": None,
                }

        except Exception as e:
            logger.error(f"LLM call failed for subagent {self.config.id}: {e}")
            raise


class FinancialAdvisorSubagent(ShadowSubagent):
    """
    Financial advisor subagent that provides tips about budgeting,
    savings, fees, and financial planning.
    """

    async def evaluate(
        self,
        user_message: str,
        session: ConversationSession,
        user_context: Optional[UserContext],
        recent_messages: List[Any],
        language: str = "en",
    ) -> SubagentResult:
        """Evaluate for financial advice opportunities."""
        try:
            # Build financial context
            financial_context = self._build_financial_context(user_context, session, language)

            # Build system prompt
            system_prompt = self._build_system_prompt(
                language=language,
                additional_context=financial_context,
            )

            # Build user prompt with conversation
            conversation = self._build_conversation_context(user_message, recent_messages)
            user_prompt = f"""Analyze this conversation and determine if there's an opportunity to provide financial advice.

Conversation:
{conversation}

Remember: Only provide tips when genuinely helpful. Score conservatively."""

            # Call LLM
            result = await self._call_llm(system_prompt, user_prompt)

            return SubagentResult(
                subagent_id=self.config.id,
                relevance_score=result.get("relevance_score", 0),
                message=result.get("message"),
                activation_detected=result.get("activation_detected", False),
                activation_intent=result.get("activation_intent"),
            )

        except Exception as e:
            logger.error(f"Financial advisor evaluation failed: {e}")
            return SubagentResult(
                subagent_id=self.config.id,
                relevance_score=0,
                error=str(e),
            )

    def _build_financial_context(
        self,
        user_context: Optional[UserContext],
        session: ConversationSession,
        language: str,
    ) -> str:
        """Build context about user's financial situation."""
        context_parts = []

        if user_context and hasattr(user_context, 'profile'):
            profile = user_context.profile or {}

            # Add user financial summary if available
            if 'wallet_balance' in profile:
                context_parts.append(f"Wallet balance: ${profile['wallet_balance']:.2f}")

            if 'kyc_level' in profile:
                context_parts.append(f"KYC level: {profile['kyc_level']}")

            if 'transaction_count' in profile:
                context_parts.append(f"Total transactions: {profile['transaction_count']}")

            if 'avg_transfer_amount' in profile:
                context_parts.append(f"Average transfer amount: ${profile['avg_transfer_amount']:.2f}")

        # Add current agent context
        if hasattr(session, 'agent_stack') and session.agent_stack:
            current_agent = session.agent_stack[-1].get('agentId', 'unknown')
            context_parts.append(f"Currently in: {current_agent}")

        if context_parts:
            header = "User financial context:" if language == "en" else "Contexto financiero del usuario:"
            return f"{header}\n" + "\n".join(f"- {part}" for part in context_parts)

        return ""


class CampaignsSubagent(ShadowSubagent):
    """
    Campaigns subagent that surfaces relevant promotions and new features.
    """

    async def evaluate(
        self,
        user_message: str,
        session: ConversationSession,
        user_context: Optional[UserContext],
        recent_messages: List[Any],
        language: str = "en",
    ) -> SubagentResult:
        """Evaluate for campaign/promotion opportunities."""
        try:
            # Get active campaigns
            active_campaigns = self._get_active_campaigns()

            if not active_campaigns:
                return SubagentResult(
                    subagent_id=self.config.id,
                    relevance_score=0,
                )

            # Build campaign context
            campaign_context = self._build_campaign_context(active_campaigns, user_context, language)

            # Build system prompt
            system_prompt = self._build_system_prompt(
                language=language,
                additional_context=campaign_context,
            )

            # Build user prompt with conversation
            conversation = self._build_conversation_context(user_message, recent_messages)
            user_prompt = f"""Analyze this conversation and determine if any of the active campaigns/promotions would be relevant to mention.

Conversation:
{conversation}

Remember: Only mention promotions when contextually appropriate. Don't be pushy."""

            # Call LLM
            result = await self._call_llm(system_prompt, user_prompt)

            return SubagentResult(
                subagent_id=self.config.id,
                relevance_score=result.get("relevance_score", 0),
                message=result.get("message"),
                activation_detected=result.get("activation_detected", False),
                activation_intent=result.get("activation_intent"),
            )

        except Exception as e:
            logger.error(f"Campaigns evaluation failed: {e}")
            return SubagentResult(
                subagent_id=self.config.id,
                relevance_score=0,
                error=str(e),
            )

    def _get_active_campaigns(self) -> List[Dict[str, Any]]:
        """Get currently active campaigns based on date filtering."""
        if not self.config.active_campaigns:
            return []

        today = datetime.now().date()
        active = []

        for campaign in self.config.active_campaigns:
            start_date = campaign.get("start")
            end_date = campaign.get("end")

            # Parse dates
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
                end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
            except (ValueError, TypeError):
                continue

            # Check if campaign is active
            if start and today < start:
                continue
            if end and today > end:
                continue

            active.append(campaign)

        return active

    def _build_campaign_context(
        self,
        campaigns: List[Dict[str, Any]],
        user_context: Optional[UserContext],
        language: str,
    ) -> str:
        """Build context about active campaigns."""
        context_parts = []

        header = "Active campaigns/promotions:" if language == "en" else "Campanas/promociones activas:"
        context_parts.append(header)

        for campaign in campaigns:
            campaign_id = campaign.get("id", "unknown")
            description = campaign.get("description", {})
            desc_text = description.get(language, description.get("en", campaign_id))
            context_parts.append(f"- {campaign_id}: {desc_text}")

        return "\n".join(context_parts)
