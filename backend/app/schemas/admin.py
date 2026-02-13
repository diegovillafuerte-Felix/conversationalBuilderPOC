"""Pydantic schemas for admin API requests and responses."""

from datetime import datetime
from typing import Optional, List, Any
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Agent Schemas
# ============================================================================

class AgentCreate(BaseModel):
    """Request to create an agent."""

    name: str = Field(..., min_length=1, max_length=100, description="Agent name")
    description: str = Field(..., min_length=1, description="Agent description")
    parent_agent_id: Optional[UUID] = Field(None, description="Parent agent ID for hierarchy")
    system_prompt_addition: Optional[str] = Field(None, description="Additional system prompt text")
    model_config_json: dict = Field(default_factory=dict, description="Model configuration")
    navigation_tools: dict = Field(default_factory=dict, description="Navigation tool settings")


class AgentUpdate(BaseModel):
    """Request to update an agent."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=1)
    parent_agent_id: Optional[UUID] = None
    system_prompt_addition: Optional[str] = None
    model_config_json: Optional[dict] = None
    navigation_tools: Optional[dict] = None
    is_active: Optional[bool] = None


class AgentListItem(BaseModel):
    """Lightweight agent representation for tree views."""

    id: UUID
    name: str
    parent_agent_id: Optional[UUID]
    description: str
    is_active: bool


class ToolResponse(BaseModel):
    """Tool details in responses."""

    id: UUID
    agent_id: UUID
    name: str
    description: str
    parameters: Optional[List[dict]] = None
    api_config: Optional[dict] = None
    response_config: Optional[dict] = None
    requires_confirmation: bool
    confirmation_template: Optional[str] = None
    side_effects: str
    flow_transition: Optional[dict] = None
    created_at: datetime


class SubflowStateResponse(BaseModel):
    """Subflow state details in responses."""

    id: UUID
    subflow_id: UUID
    state_id: str
    name: str
    agent_instructions: str
    state_tools: Optional[List[dict]] = None
    transitions: Optional[List[dict]] = None
    is_final: bool
    on_enter: Optional[dict] = None


class SubflowResponse(BaseModel):
    """Subflow details in responses."""

    id: UUID
    agent_id: UUID
    name: str
    trigger_description: str
    initial_state: str
    data_schema: Optional[dict] = None
    timeout_config: Optional[dict] = None
    created_at: datetime
    states: List[SubflowStateResponse] = Field(default_factory=list)


class ResponseTemplateResponse(BaseModel):
    """Response template details in responses."""

    id: UUID
    agent_id: UUID
    name: str
    trigger_config: dict
    template: str
    required_fields: Optional[List[str]] = None
    enforcement: str


class AgentResponse(BaseModel):
    """Full agent details with relationships."""

    id: UUID
    name: str
    parent_agent_id: Optional[UUID]
    description: str
    system_prompt_addition: Optional[str]
    model_config_json: dict
    navigation_tools: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime
    children: List[AgentListItem] = Field(default_factory=list)
    tools: List[ToolResponse] = Field(default_factory=list)
    subflows: List[SubflowResponse] = Field(default_factory=list)
    response_templates: List[ResponseTemplateResponse] = Field(default_factory=list)


# ============================================================================
# Tool Schemas
# ============================================================================

class ToolCreate(BaseModel):
    """Request to create a tool."""

    name: str = Field(..., min_length=1, max_length=100, description="Tool name")
    description: str = Field(..., min_length=1, description="Tool description")
    parameters: Optional[List[dict]] = Field(None, description="Parameter definitions")
    api_config: Optional[dict] = Field(None, description="API configuration")
    response_config: Optional[dict] = Field(None, description="Response configuration")
    requires_confirmation: bool = Field(False, description="Whether tool requires confirmation")
    confirmation_template: Optional[str] = Field(None, description="Confirmation message template")
    side_effects: str = Field("none", description="Side effect type: none, read, write, financial")
    flow_transition: Optional[dict] = Field(None, description="Flow transition configuration")


class ToolUpdate(BaseModel):
    """Request to update a tool."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=1)
    parameters: Optional[List[dict]] = None
    api_config: Optional[dict] = None
    response_config: Optional[dict] = None
    requires_confirmation: Optional[bool] = None
    confirmation_template: Optional[str] = None
    side_effects: Optional[str] = None
    flow_transition: Optional[dict] = None


# ============================================================================
# Subflow Schemas
# ============================================================================

class SubflowCreate(BaseModel):
    """Request to create a subflow."""

    name: str = Field(..., min_length=1, max_length=100, description="Subflow name")
    trigger_description: str = Field(..., min_length=1, description="When to trigger this flow")
    initial_state: str = Field(..., min_length=1, description="Initial state ID")
    data_schema: Optional[dict] = Field(None, description="Data schema for flow")
    timeout_config: Optional[dict] = Field(None, description="Timeout configuration")


class SubflowUpdate(BaseModel):
    """Request to update a subflow."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    trigger_description: Optional[str] = Field(None, min_length=1)
    initial_state: Optional[str] = Field(None, min_length=1)
    data_schema: Optional[dict] = None
    timeout_config: Optional[dict] = None


# ============================================================================
# SubflowState Schemas
# ============================================================================

class StateCreate(BaseModel):
    """Request to create a subflow state."""

    state_id: str = Field(..., min_length=1, max_length=100, description="Unique state identifier")
    name: str = Field(..., min_length=1, max_length=100, description="State display name")
    agent_instructions: str = Field(..., min_length=1, description="Instructions for agent in this state")
    state_tools: Optional[List[dict]] = Field(None, description="State-specific tools")
    transitions: Optional[List[dict]] = Field(None, description="State transitions")
    is_final: bool = Field(False, description="Whether this is a final state")
    on_enter: Optional[dict] = Field(None, description="Actions on entering state")


class StateUpdate(BaseModel):
    """Request to update a subflow state."""

    state_id: Optional[str] = Field(None, min_length=1, max_length=100)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    agent_instructions: Optional[str] = Field(None, min_length=1)
    state_tools: Optional[List[dict]] = None
    transitions: Optional[List[dict]] = None
    is_final: Optional[bool] = None
    on_enter: Optional[dict] = None


# ============================================================================
# ResponseTemplate Schemas
# ============================================================================

class TemplateCreate(BaseModel):
    """Request to create a response template."""

    name: str = Field(..., min_length=1, max_length=100, description="Template name")
    trigger_config: dict = Field(..., description="Trigger configuration")
    template: str = Field(..., min_length=1, description="Template text")
    required_fields: Optional[List[str]] = Field(None, description="Required fields in template")
    enforcement: str = Field("suggested", description="Enforcement level: mandatory or suggested")


class TemplateUpdate(BaseModel):
    """Request to update a response template."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    trigger_config: Optional[dict] = None
    template: Optional[str] = Field(None, min_length=1)
    required_fields: Optional[List[str]] = None
    enforcement: Optional[str] = None
