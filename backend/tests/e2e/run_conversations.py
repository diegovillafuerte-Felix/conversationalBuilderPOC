#!/usr/bin/env python3
"""E2E conversation runner — Claude Code's primary testing tool.

Runs multi-turn conversations against the live system and produces
rich, readable output files. Designed to be read and assessed by
Claude Code (or a human), not to produce pass/fail verdicts.

Usage:
    # Run all scenarios
    cd backend && ./venv/bin/python -m tests.e2e.run_conversations

    # Run a specific scenario
    cd backend && ./venv/bin/python -m tests.e2e.run_conversations --scenario remittance_flow

    # Run smoke tests only (single-turn scenarios)
    cd backend && ./venv/bin/python -m tests.e2e.run_conversations --smoke

    # Skip server health checks (if you know servers are up)
    cd backend && ./venv/bin/python -m tests.e2e.run_conversations --no-health-check
"""

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

from tests.e2e.scenarios import (
    SCENARIOS,
    Scenario,
    ScenarioTurn,
    get_scenario,
    get_smoke_scenarios,
)
from tests.e2e.server_manager import ServerManager, BACKEND_URL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

RESULTS_DIR = Path(__file__).parent / "results"
CHAT_ENDPOINT = f"{BACKEND_URL}/api/chat/message"


@dataclass
class TurnResult:
    turn_number: int
    user_message: str
    description: str
    response_message: str
    agent_id: str
    agent_name: str
    tool_calls: list[dict]
    flow_state: str | None
    escalated: bool
    elapsed_seconds: float
    http_status: int
    gate_failures: list[str]
    raw_response: dict


@dataclass
class ScenarioResult:
    scenario: Scenario
    session_id: str | None
    turn_results: list[TurnResult]
    total_seconds: float
    gate_failures: list[str]

    @property
    def ok(self) -> bool:
        return len(self.gate_failures) == 0


def run_turn(
    client: httpx.Client,
    turn: ScenarioTurn,
    turn_number: int,
    user_id: str,
    session_id: str | None,
) -> TurnResult:
    """Execute a single conversation turn and check structural gates."""
    payload = {
        "user_id": user_id,
        "message": turn.user_message,
    }
    if session_id:
        payload["session_id"] = session_id

    start = time.time()
    try:
        resp = client.post(CHAT_ENDPOINT, json=payload, timeout=60.0)
        elapsed = time.time() - start
    except httpx.TimeoutException:
        elapsed = time.time() - start
        return TurnResult(
            turn_number=turn_number,
            user_message=turn.user_message,
            description=turn.description,
            response_message="",
            agent_id="",
            agent_name="",
            tool_calls=[],
            flow_state=None,
            escalated=False,
            elapsed_seconds=elapsed,
            http_status=0,
            gate_failures=["TIMEOUT: Request timed out after 60s"],
            raw_response={},
        )

    gate_failures = []

    # HTTP-level gate
    if resp.status_code != 200:
        gate_failures.append(f"HTTP {resp.status_code}: {resp.text[:200]}")
        return TurnResult(
            turn_number=turn_number,
            user_message=turn.user_message,
            description=turn.description,
            response_message="",
            agent_id="",
            agent_name="",
            tool_calls=[],
            flow_state=None,
            escalated=False,
            elapsed_seconds=elapsed,
            http_status=resp.status_code,
            gate_failures=gate_failures,
            raw_response={},
        )

    data = resp.json()

    # Structural gates
    message = data.get("message", "")
    if turn.gate.non_empty_message and not message.strip():
        gate_failures.append("EMPTY_MESSAGE: Response message is empty")

    agent_id = data.get("agent_id", "")
    if turn.gate.agent_id_not and agent_id in turn.gate.agent_id_not:
        gate_failures.append(f"WRONG_AGENT: agent_id={agent_id} is in excluded list {turn.gate.agent_id_not}")

    escalated = data.get("escalated", False)
    if turn.gate.expect_escalated is True and not escalated:
        gate_failures.append("NOT_ESCALATED: Expected escalated=true but got false")
    elif turn.gate.expect_escalated is False and escalated:
        gate_failures.append("UNEXPECTED_ESCALATION: Expected escalated=false but got true")

    tool_calls = []
    for tc in data.get("tool_calls", []):
        tool_calls.append({
            "name": tc.get("tool_name", ""),
            "params": tc.get("parameters", {}),
            "result": tc.get("result"),
        })

    return TurnResult(
        turn_number=turn_number,
        user_message=turn.user_message,
        description=turn.description,
        response_message=message,
        agent_id=agent_id,
        agent_name=data.get("agent_name", ""),
        tool_calls=tool_calls,
        flow_state=data.get("flow_state"),
        escalated=escalated,
        elapsed_seconds=elapsed,
        http_status=resp.status_code,
        gate_failures=gate_failures,
        raw_response=data,
    )


def run_scenario(client: httpx.Client, scenario: Scenario) -> ScenarioResult:
    """Run all turns in a scenario sequentially."""
    session_id = None
    turn_results = []
    all_gate_failures = []
    scenario_start = time.time()

    for i, turn in enumerate(scenario.turns, 1):
        result = run_turn(client, turn, i, scenario.user_id, session_id)
        turn_results.append(result)
        all_gate_failures.extend(result.gate_failures)

        # Capture session_id from first turn for subsequent turns
        if result.raw_response.get("session_id"):
            session_id = result.raw_response["session_id"]

        # Hard stop if HTTP failure or timeout — remaining turns won't work
        if result.http_status != 200:
            for remaining_turn in scenario.turns[i:]:
                all_gate_failures.append(
                    f"SKIPPED: Turn {i+1} skipped due to prior failure"
                )
            break

    total_seconds = time.time() - scenario_start
    return ScenarioResult(
        scenario=scenario,
        session_id=session_id,
        turn_results=turn_results,
        total_seconds=total_seconds,
        gate_failures=all_gate_failures,
    )


