"""Subflow and State ORM models for statechart-based flows."""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Text, Boolean, ForeignKey, DateTime, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, GUID


class Subflow(Base):
    """Subflow definition - a statechart-based conversational flow."""

    __tablename__ = "subflows"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    trigger_description: Mapped[str] = mapped_column(Text, nullable=False)
    initial_state: Mapped[str] = mapped_column(String(100), nullable=False)

    # Data schema: field definitions for data collected during flow
    data_schema: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Timeout config: {durationMinutes, onTimeout, reminderMessage}
    timeout_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", back_populates="subflows")
    states: Mapped[List["SubflowState"]] = relationship(
        "SubflowState", back_populates="subflow", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Subflow {self.name} ({self.id})>"


class SubflowState(Base):
    """State definition within a subflow."""

    __tablename__ = "subflow_states"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    subflow_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("subflows.id", ondelete="CASCADE"), nullable=False
    )
    state_id: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    agent_instructions: Mapped[str] = mapped_column(Text, nullable=False)

    # State-specific tools: array of inline tool definitions
    state_tools: Mapped[Optional[List[dict]]] = mapped_column(JSON, nullable=True)

    # Transitions: array of TransitionDefinition objects
    transitions: Mapped[Optional[List[dict]]] = mapped_column(JSON, nullable=True)

    is_final: Mapped[bool] = mapped_column(Boolean, default=False)

    # On enter actions: {fetchContext, sendMessage}
    on_enter: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Full JSON config for runtime language switching
    config_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    subflow: Mapped["Subflow"] = relationship("Subflow", back_populates="states")

    __table_args__ = (
        UniqueConstraint("subflow_id", "state_id", name="uq_subflow_state"),
    )

    def __repr__(self) -> str:
        return f"<SubflowState {self.name} ({self.state_id})>"


# Import Agent here to avoid circular imports
from app.models.agent import Agent
