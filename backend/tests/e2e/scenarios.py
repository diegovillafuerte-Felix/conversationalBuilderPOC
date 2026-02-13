"""E2E conversation scenario definitions.

Each scenario defines a multi-turn conversation with minimal structural gates.
Quality judgment is left to whoever reads the output (Claude Code or a human).
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TurnGate:
    """Minimal structural gates — catches 'system is broken', not 'wrong answer'."""
    non_empty_message: bool = True
    agent_id_not: list[str] | None = None  # should NOT be one of these agents
    expect_escalated: bool | None = None    # True = must be escalated, False = must NOT be


@dataclass
class ScenarioTurn:
    user_message: str
    description: str = ""
    gate: TurnGate = field(default_factory=TurnGate)


@dataclass
class Scenario:
    id: str
    name: str
    description: str
    user_id: str
    turns: list[ScenarioTurn]
    smoke: bool = False  # True = single-turn quick test


# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------

SCENARIOS: list[Scenario] = [
    Scenario(
        id="greeting_smoke",
        name="Greeting smoke test",
        description="User greets Felix. Should get a friendly response without routing.",
        user_id="user_demo",
        smoke=True,
        turns=[
            ScenarioTurn(
                user_message="Hola, soy nuevo aqui",
                description="Felix should greet the user by name (Juan) and offer help",
                gate=TurnGate(non_empty_message=True),
            ),
        ],
    ),
    Scenario(
        id="exchange_rate_smoke",
        name="Exchange rate inquiry",
        description="User asks for exchange rate to Mexico. Should route to remittances and call get_exchange_rate.",
        user_id="user_demo",
        smoke=True,
        turns=[
            ScenarioTurn(
                user_message="Cual es el tipo de cambio a Mexico?",
                description="Should route to remittances agent and return exchange rate info",
                gate=TurnGate(non_empty_message=True),
            ),
        ],
    ),
    Scenario(
        id="escalation",
        name="Human agent escalation",
        description="User requests a human agent. Should escalate.",
        user_id="user_demo",
        smoke=True,
        turns=[
            ScenarioTurn(
                user_message="Quiero hablar con un agente humano",
                description="Should escalate to human agent",
                gate=TurnGate(non_empty_message=True, expect_escalated=True),
            ),
        ],
    ),
    Scenario(
        id="remittance_flow",
        name="Remittance send money flow",
        description="User wants to send money to Mexico. Multi-turn flow through recipient selection and amount.",
        user_id="user_demo",
        turns=[
            ScenarioTurn(
                user_message="Quiero enviar dinero a Mexico",
                description="Should route to remittances, start send money flow, list recipients",
                gate=TurnGate(non_empty_message=True),
            ),
            ScenarioTurn(
                user_message="A Maria Garcia",
                description="Should select Maria as recipient and show details or ask for amount",
                gate=TurnGate(non_empty_message=True),
            ),
            ScenarioTurn(
                user_message="200 dolares",
                description="Should engage with the amount — show exchange rate, fees, or confirmation",
                gate=TurnGate(non_empty_message=True),
            ),
        ],
    ),
    Scenario(
        id="multi_product_nav",
        name="Multi-product navigation",
        description="User navigates across wallet, credit, and topups agents in one session.",
        user_id="user_demo",
        turns=[
            ScenarioTurn(
                user_message="Cual es mi saldo de wallet?",
                description="Should route to wallet agent and show balance",
                gate=TurnGate(non_empty_message=True),
            ),
            ScenarioTurn(
                user_message="Y cuanto debo del credito?",
                description="Should route to SNPL agent and show debt/balance info",
                gate=TurnGate(non_empty_message=True),
            ),
            ScenarioTurn(
                user_message="Quiero hacer una recarga",
                description="Should route to topups agent and start the flow",
                gate=TurnGate(non_empty_message=True),
            ),
        ],
    ),
]


def get_scenario(scenario_id: str) -> Scenario | None:
    """Get a scenario by ID."""
    for s in SCENARIOS:
        if s.id == scenario_id:
            return s
    return None


def get_smoke_scenarios() -> list[Scenario]:
    """Get only smoke (single-turn) scenarios."""
    return [s for s in SCENARIOS if s.smoke]