def format_result(result: ScenarioResult) -> str:
    """Format a scenario result as readable text."""
    lines = []
    lines.append(f"=== SCENARIO: {result.scenario.id} ===")
    lines.append(f"Name: {result.scenario.name}")
    lines.append(f"Description: {result.scenario.description}")
    lines.append(f"Session: {result.session_id or 'N/A'}")
    lines.append(f"User: {result.scenario.user_id}")
    lines.append("")

    for tr in result.turn_results:
        lines.append(f"--- Turn {tr.turn_number} ({tr.elapsed_seconds:.1f}s) ---")
        if tr.description:
            lines.append(f"[{tr.description}]")
        lines.append(f'User: "{tr.user_message}"')
        lines.append(f"Agent: {tr.agent_id} ({tr.agent_name})")

        if tr.tool_calls:
            tool_strs = []
            for tc in tr.tool_calls:
                params_str = ", ".join(f"{k}={v}" for k, v in tc["params"].items()) if tc["params"] else ""
                tool_strs.append(f"{tc['name']}({params_str})")
            lines.append(f"Tools: {' → '.join(tool_strs)}")

        if tr.flow_state:
            lines.append(f"Flow state: {tr.flow_state}")
        if tr.escalated:
            lines.append("Escalated: YES")

        # Response (indent for readability)
        lines.append(f"Response: {tr.response_message}")

        if tr.gate_failures:
            for gf in tr.gate_failures:
                lines.append(f"  ⚠ GATE FAILURE: {gf}")

        lines.append("")

    status = "OK" if result.ok else f"GATE FAILURES ({len(result.gate_failures)})"
    lines.append(
        f"=== RESULT: {status} "
        f"({len(result.turn_results)} turns, {result.total_seconds:.1f}s total) ==="
    )

    if not result.ok:
        lines.append("")
        lines.append("Gate failures:")
        for gf in result.gate_failures:
            lines.append(f"  - {gf}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Run E2E conversation scenarios")
    parser.add_argument("--scenario", type=str, help="Run a specific scenario by ID")
    parser.add_argument("--smoke", action="store_true", help="Run only smoke (single-turn) scenarios")
    parser.add_argument("--no-health-check", action="store_true", help="Skip server health checks")
    parser.add_argument("--results-dir", type=str, help="Output directory for results")
    args = parser.parse_args()

    # Determine which scenarios to run
    if args.scenario:
        scenario = get_scenario(args.scenario)
        if not scenario:
            available = ", ".join(s.id for s in SCENARIOS)
            print(f"Unknown scenario: {args.scenario}")
            print(f"Available: {available}")
            sys.exit(1)
        scenarios = [scenario]
    elif args.smoke:
        scenarios = get_smoke_scenarios()
    else:
        scenarios = SCENARIOS

    results_dir = Path(args.results_dir) if args.results_dir else RESULTS_DIR
    results_dir.mkdir(parents=True, exist_ok=True)

    # Health check
    if not args.no_health_check:
        manager = ServerManager()
        if not manager.is_backend_running():
            print("ERROR: Backend is not running on port 8000")
            print("Start it with: cd backend && ./venv/bin/python -m uvicorn app.main:app --port 8000")
            sys.exit(1)
        if not manager.is_services_running():
            print("ERROR: Services gateway is not running on port 8001")
            print("Start it with: cd services && ./venv/bin/python -m uvicorn app.main:app --port 8001")
            sys.exit(1)
        logger.info("Both servers are healthy")

    # Run scenarios
    client = httpx.Client()
    all_results: list[ScenarioResult] = []
    total_gate_failures = 0

    print(f"\nRunning {len(scenarios)} scenario(s)...\n")

    for scenario in scenarios:
        logger.info(f"Running: {scenario.id} ({scenario.name})")
        result = run_scenario(client, scenario)
        all_results.append(result)

        # Write individual result file
        output_path = results_dir / f"{scenario.id}.txt"
        output_path.write_text(format_result(result))

        status = "OK" if result.ok else "GATE FAILURE"
        print(f"  {scenario.id}: {status} ({len(result.turn_results)} turns, {result.total_seconds:.1f}s)")

        if not result.ok:
            total_gate_failures += len(result.gate_failures)
            for gf in result.gate_failures:
                print(f"    ⚠ {gf}")

    client.close()

    # Summary
    total_time = sum(r.total_seconds for r in all_results)
    total_turns = sum(len(r.turn_results) for r in all_results)
    ok_count = sum(1 for r in all_results if r.ok)
    fail_count = len(all_results) - ok_count

    print(f"\n{'='*60}")
    print(f"Results: {ok_count} OK, {fail_count} failed ({total_turns} turns, {total_time:.1f}s)")
    print(f"Output: {results_dir}/")
    print(f"{'='*60}")

    # Write summary file
    summary_lines = ["=== E2E SUMMARY ===", ""]
    for r in all_results:
        status = "OK" if r.ok else "FAIL"
        summary_lines.append(f"[{status}] {r.scenario.id}: {len(r.turn_results)} turns, {r.total_seconds:.1f}s")
    summary_lines.append("")
    summary_lines.append(f"Total: {ok_count} OK, {fail_count} failed, {total_turns} turns, {total_time:.1f}s")
    (results_dir / "_summary.txt").write_text("\n".join(summary_lines))

    sys.exit(1 if total_gate_failures > 0 else 0)


if __name__ == "__main__":
    main()
