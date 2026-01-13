"""Pydantic schemas for chat API requests and responses."""

from datetime import datetime
from typing import Optional, List, Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ShadowMessageInfo(BaseModel):
    """A message injected by a shadow subagent (financial advisor, campaigns, etc.)."""

    content: str = Field(..., description="The shadow message content")
    source: str = Field(..., description="Source label (e.g., 'Felix Financial Advisor')")
    subagent_id: str = Field(..., description="ID of the shadow subagent (e.g., 'financial_advisor')")
    message_type: Literal["tip", "promotion", "alert"] = Field(
        default="tip", description="Type of shadow message"
    )


class ChatMessageRequest(BaseModel):
    """Request to send a chat message."""

    session_id: Optional[UUID] = Field(
        None, description="Existing session ID. If not provided, creates new session."
    )
    user_id: str = Field(..., description="User identifier")
    message: str = Field(..., min_length=1, description="User's message content")


class ToolCallInfo(BaseModel):
    """Information about a tool call made during response generation."""

    tool_name: str
    parameters: dict[str, Any]
    result: Optional[Any] = None
    requires_confirmation: bool = False
    confirmation_message: Optional[str] = None


class DebugLLMCall(BaseModel):
    """Debug information about an LLM call."""

    system_prompt: str = Field(..., description="Full system prompt sent to LLM")
    messages: List[dict] = Field(..., description="Messages array sent to LLM")
    tools_provided: List[str] = Field(default_factory=list, description="Tool names provided to LLM")
    model: str = Field(..., description="Model used")
    temperature: float = Field(..., description="Temperature setting")
    raw_response: Optional[str] = Field(None, description="Raw text response from LLM")
    token_counts: Optional[dict] = Field(None, description="Token usage breakdown")


class DebugInfo(BaseModel):
    """Debug information for developer view."""

    llm_call: Optional[DebugLLMCall] = Field(None, description="LLM call details")
    agent_stack: List[dict] = Field(default_factory=list, description="Current agent navigation stack")
    flow_info: Optional[dict] = Field(None, description="Current flow state details")
    context_sections: Optional[dict] = Field(None, description="Context assembly breakdown")
    processing_time_ms: Optional[int] = Field(None, description="Total processing time")
    enrichment_info: Optional[dict] = Field(None, description="Context enrichment state and errors")
    routing_path: List[dict] = Field(default_factory=list, description="Routing events during conversation")
    chain_iterations: int = Field(default=0, description="Number of routing chain iterations")
    stable_state_reached: bool = Field(default=False, description="Whether chain reached stable state")


class ChatMessageResponse(BaseModel):
    """Response from the chat endpoint."""

    session_id: UUID
    message: str = Field(..., description="Assistant's response message")
    agent_id: str = Field(..., description="ID of the agent that responded")
    agent_name: str = Field(..., description="Name of the responding agent")

    # Optional metadata
    tool_calls: List[ToolCallInfo] = Field(
        default_factory=list, description="Tools called during response"
    )
    pending_confirmation: Optional[dict] = Field(
        None, description="Confirmation awaiting user response"
    )
    flow_state: Optional[str] = Field(None, description="Current subflow state if in a flow")
    escalated: bool = Field(False, description="Whether conversation was escalated")

    # Shadow service messages (tips, promotions, alerts)
    shadow_messages: List[ShadowMessageInfo] = Field(
        default_factory=list,
        description="Messages from shadow subagents (financial advisor, campaigns, etc.)"
    )

    # Debug information (optional, for developer view)
    debug: Optional[DebugInfo] = Field(None, description="Debug information for developer view")

    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SessionCreateRequest(BaseModel):
    """Request to create a new chat session."""

    user_id: str = Field(..., description="User identifier")


class SessionResponse(BaseModel):
    """Response with session information."""

    session_id: UUID
    user_id: str
    status: str
    current_agent_id: Optional[str] = None
    current_agent_name: Optional[str] = None
    current_flow: Optional[str] = None
    message_count: int
    created_at: datetime
    last_interaction_at: datetime


class SessionEndRequest(BaseModel):
    """Request to end a session."""

    reason: Optional[str] = Field(None, description="Reason for ending session")


class MessageHistoryItem(BaseModel):
    """A single message in the conversation history."""

    role: str
    content: str
    timestamp: datetime
    agent_id: Optional[str] = None
    tool_calls: Optional[List[ToolCallInfo]] = None


class ConversationHistoryResponse(BaseModel):
    """Response with conversation history."""

    session_id: UUID
    messages: List[MessageHistoryItem]
    total_messages: int


class UserListItem(BaseModel):
    """User item for the user list."""

    user_id: str
    name: str
    preferred_name: str


class UserContextResponse(BaseModel):
    """User context for display."""

    user_id: str
    profile: dict
    product_summaries: Optional[dict] = None
    behavioral_summary: Optional[str] = None
