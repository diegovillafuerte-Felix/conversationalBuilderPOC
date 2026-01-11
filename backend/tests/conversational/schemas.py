"""Pydantic schemas for conversational test scenarios."""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class ExpectedBehavior(BaseModel):
    """Definition of an expected behavior in a conversation turn."""

    type: Literal[
        "tool_call",           # Agent should call a specific tool
        "contains_text",       # Response should contain ALL specified texts
        "contains_any",        # Response should contain ANY of the texts
        "not_contains",        # Response should NOT contain text
        "regex_match",         # Response should match regex
        "flow_state",          # Session should be in a specific flow state
    ]

    # For tool_call
    tool: Optional[str] = None
    params: Optional[Dict[str, Any]] = None

    # For text matching
    text: Optional[List[str]] = None
    pattern: Optional[str] = None

    # Case sensitivity
    case_sensitive: bool = False


class ConversationTurn(BaseModel):
    """A single turn in a test conversation."""

    user_input: str = Field(..., description="The user's message")
    expected_behaviors: List[ExpectedBehavior] = Field(
        default_factory=list,
        description="List of expected behaviors for this turn"
    )
    description: Optional[str] = Field(
        None, description="Optional description of what this turn tests"
    )


class SuccessCriteria(BaseModel):
    """Success criteria for the overall scenario."""

    final_state: Optional[str] = None
    tools_called: Optional[List[str]] = None
    no_escalation: bool = False
    no_error_state: bool = False
    max_turns: Optional[int] = None


class InitialContext(BaseModel):
    """Initial context setup for the test."""

    user_id: str = "test_scenario_user"
    user_balance: float = 100.0
    language: str = "es"
    extra: Dict[str, Any] = Field(default_factory=dict)


class TestScenario(BaseModel):
    """A complete test scenario definition."""

    id: str = Field(..., description="Unique identifier for the scenario")
    name: Dict[str, str] = Field(..., description="Localized names")
    description: str = Field(..., description="Description of what the scenario tests")

    initial_context: InitialContext = Field(default_factory=InitialContext)
    turns: List[ConversationTurn] = Field(..., min_length=1)
    success_criteria: SuccessCriteria = Field(default_factory=SuccessCriteria)

    tags: List[str] = Field(default_factory=list)
    enabled: bool = True


class BehaviorResult(BaseModel):
    """Result of validating a single expected behavior."""

    behavior_type: str
    passed: bool
    message: str
    expected: Optional[Any] = None
    actual: Optional[Any] = None


class TurnResult(BaseModel):
    """Result of a single conversation turn."""

    turn_number: int
    user_input: str
    agent_response: Optional[str] = None
    session_id: Optional[str] = None
    agent_name: Optional[str] = None
    tool_calls: List[str] = Field(default_factory=list)
    flow_state: Optional[str] = None
    behavior_results: List[BehaviorResult] = Field(default_factory=list)
    passed: bool
    error: Optional[str] = None


class ScenarioResult(BaseModel):
    """Result of running a test scenario."""

    scenario_id: str
    scenario_name: str
    passed: bool

    turn_results: List[TurnResult] = Field(default_factory=list)
    success_criteria_results: Dict[str, bool] = Field(default_factory=dict)

    total_turns: int
    failed_turns: int

    error_message: Optional[str] = None
    execution_time_ms: int = 0
