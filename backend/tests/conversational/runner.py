"""Test scenario runner that simulates conversations."""

import logging
import time
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.orchestrator import Orchestrator
from app.models.user import UserContext

from .schemas import (
    TestScenario,
    ConversationTurn,
    ScenarioResult,
    TurnResult,
    BehaviorResult,
)
from .validators import ResponseValidator

logger = logging.getLogger(__name__)


class ConversationalTestRunner:
    """Runs test scenarios by simulating multi-turn conversations."""

    def __init__(
        self,
        db: AsyncSession,
        llm_client=None,
    ):
        self.db = db
        self.llm_client = llm_client
        self.validator = ResponseValidator()

    async def run_scenario(self, scenario: TestScenario) -> ScenarioResult:
        """Run a single test scenario."""
        start_time = time.time()

        if not scenario.enabled:
            return ScenarioResult(
                scenario_id=scenario.id,
                scenario_name=scenario.name.get("en", scenario.id),
                passed=True,
                turn_results=[],
                success_criteria_results={},
                total_turns=0,
                failed_turns=0,
                error_message="Scenario disabled",
            )

        try:
            # Setup initial context
            await self._setup_context(scenario.initial_context)

            # Create orchestrator
            orchestrator = Orchestrator(
                db=self.db,
                llm_client=self.llm_client,
            )

            # Run conversation turns
            session_id = None
            turn_results: List[TurnResult] = []
            all_tool_calls: List[str] = []

            for i, turn in enumerate(scenario.turns):
                result = await self._run_turn(
                    orchestrator=orchestrator,
                    turn=turn,
                    user_id=scenario.initial_context.user_id,
                    session_id=session_id,
                    turn_number=i + 1,
                )

                turn_results.append(result)
                session_id = result.session_id
                all_tool_calls.extend(result.tool_calls)

            # Evaluate success criteria
            success_criteria_results = self._evaluate_success_criteria(
                scenario=scenario,
                turn_results=turn_results,
                all_tool_calls=all_tool_calls,
            )

            # Determine overall pass/fail
            failed_turns = sum(1 for tr in turn_results if not tr.passed)
            criteria_passed = all(success_criteria_results.values()) if success_criteria_results else True
            passed = failed_turns == 0 and criteria_passed

            execution_time_ms = int((time.time() - start_time) * 1000)

            return ScenarioResult(
                scenario_id=scenario.id,
                scenario_name=scenario.name.get("en", scenario.id),
                passed=passed,
                turn_results=turn_results,
                success_criteria_results=success_criteria_results,
                total_turns=len(scenario.turns),
                failed_turns=failed_turns,
                execution_time_ms=execution_time_ms,
            )

        except Exception as e:
            logger.exception(f"Error running scenario {scenario.id}")
            return ScenarioResult(
                scenario_id=scenario.id,
                scenario_name=scenario.name.get("en", scenario.id),
                passed=False,
                turn_results=[],
                success_criteria_results={},
                total_turns=len(scenario.turns),
                failed_turns=len(scenario.turns),
                error_message=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

    async def _setup_context(self, context) -> None:
        """Set up the initial test context (user, balance, etc.)."""
        # Check if user exists, create or update
        result = await self.db.execute(
            select(UserContext).where(UserContext.user_id == context.user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            user = UserContext(
                user_id=context.user_id,
                profile={
                    "name": "Test User",
                    "language": context.language,
                },
                product_summaries={
                    "wallet": {"currentBalance": context.user_balance}
                },
            )
            self.db.add(user)
        else:
            user.profile["language"] = context.language
            if user.product_summaries:
                user.product_summaries["wallet"] = {"currentBalance": context.user_balance}
            else:
                user.product_summaries = {"wallet": {"currentBalance": context.user_balance}}

        await self.db.flush()

    async def _run_turn(
        self,
        orchestrator: Orchestrator,
        turn: ConversationTurn,
        user_id: str,
        session_id: Optional[str],
        turn_number: int,
    ) -> TurnResult:
        """Run a single conversation turn."""
        try:
            from uuid import UUID

            session_uuid = UUID(session_id) if session_id else None

            response = await orchestrator.handle_message(
                user_message=turn.user_input,
                user_id=user_id,
                session_id=session_uuid,
            )

            # Extract tool call names
            tool_calls = [tc.get("name", "") for tc in response.tool_calls]

            # Validate expected behaviors
            behavior_results: List[BehaviorResult] = []
            for behavior in turn.expected_behaviors:
                result = self.validator.validate(
                    behavior=behavior,
                    response_text=response.message,
                    tool_calls=tool_calls,
                    flow_state=response.flow_state,
                )
                behavior_results.append(result)

            all_passed = all(br.passed for br in behavior_results) if behavior_results else True

            return TurnResult(
                turn_number=turn_number,
                user_input=turn.user_input,
                agent_response=response.message,
                session_id=str(response.session_id),
                agent_name=response.agent_name,
                tool_calls=tool_calls,
                flow_state=response.flow_state,
                behavior_results=behavior_results,
                passed=all_passed,
            )

        except Exception as e:
            logger.exception(f"Error in turn {turn_number}")
            return TurnResult(
                turn_number=turn_number,
                user_input=turn.user_input,
                passed=False,
                error=str(e),
            )

    def _evaluate_success_criteria(
        self,
        scenario: TestScenario,
        turn_results: List[TurnResult],
        all_tool_calls: List[str],
    ) -> dict:
        """Evaluate the overall success criteria."""
        criteria = scenario.success_criteria
        results = {}

        if criteria.final_state:
            last_turn = turn_results[-1] if turn_results else None
            results["final_state"] = (
                last_turn.flow_state == criteria.final_state if last_turn else False
            )

        if criteria.tools_called:
            results["tools_called"] = all(
                tool in all_tool_calls for tool in criteria.tools_called
            )

        if criteria.no_escalation:
            results["no_escalation"] = not any(
                "escalate" in tc for tc in all_tool_calls
            )

        if criteria.no_error_state:
            results["no_error_state"] = not any(
                tr.flow_state == "error_state" for tr in turn_results
            )

        if criteria.max_turns:
            results["max_turns"] = len(turn_results) <= criteria.max_turns

        return results

    async def run_all_scenarios(
        self, scenarios: List[TestScenario]
    ) -> List[ScenarioResult]:
        """Run all test scenarios."""
        results = []
        for scenario in scenarios:
            result = await self.run_scenario(scenario)
            results.append(result)
            status = "PASSED" if result.passed else "FAILED"
            logger.info(f"Scenario {scenario.id}: {status}")
        return results
