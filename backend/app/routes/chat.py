"""Chat API routes."""

import logging
import uuid as uuid_module
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from openai import OpenAIError

from app.database import get_db
from app.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    SessionCreateRequest,
    SessionResponse,
    SessionEndRequest,
    ToolCallInfo,
    UserListItem,
    UserContextResponse,
    DebugInfo,
    DebugLLMCall,
    TraceEventInfo,
    ConversationListItem,
    ConversationDetailResponse,
    ConversationMessageItem,
    ConversationEventsResponse,
)
from app.core.orchestrator import Orchestrator
from app.core.agent_registry import get_agent_registry
from app.models.session import ConversationSession
from app.models.conversation import ConversationMessage
from app.models.user import UserContext

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/message", response_model=ChatMessageResponse)
async def send_message(
    request: ChatMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Send a message and get a response.

    If session_id is not provided, a new session will be created.
    """
    try:
        orchestrator = Orchestrator(db)
        response = await orchestrator.handle_message(
            user_message=request.message,
            user_id=request.user_id,
            session_id=request.session_id,
        )

        # Convert debug info if present
        debug_info = None
        if response.debug:
            debug_info = DebugInfo(
                llm_call=DebugLLMCall(
                    system_prompt=response.debug.llm_call.system_prompt,
                    messages=response.debug.llm_call.messages,
                    tools_provided=response.debug.llm_call.tools_provided,
                    model=response.debug.llm_call.model,
                    temperature=response.debug.llm_call.temperature,
                    raw_response=response.debug.llm_call.raw_response,
                    token_counts=response.debug.llm_call.token_counts,
                ) if response.debug.llm_call else None,
                agent_stack=response.debug.agent_stack,
                flow_info=response.debug.flow_info,
                context_sections=response.debug.context_sections,
                processing_time_ms=response.debug.processing_time_ms,
                routing_path=response.debug.routing_path,
                chain_iterations=response.debug.chain_iterations,
                stable_state_reached=response.debug.stable_state_reached,
                event_trace=[
                    TraceEventInfo(
                        id=e["id"],
                        category=e["category"],
                        event_type=e["event_type"],
                        message=e["message"],
                        timestamp=e["timestamp"],
                        level=e["level"],
                        data=e.get("data", {}),
                        duration_ms=e.get("duration_ms"),
                        parent_id=e.get("parent_id"),
                        turn_id=e.get("turn_id"),
                        user_message=e.get("user_message"),
                        assistant_response=e.get("assistant_response"),
                    )
                    for e in response.debug.event_trace
                ],
            )

        return ChatMessageResponse(
            session_id=response.session_id,
            message=response.message,
            agent_id=response.agent_id,
            agent_name=response.agent_name,
            tool_calls=[
                ToolCallInfo(
                    tool_name=tc["name"],
                    parameters=tc["params"],
                    result=tc.get("result"),
                )
                for tc in response.tool_calls
            ],
            pending_confirmation=response.pending_confirmation,
            flow_state=response.flow_state,
            escalated=response.escalated,
            debug=debug_info,
        )

    except OpenAIError as e:
        logger.error(f"LLM error after retries: {e}")
        return ChatMessageResponse(
            session_id=request.session_id or uuid_module.uuid4(),
            message="Lo siento, estoy teniendo problemas técnicos en este momento. Por favor intenta de nuevo en unos minutos.",
            agent_id="system",
            agent_name="Felix Assistant",
            tool_calls=[],
            pending_confirmation=None,
            escalated=False,
            timestamp=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Error handling message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session", response_model=SessionResponse)
async def create_session(
    request: SessionCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new chat session."""
    # Get root agent from registry
    registry = get_agent_registry()
    root_agent = registry.get_root_agent()

    if not root_agent:
        raise HTTPException(status_code=500, detail="No root agent configured")

    # Create session
    session = ConversationSession(
        user_id=request.user_id,
        agent_stack=[
            {
                "agentId": root_agent.config_id,
                "enteredAt": "now",
                "entryReason": "Session created",
            }
        ],
        status="active",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    return SessionResponse(
        session_id=session.session_id,
        user_id=session.user_id,
        status=session.status,
        current_agent_id=root_agent.config_id,
        current_agent_name=root_agent.name,
        message_count=session.message_count,
        created_at=session.created_at,
        last_interaction_at=session.last_interaction_at,
    )


@router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get session information."""
    result = await db.execute(
        select(ConversationSession).where(
            ConversationSession.session_id == session_id
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get current agent from registry
    current_agent_id = session.get_current_agent_id()
    current_agent = None
    if current_agent_id:
        registry = get_agent_registry()
        current_agent = registry.get_agent(current_agent_id)

    return SessionResponse(
        session_id=session.session_id,
        user_id=session.user_id,
        status=session.status,
        current_agent_id=current_agent_id,
        current_agent_name=current_agent.name if current_agent else None,
        current_flow=session.current_flow.get("currentState") if session.current_flow else None,
        message_count=session.message_count,
        created_at=session.created_at,
        last_interaction_at=session.last_interaction_at,
    )


@router.post("/session/{session_id}/end", response_model=SessionResponse)
async def end_session(
    session_id: UUID,
    request: Optional[SessionEndRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    """End a chat session."""
    result = await db.execute(
        select(ConversationSession).where(
            ConversationSession.session_id == session_id
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.status = "completed"
    session.current_flow = None
    session.pending_confirmation = None
    await db.commit()
    await db.refresh(session)

    return SessionResponse(
        session_id=session.session_id,
        user_id=session.user_id,
        status=session.status,
        current_agent_id=session.get_current_agent_id(),
        current_agent_name=None,
        message_count=session.message_count,
        created_at=session.created_at,
        last_interaction_at=session.last_interaction_at,
    )


@router.get("/users", response_model=List[UserListItem])
async def list_test_users(db: AsyncSession = Depends(get_db)):
    """List available test users."""
    result = await db.execute(select(UserContext))
    users = result.scalars().all()

    return [
        UserListItem(
            user_id=u.user_id,
            name=u.profile.get("name", "Unknown") if u.profile else "Unknown",
            preferred_name=u.get_preferred_name(),
        )
        for u in users
    ]


@router.get("/users/{user_id}/context", response_model=UserContextResponse)
async def get_user_context(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get user context for display."""
    result = await db.execute(
        select(UserContext).where(UserContext.user_id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserContextResponse(
        user_id=user.user_id,
        profile=user.profile or {},
        product_summaries=user.product_summaries,
        behavioral_summary=user.behavioral_summary,
    )


@router.get("/conversations", response_model=List[ConversationListItem])
async def list_conversations(
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Browse conversation sessions with optional text search."""
    query = select(ConversationSession)

    if user_id:
        query = query.where(ConversationSession.user_id == user_id)
    if status:
        query = query.where(ConversationSession.status == status)

    if q:
        search_value = f"%{q.lower()}%"
        session_ids_result = await db.execute(
            select(ConversationMessage.session_id)
            .where(func.lower(ConversationMessage.content).like(search_value))
            .distinct()
        )
        matching_ids = [row[0] for row in session_ids_result.all()]
        if not matching_ids:
            return []
        query = query.where(ConversationSession.session_id.in_(matching_ids))

    query = query.order_by(ConversationSession.last_interaction_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    sessions = result.scalars().all()

    items: List[ConversationListItem] = []
    for session in sessions:
        last_message_result = await db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.session_id == session.session_id)
            .order_by(ConversationMessage.created_at.desc())
            .limit(1)
        )
        last_message = last_message_result.scalar_one_or_none()
        preview = last_message.content[:200] if last_message else None
        items.append(
            ConversationListItem(
                session_id=session.session_id,
                user_id=session.user_id,
                status=session.status,
                message_count=session.message_count,
                current_agent_id=session.get_current_agent_id(),
                current_flow=session.current_flow.get("currentState") if session.current_flow else None,
                created_at=session.created_at,
                last_interaction_at=session.last_interaction_at,
                last_message_preview=preview,
            )
        )

    return items


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation_detail(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get full conversation detail including message history."""
    session_result = await db.execute(
        select(ConversationSession).where(ConversationSession.session_id == conversation_id)
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages_result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.session_id == conversation_id)
        .order_by(ConversationMessage.created_at.asc())
    )
    messages = messages_result.scalars().all()

    return ConversationDetailResponse(
        session_id=session.session_id,
        user_id=session.user_id,
        status=session.status,
        current_agent_id=session.get_current_agent_id(),
        current_flow=session.current_flow.get("currentState") if session.current_flow else None,
        message_count=session.message_count,
        created_at=session.created_at,
        last_interaction_at=session.last_interaction_at,
        messages=[
            ConversationMessageItem(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at,
                metadata=msg.msg_metadata or {},
            )
            for msg in messages
        ],
    )


@router.get("/conversations/{conversation_id}/events", response_model=ConversationEventsResponse)
async def get_conversation_events(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get flattened event traces captured during the conversation."""
    session_result = await db.execute(
        select(ConversationSession).where(ConversationSession.session_id == conversation_id)
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages_result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.session_id == conversation_id)
        .where(ConversationMessage.role == "assistant")
        .order_by(ConversationMessage.created_at.asc())
    )
    assistant_messages = messages_result.scalars().all()

    events: List[TraceEventInfo] = []
    for message in assistant_messages:
        trace_events = (message.msg_metadata or {}).get("eventTrace", [])
        for event in trace_events:
            if not isinstance(event, dict):
                continue
            events.append(
                TraceEventInfo(
                    id=event.get("id", ""),
                    category=event.get("category", "unknown"),
                    event_type=event.get("event_type", "unknown"),
                    message=event.get("message", ""),
                    timestamp=event.get("timestamp", message.created_at.isoformat()),
                    level=event.get("level", "info"),
                    data=event.get("data", {}),
                    duration_ms=event.get("duration_ms"),
                    parent_id=event.get("parent_id"),
                    turn_id=event.get("turn_id"),
                    user_message=event.get("user_message"),
                    assistant_response=event.get("assistant_response"),
                )
            )

    return ConversationEventsResponse(session_id=session.session_id, events=events)
