"""Pydantic schemas for conversational test scenarios."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ExpectedBehavior(BaseModel):
    """Definition of an expected behavior in a conversation turn."""

    type: Literal[
        "tool_call",  # Agent should call a specific tool
        "contains_text",  # Response should contain ALL specified texts
        "contains_any",  # Response should contain ANY of the texts
        "not_contains",  # Response should NOT contain text
        "regex_match",  # Response should match regex
        "flow_state",  # Session should be in a specific flow state
    ]

    # For tool_call
    tool: str | None = None
    params: dict[str, Any] | None = None

    # For text matching
    text: list[str] | None = None
    pattern: str | None = None

    # Case sensitivity
    case_sensitive: bool = False


class ConversationTurn(BaseModel):
    """A single turn in a test conversation."""

    user_input: str = Field(..., description="The user's message")
    expected_behaviors: list[ExpectedBehavior] = Field(
        default_factory=list, description="List of expected behaviors for this turn"
    )
    description: str | None = Field(None, description="Optional description of what this turn tests")


class SuccessCriteria(BaseModel):
    """Success criteria for the overall scenario."""

    final_state: str | None = None
    tools_called: list[str] | None = None
    no_escalation: bool = False
    no_error_state: bool = False
    max_turns: int | None = None


class InitialContext(BaseModel):
    """Initial context setup for the test."""

    user_id: str = "test_scenario_user"
    user_balance: float = 100.0
    language: str = "es"
    extra: dict[str, Any] = Field(default_factory=dict)


class TestScenario(BaseModel):
    """A complete test scenario definition."""

    id: str = Field(..., description="Unique identifier for the scenario")
    name: dict[str, str] = Field(..., description="Localized names")
    description: str = Field(..., description="Description of what the scenario tests")

    initial_context: InitialContext = Field(default_factory=InitialContext)
    turns: list[ConversationTurn] = Field(..., min_length=1)
    success_criteria: SuccessCriteria = Field(default_factory=SuccessCriteria)

    tags: list[str] = Field(default_factory=list)
    enabled: bool = True


class BehaviorResult(BaseModel):
    """Result of validating a single expected behavior."""

    behavior_type: str
    passed: bool
    message: str
    expected: Any | None = None
    actual: Any | None = None


class TurnResult(BaseModel):
    """Result of a single conversation turn."""

    turn_number: int
    user_input: str
    agent_response: str | None = None
    session_id: str | None = None
    agent_name: str | None = None
    tool_calls: list[str] = Field(default_factory=list)
    flow_state: str | None = None
    behavior_results: list[BehaviorResult] = Field(default_factory=list)
    passed: bool
    error: str | None = None


class ScenarioResult(BaseModel):
    """Result of running a test scenario."""

    scenario_id: str
    scenario_name: str
    passed: bool

    turn_results: list[TurnResult] = Field(default_factory=list)
    success_criteria_results: dict[str, bool] = Field(default_factory=dict)

    total_turns: int
    failed_turns: int

    error_message: str | None = None
    execution_time_ms: int = 0
