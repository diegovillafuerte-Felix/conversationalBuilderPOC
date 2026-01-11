"""Pytest integration for running conversational test scenarios."""

import pytest
from pathlib import Path

from .runner import ConversationalTestRunner
from .schemas import TestScenario
from .conftest import get_all_agent_scenarios


def scenario_id(val):
    """Generate test IDs for pytest parametrization."""
    if isinstance(val, tuple):
        agent_name, scenario = val
        return f"{agent_name}::{scenario.id}"
    return str(val)


class TestAgentScenarios:
    """Test class for running agent-defined scenarios."""

    @pytest.mark.conversational
    @pytest.mark.slow
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "agent_scenario",
        get_all_agent_scenarios(),
        ids=scenario_id,
    )
    async def test_scenario(self, db_session, mock_llm_client, agent_scenario):
        """Run a single test scenario from agent configs."""
        agent_name, scenario = agent_scenario

        if not scenario.enabled:
            pytest.skip(f"Scenario {scenario.id} is disabled")

        runner = ConversationalTestRunner(
            db=db_session,
            llm_client=mock_llm_client,
        )

        result = await runner.run_scenario(scenario)

        # Generate detailed failure message
        if not result.passed:
            failure_msg = self._format_failure_message(result)
            pytest.fail(failure_msg)

    def _format_failure_message(self, result) -> str:
        """Format a detailed failure message."""
        lines = [
            f"Scenario '{result.scenario_name}' failed:",
            f"  Failed turns: {result.failed_turns}/{result.total_turns}",
        ]

        for tr in result.turn_results:
            if not tr.passed:
                lines.append(f"  Turn {tr.turn_number}: {tr.user_input[:50]}...")
                if tr.error:
                    lines.append(f"    Error: {tr.error}")
                for br in tr.behavior_results:
                    if not br.passed:
                        lines.append(f"    - {br.behavior_type}: {br.message}")

        for criterion, passed in result.success_criteria_results.items():
            if not passed:
                lines.append(f"  Criterion failed: {criterion}")

        if result.error_message:
            lines.append(f"  Error: {result.error_message}")

        return "\n".join(lines)


class TestScenarioRunner:
    """Test the scenario runner itself."""

    @pytest.mark.asyncio
    async def test_runner_basic(self, db_session, mock_llm_client, sample_scenario):
        """Test that the runner can execute a simple scenario."""
        runner = ConversationalTestRunner(
            db=db_session,
            llm_client=mock_llm_client,
        )

        result = await runner.run_scenario(sample_scenario)

        assert result is not None
        assert result.scenario_id == "test_sample"
        assert result.total_turns == 1

    @pytest.mark.asyncio
    async def test_runner_disabled_scenario(self, db_session, mock_llm_client):
        """Test that disabled scenarios are skipped."""
        scenario = TestScenario(
            id="disabled_test",
            name={"en": "Disabled Test"},
            description="A disabled scenario",
            turns=[{"user_input": "Hello", "expected_behaviors": []}],
            enabled=False,
        )

        runner = ConversationalTestRunner(
            db=db_session,
            llm_client=mock_llm_client,
        )

        result = await runner.run_scenario(scenario)

        assert result.passed is True
        assert "disabled" in result.error_message.lower()


class TestResponseValidator:
    """Test the response validators."""

    def test_validate_contains_text_pass(self):
        """Test contains_text validation passing."""
        from .validators import ResponseValidator
        from .schemas import ExpectedBehavior

        validator = ResponseValidator()
        behavior = ExpectedBehavior(
            type="contains_text",
            text=["hola", "ayudar"],
        )

        result = validator.validate(
            behavior=behavior,
            response_text="¡Hola! ¿En qué puedo ayudar?",
            tool_calls=[],
        )

        assert result.passed is True

    def test_validate_contains_text_fail(self):
        """Test contains_text validation failing."""
        from .validators import ResponseValidator
        from .schemas import ExpectedBehavior

        validator = ResponseValidator()
        behavior = ExpectedBehavior(
            type="contains_text",
            text=["recarga", "topup"],
        )

        result = validator.validate(
            behavior=behavior,
            response_text="¡Hola! ¿En qué puedo ayudar?",
            tool_calls=[],
        )

        assert result.passed is False

    def test_validate_contains_any_pass(self):
        """Test contains_any validation passing."""
        from .validators import ResponseValidator
        from .schemas import ExpectedBehavior

        validator = ResponseValidator()
        behavior = ExpectedBehavior(
            type="contains_any",
            text=["recarga", "hola", "topup"],
        )

        result = validator.validate(
            behavior=behavior,
            response_text="¡Hola!",
            tool_calls=[],
        )

        assert result.passed is True

    def test_validate_tool_call_pass(self):
        """Test tool_call validation passing."""
        from .validators import ResponseValidator
        from .schemas import ExpectedBehavior

        validator = ResponseValidator()
        behavior = ExpectedBehavior(
            type="tool_call",
            tool="start_flow_recarga",
        )

        result = validator.validate(
            behavior=behavior,
            response_text="",
            tool_calls=["start_flow_recarga", "get_carriers"],
        )

        assert result.passed is True

    def test_validate_tool_call_fail(self):
        """Test tool_call validation failing."""
        from .validators import ResponseValidator
        from .schemas import ExpectedBehavior

        validator = ResponseValidator()
        behavior = ExpectedBehavior(
            type="tool_call",
            tool="send_topup",
        )

        result = validator.validate(
            behavior=behavior,
            response_text="",
            tool_calls=["get_carriers"],
        )

        assert result.passed is False

    def test_validate_not_contains_pass(self):
        """Test not_contains validation passing."""
        from .validators import ResponseValidator
        from .schemas import ExpectedBehavior

        validator = ResponseValidator()
        behavior = ExpectedBehavior(
            type="not_contains",
            text=["error", "problema"],
        )

        result = validator.validate(
            behavior=behavior,
            response_text="¡Listo! Tu recarga fue exitosa.",
            tool_calls=[],
        )

        assert result.passed is True

    def test_validate_regex_match_pass(self):
        """Test regex_match validation passing."""
        from .validators import ResponseValidator
        from .schemas import ExpectedBehavior

        validator = ResponseValidator()
        behavior = ExpectedBehavior(
            type="regex_match",
            pattern=r"\$\d+",
        )

        result = validator.validate(
            behavior=behavior,
            response_text="El total es $100 MXN",
            tool_calls=[],
        )

        assert result.passed is True

    def test_validate_flow_state_pass(self):
        """Test flow_state validation passing."""
        from .validators import ResponseValidator
        from .schemas import ExpectedBehavior

        validator = ResponseValidator()
        behavior = ExpectedBehavior(
            type="flow_state",
            text=["select_amount"],
        )

        result = validator.validate(
            behavior=behavior,
            response_text="",
            tool_calls=[],
            flow_state="select_amount",
        )

        assert result.passed is True
