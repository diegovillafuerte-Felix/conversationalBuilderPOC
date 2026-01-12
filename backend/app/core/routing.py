"""Routing types and data classes for the orchestrator."""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Any, List


class RoutingType(Enum):
    """Types of routing actions."""
    ENTER_AGENT = "enter_agent"
    START_FLOW = "start_flow"
    NAVIGATION = "navigation"  # up_one_level, go_home, escalate_to_human
    SERVICE = "service"  # Regular service tools


class NavigationAction(Enum):
    """Navigation action targets."""
    UP_ONE_LEVEL = "up_one_level"
    GO_HOME = "go_home"
    ESCALATE_TO_HUMAN = "escalate_to_human"


@dataclass
class RoutingConfig:
    """
    Explicit routing configuration for a tool.

    Attributes:
        type: The type of routing action
        target: Target identifier (agent config_id, subflow config_id, or navigation action)
        cross_agent: For cross-agent flows, the agent config_id to enter first
    """
    type: RoutingType
    target: Optional[str]
    cross_agent: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "RoutingConfig":
        """Create RoutingConfig from dictionary (from database or config)."""
        if not data:
            return cls(type=RoutingType.SERVICE, target=None)
        return cls(
            type=RoutingType(data["type"]),
            target=data.get("target"),
            cross_agent=data.get("cross_agent")
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        result = {
            "type": self.type.value,
            "target": self.target,
        }
        if self.cross_agent:
            result["cross_agent"] = self.cross_agent
        return result


@dataclass
class RoutingResult:
    """
    Result of routing resolution.

    Attributes:
        success: Whether routing resolution succeeded
        action: The type of routing action
        target_id: Database ID of the resolved target (Agent/Subflow UUID as string)
        target_entity: The actual loaded entity (Agent or Subflow object)
        error: Error message if resolution failed
    """
    success: bool
    action: RoutingType
    target_id: Optional[str]
    target_entity: Optional[Any]
    error: Optional[str] = None


@dataclass
class RoutingOutcome:
    """
    Outcome of routing execution.

    Attributes:
        handled: Whether this was a routing action (vs regular tool)
        state_changed: Whether session state changed (agent/flow transition)
        context_requirements: List of data keys to fetch for context enrichment
        response_text: Direct response text to return (only for errors/escalation)
        error: Error message if execution failed
    """
    handled: bool
    state_changed: bool
    context_requirements: List[str] = field(default_factory=list)
    response_text: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "handled": self.handled,
            "state_changed": self.state_changed,
            "context_requirements": self.context_requirements,
            "response_text": self.response_text,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RoutingOutcome":
        """Create RoutingOutcome from dictionary."""
        return cls(
            handled=data.get("handled", False),
            state_changed=data.get("state_changed", False),
            context_requirements=data.get("context_requirements", []),
            response_text=data.get("response_text"),
            error=data.get("error"),
        )
