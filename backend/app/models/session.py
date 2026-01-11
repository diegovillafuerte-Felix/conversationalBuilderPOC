"""Conversation session ORM model."""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Integer, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, GUID


class ConversationSession(Base):
    """Conversation session - tracks state across a conversation."""

    __tablename__ = "conversation_sessions"

    session_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Agent stack: array of AgentStackFrame objects
    # Each frame: {agentId, enteredAt, entryReason}
    agent_stack: Mapped[List[dict]] = mapped_column(JSON, nullable=False, default=list)

    # Current flow state: {flowId, currentState, stateData, enteredAt}
    current_flow: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Pending confirmation: {toolName, toolParams, displayMessage, expiresAt}
    pending_confirmation: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Status: active, completed, escalated, expired
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    last_interaction_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    message_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    messages: Mapped[List["ConversationMessage"]] = relationship(
        "ConversationMessage", back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ConversationSession {self.session_id} (user={self.user_id})>"

    def get_current_agent_id(self) -> Optional[str]:
        """Get the ID of the current agent from the stack."""
        if self.agent_stack:
            return self.agent_stack[-1].get("agentId")
        return None

    def push_agent(self, agent_id: str, reason: str) -> None:
        """Push a new agent onto the stack."""
        self.agent_stack = self.agent_stack + [
            {
                "agentId": agent_id,
                "enteredAt": datetime.utcnow().isoformat(),
                "entryReason": reason,
            }
        ]

    def pop_agent(self) -> Optional[dict]:
        """Pop the current agent from the stack."""
        if len(self.agent_stack) > 1:
            popped = self.agent_stack[-1]
            self.agent_stack = self.agent_stack[:-1]
            return popped
        return None


# Import at bottom to avoid circular imports
from app.models.conversation import ConversationMessage
