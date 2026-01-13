"""
Shadow Service - Orchestrates multiple shadow subagents that run in parallel
with the main conversation flow to inject contextual messages (tips, promotions, alerts).
"""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any

from app.core.llm_client import LLMClient
from app.models.session import ConversationSession
from app.models.user import UserContext

logger = logging.getLogger(__name__)


@dataclass
class ShadowMessage:
    """A message injected by a shadow subagent."""
    content: str
    source: str  # e.g., "Felix Financial Advisor", "Felix"
    subagent_id: str  # e.g., "financial_advisor", "campaigns"
    message_type: str = "tip"  # tip, promotion, alert
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Activation:
    """Represents a shadow subagent requesting to take over the conversation."""
    target_agent_id: str  # The full agent ID to route to
    subagent_id: str  # Which shadow subagent triggered this
    intent: str  # e.g., "budgeting_help", "savings_advice"
    reason: str = ""  # Human-readable reason for the takeover


@dataclass
class SubagentResult:
    """Result from a single shadow subagent evaluation."""
    subagent_id: str
    relevance_score: float  # 0-100
    message: Optional[str] = None
    activation_detected: bool = False
    activation_intent: Optional[str] = None
    error: Optional[str] = None

    @property
    def has_message(self) -> bool:
        return self.message is not None and len(self.message.strip()) > 0


@dataclass
class ShadowResult:
    """Aggregated result from all shadow subagents."""
    messages: List[ShadowMessage] = field(default_factory=list)
    activation: Optional[Activation] = None
    subagent_results: List[SubagentResult] = field(default_factory=list)

    @property
    def has_messages(self) -> bool:
        return len(self.messages) > 0

    @property
    def has_activation(self) -> bool:
        return self.activation is not None


