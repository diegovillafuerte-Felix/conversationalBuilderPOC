"""Global test fixtures for the test suite."""

import sys
from pathlib import Path

# Add the app directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import pytest_asyncio
from typing import AsyncGenerator, List, Any
from unittest.mock import patch
from uuid import uuid4
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient, ASGITransport

from app.database import Base
from app.core.llm_client import LLMResponse, ToolCall


# ============= Mock LLM Client =============

@dataclass
class MockLLMClient:
    """Mock LLM client for testing without actual API calls."""

    responses: List[LLMResponse] = field(default_factory=list)
    calls: List[dict] = field(default_factory=list)
    default_response: LLMResponse = field(default_factory=lambda: LLMResponse(
        text="This is a mock response.",
        tool_calls=[],
        stop_reason="stop",
        model="mock-model",
    ))

    def add_response(self, response: LLMResponse):
        """Add a response to the queue."""
        self.responses.append(response)

    def add_text_response(self, text: str):
        """Add a simple text response."""
        self.responses.append(LLMResponse(
            text=text,
            tool_calls=[],
            stop_reason="stop",
            model="mock-model",
        ))

    def add_tool_call_response(self, tool_name: str, params: dict, text: str = ""):
        """Add a response with a tool call."""
        self.responses.append(LLMResponse(
            text=text,
            tool_calls=[ToolCall(id=f"call_{uuid4().hex[:8]}", name=tool_name, parameters=params)],
            stop_reason="tool_calls",
            model="mock-model",
        ))

    async def complete(
        self,
        system_prompt: str,
        messages: list,
        tools: list = None,
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
    ) -> LLMResponse:
        """Mock complete method."""
        self.calls.append({
            "system_prompt": system_prompt,
            "messages": messages,
            "tools": tools,
            "model": model,
        })
        if self.responses:
            return self.responses.pop(0)
        return self.default_response

    async def complete_with_tool_results(
        self,
        system_prompt: str,
        messages: list,
        tools: list,
        tool_results: list,
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
    ) -> LLMResponse:
        """Mock complete_with_tool_results method."""
        self.calls.append({
            "system_prompt": system_prompt,
            "messages": messages,
            "tools": tools,
            "tool_results": tool_results,
            "model": model,
        })
        if self.responses:
            return self.responses.pop(0)
        return self.default_response


# ============= Database Fixtures =============

@pytest_asyncio.fixture
async def async_engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a database session for testing."""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session_maker() as session:
        yield session
        await session.rollback()


# ============= Mock LLM Fixtures =============

@pytest.fixture
def mock_llm_client() -> MockLLMClient:
    """Create a mock LLM client."""
    return MockLLMClient()


@pytest_asyncio.fixture
async def patched_llm_client(mock_llm_client):
    """Patch the LLM client globally."""
    with patch("app.core.llm_client.get_llm_client", return_value=mock_llm_client):
        yield mock_llm_client


# ============= Sample Data Fixtures =============

@pytest.fixture
def initialized_registry():
    """Initialize the agent registry with real configs for testing."""
    from app.core.agent_registry import initialize_agent_registry, reset_agent_registry, get_agent_registry

    # Reset to ensure clean state
    reset_agent_registry()
    # Initialize with real JSON configs
    initialize_agent_registry()
    yield get_agent_registry()
    # Cleanup
    reset_agent_registry()


@pytest.fixture
def sample_agent(initialized_registry):
    """Get the root agent (felix) from the registry for testing."""
    return initialized_registry.get_root_agent()


@pytest.fixture
def sample_child_agent(initialized_registry):
    """Get a child agent (topups) from the registry for testing."""
    return initialized_registry.get_agent("topups")


@pytest_asyncio.fixture
async def sample_user_context(db_session):
    """Create a sample user context for testing."""
    from app.models.user import UserContext

    user = UserContext(
        user_id="test_user_123",
        profile={
            "name": "Test User",
            "preferred_name": "Tester",
            "language": "es",
        },
        product_summaries={
            "topups": {"lifetimeCount": 5},
            "wallet": {"currentBalance": 100.00},
        },
        behavioral_summary="Test user who frequently uses topups.",
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def sample_session(db_session, sample_agent):
    """Create a sample conversation session."""
    from app.models.session import ConversationSession

    session = ConversationSession(
        user_id="test_user_123",
        agent_stack=[{
            "agentId": sample_agent.config_id,  # Use config_id instead of UUID
            "enteredAt": "2025-01-01T00:00:00",
            "entryReason": "Session start",
        }],
        status="active",
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session


@pytest_asyncio.fixture
async def sample_session_with_child(db_session, sample_agent, sample_child_agent):
    """Create a session with agent stack containing parent and child."""
    from app.models.session import ConversationSession

    session = ConversationSession(
        user_id="test_user_123",
        agent_stack=[
            {
                "agentId": sample_agent.config_id,  # Use config_id instead of UUID
                "enteredAt": "2025-01-01T00:00:00",
                "entryReason": "Session start",
            },
            {
                "agentId": sample_child_agent.config_id,  # Use config_id instead of UUID
                "enteredAt": "2025-01-01T00:01:00",
                "entryReason": "User requested topups",
            },
        ],
        status="active",
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session


# ============= FastAPI Test Client =============

@pytest_asyncio.fixture
async def test_client(db_session, patched_llm_client) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with mocked dependencies."""
    from app.main import app
    from app.database import get_db

    # Override the database dependency
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
