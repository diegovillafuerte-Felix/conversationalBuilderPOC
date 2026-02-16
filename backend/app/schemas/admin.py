"""Pydantic schemas for admin API requests and responses."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# ============================================================================
# Agent Schemas
# ============================================================================


class AgentCreate(BaseModel):
    """Request to create an agent."""

    name: str = Field(..., min_length=1, max_length=100, description="Agent name")
    description: str = Field(..., min_length=1, description="Agent description")
    parent_agent_id: UUID | None = Field(None, description="Parent agent ID for hierarchy")
    system_prompt_addition: str | None = Field(None, description="Additional system prompt text")
    model_config_json: dict = Field(default_factory=dict, description="Model configuration")
    navigation_tools: dict = Field(default_factory=dict, description="Navigation tool settings")


class AgentUpdate(BaseModel):
    """Request to update an agent."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, min_length=1)
    parent_agent_id: UUID | None = None
    system_prompt_addition: str | None = None
    model_config_json: dict | None = None
    navigation_tools: dict | None = None
    is_active: bool | None = None


class AgentListItem(BaseModel):
    """Lightweight agent representation for tree views."""

    id: UUID
    name: str
    parent_agent_id: UUID | None
    description: str
    is_active: bool


class ToolResponse(BaseModel):
    """Tool details in responses."""

    id: UUID
    agent_id: UUID
    name: str
    description: str
    parameters: list[dict] | None = None
    api_config: dict | None = None
    response_config: dict | None = None
    requires_confirmation: bool
    confirmation_template: str | None = None
    side_effects: str
    flow_transition: dict | None = None
    created_at: datetime


class SubflowStateResponse(BaseModel):
    """Subflow state details in responses."""

    id: UUID
    subflow_id: UUID
    state_id: str
    name: str
    agent_instructions: str
    state_tools: list[dict] | None = None
    transitions: list[dict] | None = None
    is_final: bool
    on_enter: dict | None = None


class SubflowResponse(BaseModel):
    """Subflow details in responses."""

    id: UUID
    agent_id: UUID
    name: str
    trigger_description: str
    initial_state: str
    data_schema: dict | None = None
    timeout_config: dict | None = None
    created_at: datetime
    states: list[SubflowStateResponse] = Field(default_factory=list)


class ResponseTemplateResponse(BaseModel):
    """Response template details in responses."""

    id: UUID
    agent_id: UUID
    name: str
    trigger_config: dict
    template: str
    required_fields: list[str] | None = None
    enforcement: str


class AgentResponse(BaseModel):
    """Full agent details with relationships."""

    id: UUID
    name: str
    parent_agent_id: UUID | None
    description: str
    system_prompt_addition: str | None
    model_config_json: dict
    navigation_tools: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime
    children: list[AgentListItem] = Field(default_factory=list)
    tools: list[ToolResponse] = Field(default_factory=list)
    subflows: list[SubflowResponse] = Field(default_factory=list)
    response_templates: list[ResponseTemplateResponse] = Field(default_factory=list)


# ============================================================================
# Tool Schemas
# ============================================================================


class ToolCreate(BaseModel):
    """Request to create a tool."""

    name: str = Field(..., min_length=1, max_length=100, description="Tool name")
    description: str = Field(..., min_length=1, description="Tool description")
    parameters: list[dict] | None = Field(None, description="Parameter definitions")
    api_config: dict | None = Field(None, description="API configuration")
    response_config: dict | None = Field(None, description="Response configuration")
    requires_confirmation: bool = Field(False, description="Whether tool requires confirmation")
    confirmation_template: str | None = Field(None, description="Confirmation message template")
    side_effects: str = Field("none", description="Side effect type: none, read, write, financial")
    flow_transition: dict | None = Field(None, description="Flow transition configuration")


class ToolUpdate(BaseModel):
    """Request to update a tool."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, min_length=1)
    parameters: list[dict] | None = None
    api_config: dict | None = None
    response_config: dict | None = None
    requires_confirmation: bool | None = None
    confirmation_template: str | None = None
    side_effects: str | None = None
    flow_transition: dict | None = None


# ============================================================================
# Subflow Schemas
# ============================================================================


class SubflowCreate(BaseModel):
    """Request to create a subflow."""

    name: str = Field(..., min_length=1, max_length=100, description="Subflow name")
    trigger_description: str = Field(..., min_length=1, description="When to trigger this flow")
    initial_state: str = Field(..., min_length=1, description="Initial state ID")
    data_schema: dict | None = Field(None, description="Data schema for flow")
    timeout_config: dict | None = Field(None, description="Timeout configuration")


class SubflowUpdate(BaseModel):
    """Request to update a subflow."""

    name: str | None = Field(None, min_length=1, max_length=100)
    trigger_description: str | None = Field(None, min_length=1)
    initial_state: str | None = Field(None, min_length=1)
    data_schema: dict | None = None
    timeout_config: dict | None = None


# ============================================================================
# SubflowState Schemas
# ============================================================================


class StateCreate(BaseModel):
    """Request to create a subflow state."""

    state_id: str = Field(..., min_length=1, max_length=100, description="Unique state identifier")
    name: str = Field(..., min_length=1, max_length=100, description="State display name")
    agent_instructions: str = Field(..., min_length=1, description="Instructions for agent in this state")
    state_tools: list[dict] | None = Field(None, description="State-specific tools")
    transitions: list[dict] | None = Field(None, description="State transitions")
    is_final: bool = Field(False, description="Whether this is a final state")
    on_enter: dict | None = Field(None, description="Actions on entering state")


class StateUpdate(BaseModel):
    """Request to update a subflow state."""

    state_id: str | None = Field(None, min_length=1, max_length=100)
    name: str | None = Field(None, min_length=1, max_length=100)
    agent_instructions: str | None = Field(None, min_length=1)
    state_tools: list[dict] | None = None
    transitions: list[dict] | None = None
    is_final: bool | None = None
    on_enter: dict | None = None


# ============================================================================
# ResponseTemplate Schemas
# ============================================================================


class TemplateCreate(BaseModel):
    """Request to create a response template."""

    name: str = Field(..., min_length=1, max_length=100, description="Template name")
    trigger_config: dict = Field(..., description="Trigger configuration")
    template: str = Field(..., min_length=1, description="Template text")
    required_fields: list[str] | None = Field(None, description="Required fields in template")
    enforcement: str = Field("suggested", description="Enforcement level: mandatory or suggested")


class TemplateUpdate(BaseModel):
    """Request to update a response template."""

    name: str | None = Field(None, min_length=1, max_length=100)
    trigger_config: dict | None = None
    template: str | None = Field(None, min_length=1)
    required_fields: list[str] | None = None
    enforcement: str | None = None
