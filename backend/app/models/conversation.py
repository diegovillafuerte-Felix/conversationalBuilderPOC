"""Conversation history ORM models."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, GUID


class ConversationMessage(Base):
    """Individual message in a conversation."""

    __tablename__ = "conversation_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("conversation_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Role: user, assistant, system
    role: Mapped[str] = mapped_column(String(20), nullable=False)

    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Metadata for assistant messages: {agentId, flowState, toolsCalled, modelUsed}
    msg_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    session: Mapped["ConversationSession"] = relationship(
        "ConversationSession", back_populates="messages"
    )

    def __repr__(self) -> str:
        return f"<ConversationMessage {self.role} ({self.id})>"

    def to_dict(self) -> dict:
        """Convert to dictionary for context assembly."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.created_at.isoformat(),
            "metadata": self.msg_metadata,
        }


class ConversationHistoryCompacted(Base):
    """Compacted/summarized conversation history for long-term context."""

    __tablename__ = "conversation_history_compacted"

    user_id: Mapped[str] = mapped_column(String(100), primary_key=True)

    # Summarized older interactions
    compacted_history: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    last_compacted_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<ConversationHistoryCompacted {self.user_id}>"


# Import at bottom to avoid circular imports
from app.models.session import ConversationSession
