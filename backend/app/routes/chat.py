"""Chat API routes."""

import logging
import uuid as uuid_module
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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
    ShadowMessageInfo,
)
from app.core.orchestrator import Orchestrator
from app.models.session import ConversationSession
from app.models.agent import Agent
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
                enrichment_info=response.debug.enrichment_info,
                routing_path=response.debug.routing_path,
                chain_iterations=response.debug.chain_iterations,
                stable_state_reached=response.debug.stable_state_reached,
            )

        # Map shadow messages to schema
        shadow_messages = [
            ShadowMessageInfo(
                content=sm.content,
                source=sm.source,
                subagent_id=sm.subagent_id,
                message_type=sm.message_type,
            )
            for sm in response.shadow_messages
        ]

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
            shadow_messages=shadow_messages,
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
    # Get root agent
    result = await db.execute(
        select(Agent)
        .where(Agent.parent_agent_id.is_(None))
        .where(Agent.is_active.is_(True))
    )
    root_agent = result.scalar_one_or_none()

    if not root_agent:
        raise HTTPException(status_code=500, detail="No root agent configured")

    # Create session
    session = ConversationSession(
        user_id=request.user_id,
        agent_stack=[
            {
                "agentId": str(root_agent.id),
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
        current_agent_id=str(root_agent.id),
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

    # Get current agent
    current_agent_id = session.get_current_agent_id()
    current_agent = None
    if current_agent_id:
        result = await db.execute(
            select(Agent).where(Agent.id == UUID(current_agent_id))
        )
        current_agent = result.scalar_one_or_none()

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
