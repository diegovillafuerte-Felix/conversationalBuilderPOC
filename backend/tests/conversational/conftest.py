"""Fixtures for conversational tests."""

import pytest
import pytest_asyncio
import json
from pathlib import Path
from typing import List

from .schemas import TestScenario


def load_scenarios_from_agent_config(agent_config_path: Path) -> List[TestScenario]:
    """Load test scenarios from an agent's JSON config."""
    with open(agent_config_path) as f:
        config = json.load(f)

    scenarios_data = config.get("test_scenarios", [])
    return [TestScenario(**s) for s in scenarios_data]


def get_all_agent_scenarios():
    """Collect all scenarios from all agent configs."""
    # Path relative to this file
    config_dir = Path(__file__).parent.parent.parent / "app" / "config" / "agents"

    if not config_dir.exists():
        return []

    all_scenarios = []
    for config_file in config_dir.glob("*.json"):
        try:
            scenarios = load_scenarios_from_agent_config(config_file)
            for scenario in scenarios:
                all_scenarios.append((config_file.stem, scenario))
        except Exception as e:
            # Skip files that can't be parsed or don't have scenarios
            continue

    return all_scenarios


@pytest.fixture
def sample_scenario():
    """Create a sample test scenario for testing the runner."""
    return TestScenario(
        id="test_sample",
        name={"en": "Sample Test", "es": "Prueba de Ejemplo"},
        description="A sample test scenario for testing the runner",
        turns=[
            {
                "user_input": "Hola",
                "expected_behaviors": [],
            },
        ],
    )


@pytest.fixture
def topup_scenario():
    """Create a topup test scenario."""
    return TestScenario(
        id="test_topup_flow",
        name={"en": "Topup Flow Test", "es": "Prueba de Recarga"},
        description="Test the topup flow",
        initial_context={
            "user_id": "test_topup_user",
            "user_balance": 50.0,
            "language": "es",
        },
        turns=[
            {
                "user_input": "Quiero hacer una recarga",
                "expected_behaviors": [
                    {"type": "contains_any", "text": ["recarga", "ayudar", "número"]},
                ],
            },
        ],
        success_criteria={
            "no_escalation": True,
        },
    )