@dataclass
class SubagentConfig:
    """Configuration for a single shadow subagent."""
    id: str
    enabled: bool
    relevance_threshold: float
    model: str
    temperature: float
    priority: int
    full_agent_id: Optional[str]
    tone: Dict[str, str]
    system_prompt_addition: Dict[str, str]
    activation_intents: List[str]
    max_tip_length: int
    cooldown_messages: int
    source_label: Dict[str, str]
    # Campaigns-specific fields
    active_campaigns: Optional[List[Dict[str, Any]]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SubagentConfig":
        return cls(
            id=data["id"],
            enabled=data.get("enabled", True),
            relevance_threshold=data.get("relevance_threshold", 90),
            model=data.get("model", "gpt-4o-mini"),
            temperature=data.get("temperature", 0.3),
            priority=data.get("priority", 1),
            full_agent_id=data.get("full_agent_id"),
            tone=data.get("tone", {"en": "", "es": ""}),
            system_prompt_addition=data.get("system_prompt_addition", {"en": "", "es": ""}),
            activation_intents=data.get("activation_intents", []),
            max_tip_length=data.get("max_tip_length", 280),
            cooldown_messages=data.get("cooldown_messages", 5),
            source_label=data.get("source_label", {"en": "Felix", "es": "Felix"}),
            active_campaigns=data.get("active_campaigns"),
        )


@dataclass
class ShadowServiceConfig:
    """Configuration for the entire shadow service."""
    enabled: bool
    global_cooldown_messages: int
    max_messages_per_response: int
    subagents: List[SubagentConfig]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ShadowServiceConfig":
        subagents = [
            SubagentConfig.from_dict(s)
            for s in data.get("subagents", [])
        ]
        return cls(
            enabled=data.get("enabled", True),
            global_cooldown_messages=data.get("global_cooldown_messages", 3),
            max_messages_per_response=data.get("max_messages_per_response", 1),
            subagents=subagents,
        )


class ShadowService:
    """
    Orchestrates multiple shadow subagents that run in parallel with the main
    conversation to inject contextual messages and detect activation intents.
    """

    def __init__(self, llm_client: LLMClient, config: ShadowServiceConfig):
        self.llm_client = llm_client
        self.config = config
        self._subagents: Dict[str, "ShadowSubagent"] = {}
        self._initialize_subagents()

    def _initialize_subagents(self):
        """Initialize all configured subagents."""
        from app.core.shadow_subagent import (
            FinancialAdvisorSubagent,
            CampaignsSubagent,
        )

        subagent_classes = {
            "financial_advisor": FinancialAdvisorSubagent,
            "campaigns": CampaignsSubagent,
        }

        for subagent_config in self.config.subagents:
            subagent_class = subagent_classes.get(subagent_config.id)
            if subagent_class:
                self._subagents[subagent_config.id] = subagent_class(
                    llm_client=self.llm_client,
                    config=subagent_config,
                )
            else:
                logger.warning(f"Unknown subagent type: {subagent_config.id}")

    async def evaluate(
        self,
        user_message: str,
        session: ConversationSession,
        user_context: Optional[UserContext],
        recent_messages: List[Any],
        language: str = "en",
    ) -> ShadowResult:
        """
        Evaluate all enabled subagents in parallel.

        Args:
            user_message: The user's message
            session: Current conversation session
            user_context: User profile and context
            recent_messages: Recent conversation history
            language: Language code (en/es)

        Returns:
            ShadowResult with messages and/or activation
        """
        if not self.config.enabled:
            return ShadowResult()

        # Check global cooldown
        if self._is_in_global_cooldown(session):
            logger.debug("Shadow service in global cooldown")
            return ShadowResult()

        # Get enabled subagents
        enabled_subagents = [
            (subagent_id, subagent)
            for subagent_id, subagent in self._subagents.items()
            if subagent.config.enabled and not self._is_subagent_in_cooldown(session, subagent_id)
        ]

        if not enabled_subagents:
            return ShadowResult()

        # Run all subagents in parallel
        tasks = [
            self._evaluate_subagent(
                subagent_id, subagent, user_message, session, user_context, recent_messages, language
            )
            for subagent_id, subagent in enabled_subagents
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        subagent_results: List[SubagentResult] = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Subagent evaluation failed: {result}")
                continue
            if result:
                subagent_results.append(result)

        return self._aggregate_results(subagent_results, session, language)

    async def _evaluate_subagent(
        self,
        subagent_id: str,
        subagent: "ShadowSubagent",
        user_message: str,
        session: ConversationSession,
        user_context: Optional[UserContext],
        recent_messages: List[Any],
        language: str,
    ) -> Optional[SubagentResult]:
        """Evaluate a single subagent with error handling."""
        try:
            return await subagent.evaluate(
                user_message=user_message,
                session=session,
                user_context=user_context,
                recent_messages=recent_messages,
                language=language,
            )
        except Exception as e:
            logger.error(f"Error evaluating subagent {subagent_id}: {e}")
            return SubagentResult(
                subagent_id=subagent_id,
                relevance_score=0,
                error=str(e),
            )

    def _aggregate_results(
        self,
        results: List[SubagentResult],
        session: ConversationSession,
        language: str,
    ) -> ShadowResult:
        """
        Aggregate results from all subagents.
        - If any subagent detected activation, use highest priority one
        - Otherwise, pick top N messages above threshold, ordered by priority
        """
        if not results:
            return ShadowResult()

        # Sort by priority (lower number = higher priority)
        results_with_config = [
            (r, self._subagents[r.subagent_id].config)
            for r in results
            if r.subagent_id in self._subagents
        ]
        results_with_config.sort(key=lambda x: x[1].priority)

        # Check for activation (highest priority first)
        for result, config in results_with_config:
            if result.activation_detected and config.full_agent_id:
                return ShadowResult(
                    activation=Activation(
                        target_agent_id=config.full_agent_id,
                        subagent_id=result.subagent_id,
                        intent=result.activation_intent or "unknown",
                        reason=f"User expressed interest in {result.activation_intent}",
                    ),
                    subagent_results=[r for r, _ in results_with_config],
                )

        # Collect messages above threshold
        messages: List[ShadowMessage] = []
        for result, config in results_with_config:
            if (
                result.has_message
                and result.relevance_score >= config.relevance_threshold
                and len(messages) < self.config.max_messages_per_response
            ):
                source_label = config.source_label.get(language, config.source_label.get("en", "Felix"))
                messages.append(ShadowMessage(
                    content=result.message[:config.max_tip_length],
                    source=source_label,
                    subagent_id=result.subagent_id,
                    message_type="promotion" if result.subagent_id == "campaigns" else "tip",
                    metadata={
                        "relevance_score": result.relevance_score,
                        "priority": config.priority,
                    },
                ))

        return ShadowResult(
            messages=messages,
            subagent_results=[r for r, _ in results_with_config],
        )

    def _is_in_global_cooldown(self, session: ConversationSession) -> bool:
        """Check if shadow service is in global cooldown."""
        shadow_metadata = self._get_shadow_metadata(session)
        last_message_count = shadow_metadata.get("last_global_message_count", 0)
        current_count = self._get_message_count(session)

        return (current_count - last_message_count) < self.config.global_cooldown_messages

    def _is_subagent_in_cooldown(self, session: ConversationSession, subagent_id: str) -> bool:
        """Check if a specific subagent is in cooldown."""
        shadow_metadata = self._get_shadow_metadata(session)
        subagent_cooldowns = shadow_metadata.get("subagent_cooldowns", {})
        last_count = subagent_cooldowns.get(subagent_id, 0)
        current_count = self._get_message_count(session)

        config = self._subagents.get(subagent_id)
        if not config:
            return False

        return (current_count - last_count) < config.config.cooldown_messages

    def _get_shadow_metadata(self, session: ConversationSession) -> Dict[str, Any]:
        """Get shadow service metadata from session."""
        if not hasattr(session, 'metadata') or session.session_metadata is None:
            return {}
        return session.session_metadata.get("shadow_service", {})

    def _get_message_count(self, session: ConversationSession) -> int:
        """Get current message count from session."""
        if not hasattr(session, 'metadata') or session.session_metadata is None:
            return 0
        return session.session_metadata.get("message_count", 0)

    def update_cooldowns(self, session: ConversationSession, triggered_subagent_ids: List[str]):
        """
        Update cooldown counters after shadow messages are sent.
        Call this from the orchestrator after including shadow messages in response.
        """
        if not hasattr(session, 'metadata') or session.session_metadata is None:
            session.session_metadata = {}

        if "shadow_service" not in session.session_metadata:
            session.session_metadata["shadow_service"] = {}

        shadow_metadata = session.session_metadata["shadow_service"]
        current_count = self._get_message_count(session)

        # Update global cooldown
        shadow_metadata["last_global_message_count"] = current_count

        # Update per-subagent cooldowns
        if "subagent_cooldowns" not in shadow_metadata:
            shadow_metadata["subagent_cooldowns"] = {}

        for subagent_id in triggered_subagent_ids:
            shadow_metadata["subagent_cooldowns"][subagent_id] = current_count


# Type hint for forward reference
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.core.shadow_subagent import ShadowSubagent
