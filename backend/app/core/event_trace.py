"""Event tracing system for debugging routing, tool calling, and orchestration flows."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, List
import uuid


class EventCategory(str, Enum):
    """Categories for trace events."""
    SESSION = "session"
    AGENT = "agent"
    FLOW = "flow"
    ROUTING = "routing"
    ENRICHMENT = "enrichment"
    LLM = "llm"
    TOOL = "tool"
    SERVICE = "service"
    SHADOW = "shadow"
    ERROR = "error"


class EventLevel(str, Enum):
    """Severity levels for trace events."""
    INFO = "info"
    DEBUG = "debug"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class TraceEvent:
    """A single trace event captured during message processing."""
    category: EventCategory
    event_type: str           # e.g., "tool_executed", "agent_entered"
    message: str              # Human-readable description
    timestamp: datetime = field(default_factory=datetime.utcnow)
    level: EventLevel = EventLevel.INFO
    data: dict = field(default_factory=dict)  # Event-specific payload
    duration_ms: Optional[int] = None
    parent_id: Optional[str] = None  # For nested events
    turn_id: Optional[str] = None  # Groups events by message turn
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])


class EventTracer:
    """Collects events during a single message processing cycle.

    Usage:
        tracer = EventTracer(turn_id="turn_123", user_message="Hello")
        tracer.trace(EventCategory.SESSION, "session_loaded", "Session loaded")

        # For timed operations:
        event_id = tracer.trace(EventCategory.LLM, "llm_request", "Calling LLM")
        # ... do work ...
        tracer.trace(EventCategory.LLM, "llm_response", "Response received",
                     duration_ms=elapsed, parent_id=event_id)

        # Export for API response:
        events = tracer.to_list()
    """

    def __init__(self, turn_id: str = None, user_message: str = None):
        self.events: List[TraceEvent] = []
        self._start_time = datetime.utcnow()
        self.turn_id = turn_id or uuid.uuid4().hex[:8]
        self.user_message = user_message
        self.assistant_response = None

    def set_response(self, response: str):
        """Set the assistant's response for this turn."""
        self.assistant_response = response

    def trace(
        self,
        category: EventCategory,
        event_type: str,
        message: str,
        level: EventLevel = EventLevel.INFO,
        data: dict = None,
        duration_ms: int = None,
        parent_id: str = None
    ) -> str:
        """Add a trace event and return its ID.

        Args:
            category: Event category (session, agent, routing, etc.)
            event_type: Specific event type (session_loaded, tool_started, etc.)
            message: Human-readable description
            level: Severity level (info, debug, warning, error)
            data: Additional event-specific data
            duration_ms: Duration of the operation in milliseconds
            parent_id: ID of parent event for nesting

        Returns:
            The event ID (useful for linking child events)
        """
        event = TraceEvent(
            category=category,
            event_type=event_type,
            message=message,
            level=level,
            data=data or {},
            duration_ms=duration_ms,
            parent_id=parent_id,
            turn_id=self.turn_id,
        )
        self.events.append(event)
        return event.id

    def error(self, event_type: str, message: str, data: dict = None) -> str:
        """Convenience method for error events."""
        return self.trace(
            EventCategory.ERROR,
            event_type,
            message,
            level=EventLevel.ERROR,
            data=data,
        )

    def warning(self, category: EventCategory, event_type: str, message: str, data: dict = None) -> str:
        """Convenience method for warning events."""
        return self.trace(
            category,
            event_type,
            message,
            level=EventLevel.WARNING,
            data=data,
        )

    def to_list(self) -> List[dict]:
        """Export events as a serializable list for API response."""
        return [
            {
                "id": e.id,
                "category": e.category.value,
                "event_type": e.event_type,
                "message": e.message,
                "timestamp": e.timestamp.isoformat(),
                "level": e.level.value,
                "data": e.data,
                "duration_ms": e.duration_ms,
                "parent_id": e.parent_id,
                "turn_id": e.turn_id,
                "user_message": self.user_message if e == self.events[0] else None,
                "assistant_response": self.assistant_response if e == self.events[0] else None,
            }
            for e in self.events
        ]

    def __len__(self) -> int:
        return len(self.events)
