"""Conversation history compaction service."""

import logging
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import ConversationMessage, ConversationHistoryCompacted
from app.core.llm_client import get_llm_client

logger = logging.getLogger(__name__)

COMPACTION_THRESHOLD = 30  # messages before compaction triggers
RECENT_MESSAGES_KEEP = 10  # messages to keep in full detail
SUMMARY_TOKEN_TARGET = 300


class HistoryCompactor:
    """Compacts older conversation messages into summaries."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm_client = get_llm_client()

    async def should_compact(self, session_id: str) -> bool:
        """Check if session needs compaction."""
        result = await self.db.execute(
            select(func.count(ConversationMessage.id))
            .where(ConversationMessage.session_id == session_id)
        )
        count = result.scalar() or 0
        return count > COMPACTION_THRESHOLD

    async def compact_history(self, user_id: str, session_id: str) -> Optional[str]:
        """Compact older messages into a summary."""
        # Get all messages ordered by time
        result = await self.db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.session_id == session_id)
            .order_by(ConversationMessage.created_at)
        )
        messages = list(result.scalars().all())

        if len(messages) <= COMPACTION_THRESHOLD:
            return None

        # Messages to compact (all except recent)
        to_compact = messages[:-RECENT_MESSAGES_KEEP]

        if not to_compact:
            return None

        # Build conversation text for summarization
        conversation_text = "\n".join([
            f"{msg.role}: {msg.content}" for msg in to_compact
        ])

        # Generate summary via LLM
        try:
            summary = await self._generate_summary(conversation_text)
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return None

        # Store compacted history
        existing = await self.db.execute(
            select(ConversationHistoryCompacted)
            .where(ConversationHistoryCompacted.user_id == user_id)
        )
        compacted = existing.scalar_one_or_none()

        if compacted:
            # Append to existing summary
            if compacted.compacted_history:
                compacted.compacted_history = f"{compacted.compacted_history}\n\n---\n\n{summary}"
            else:
                compacted.compacted_history = summary
        else:
            compacted = ConversationHistoryCompacted(
                user_id=user_id,
                compacted_history=summary,
            )
            self.db.add(compacted)

        # Delete compacted messages
        for msg in to_compact:
            await self.db.delete(msg)

        await self.db.flush()
        logger.info(f"Compacted {len(to_compact)} messages for user {user_id}")
        return summary

    async def _generate_summary(self, conversation_text: str) -> str:
        """Generate a summary of conversation text."""
        response = await self.llm_client.complete(
            system_prompt="""Eres un asistente que resume conversaciones.
Resume la siguiente conversación de manera concisa, capturando:
- Temas principales discutidos
- Acciones tomadas o solicitadas
- Cualquier información importante del usuario
Mantén el resumen bajo 150 palabras y en español.""",
            messages=[{"role": "user", "content": conversation_text}],
            max_tokens=SUMMARY_TOKEN_TARGET,
            temperature=0.3,
        )
        return response.text

    async def get_compacted_history(self, user_id: str) -> Optional[str]:
        """Get compacted history for a user."""
        result = await self.db.execute(
            select(ConversationHistoryCompacted)
            .where(ConversationHistoryCompacted.user_id == user_id)
        )
        compacted = result.scalar_one_or_none()
        return compacted.compacted_history if compacted else None
