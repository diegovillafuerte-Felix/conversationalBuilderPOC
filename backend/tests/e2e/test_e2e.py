"""Pytest wrapper for E2E conversation scenarios.

Thin wrapper around the same runner logic used by run_conversations.py.
Hard-fails only on structural gates. Use `--log-cli-level=INFO` for rich output.

Usage:
    cd backend && ./venv/bin/python -m pytest tests/e2e/ -v -m e2e --timeout=120
"""

import logging

import httpx
import pytest

from tests.e2e.scenarios import SCENARIOS, Scenario
from tests.e2e.run_conversations import run_scenario, format_result
from tests.e2e.server_manager import ServerManager, BACKEND_URL, SERVICES_URL

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def live_servers():
    """Verify servers are running before any E2E tests."""
    manager = ServerManager()
    if not manager.is_backend_running():
        pytest.skip(f"Backend not running at {BACKEND_URL}")
    if not manager.is_services_running():
        pytest.skip(f"Services gateway not running at {SERVICES_URL}")
    yield


@pytest.fixture(scope="session")
def http_client():
    """Shared HTTP client for all E2E tests."""
    client = httpx.Client()
    yield client
    client.close()


@pytest.mark.e2e
@pytest.mark.parametrize(
    "scenario",
    SCENARIOS,
    ids=[s.id for s in SCENARIOS],
)
def test_scenario(scenario: Scenario, live_servers, http_client: httpx.Client):
    """Run a conversation scenario and assert structural gates pass."""
    result = run_scenario(http_client, scenario)

    # Log the full readable output for debugging
    logger.info("\n" + format_result(result))

    assert result.ok, (
        f"Scenario '{scenario.id}' had gate failures:\n"
        + "\n".join(f"  - {gf}" for gf in result.gate_failures)
    )
