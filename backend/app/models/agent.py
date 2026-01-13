"""Agent and Tool ORM models."""

import uuid
from datetime import datetime
from typing import Optional, List, Any

from sqlalchemy import String, Text, Boolean, ForeignKey, DateTime, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, GUID


class Agent(Base):
    """Agent definition - represents an AI agent in the hierarchy."""

    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    config_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey("agents.id"), nullable=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    system_prompt_addition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Model configuration: {model, temperature, maxTokens}
    model_config_json: Mapped[dict] = mapped_column(
        "model_config", JSON, nullable=False, default=dict
    )

    # Navigation tools: {canGoUp, canGoHome, canEscalate}
    navigation_tools: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Context requirements: array of ContextRequirement objects
    context_requirements: Mapped[Optional[List[dict]]] = mapped_column(
        JSON, nullable=True
    )

    # Full JSON config for runtime language switching and admin UI editing
    config_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    parent: Mapped[Optional["Agent"]] = relationship(
        "Agent", remote_side=[id], back_populates="children"
    )
    children: Mapped[List["Agent"]] = relationship(
        "Agent", back_populates="parent", cascade="all, delete-orphan"
    )
    tools: Mapped[List["Tool"]] = relationship(
        "Tool", back_populates="agent", cascade="all, delete-orphan"
    )
    subflows: Mapped[List["Subflow"]] = relationship(
        "Subflow", back_populates="agent", cascade="all, delete-orphan"
    )
    response_templates: Mapped[List["ResponseTemplate"]] = relationship(
        "ResponseTemplate", back_populates="agent", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Agent {self.name} ({self.id})>"


class Tool(Base):
    """Tool definition - a function the agent can call."""

    __tablename__ = "tools"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Parameters: array of ParameterDefinition objects
    parameters: Mapped[Optional[List[dict]]] = mapped_column(JSON, nullable=True)

    # API configuration: {endpoint, method, headers, bodyTemplate}
    api_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Response configuration: {successPath, dataMapping, errorMessages}
    response_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    requires_confirmation: Mapped[bool] = mapped_column(Boolean, default=False)
    confirmation_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Side effects: none, read, write, financial
    side_effects: Mapped[str] = mapped_column(String(20), default="none")

    # Flow transition: {onSuccess, onError}
    flow_transition: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Routing configuration: {type, target} for navigation/flow tools
    routing: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Full JSON config for runtime language switching and admin UI editing
    config_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", back_populates="tools")

    def __repr__(self) -> str:
        return f"<Tool {self.name} ({self.id})>"

    def to_openai_tool(self) -> dict:
        """Convert to OpenAI API tool format."""
        properties = {}
        required = []

        if self.parameters:
            for param in self.parameters:
                prop = {"type": param.get("type", "string")}
                if "description" in param:
                    prop["description"] = param["description"]
                if "enum" in param.get("validation", {}):
                    prop["enum"] = param["validation"]["enum"]
                properties[param["name"]] = prop
                if param.get("required", False):
                    required.append(param["name"])

        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }


class ResponseTemplate(Base):
    """Response template for consistent messaging."""

    __tablename__ = "response_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Trigger config: {type, toolName, stateName, errorCode}
    trigger_config: Mapped[dict] = mapped_column(JSON, nullable=False)

    template: Mapped[str] = mapped_column(Text, nullable=False)
    required_fields: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)

    # Enforcement: mandatory or suggested
    enforcement: Mapped[str] = mapped_column(String(20), default="suggested")

    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", back_populates="response_templates")

    def __repr__(self) -> str:
        return f"<ResponseTemplate {self.name} ({self.id})>"


# Import Subflow here to avoid circular imports
from app.models.subflow import Subflow
