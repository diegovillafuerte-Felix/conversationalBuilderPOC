"""Unit tests for declarative transition condition evaluation."""

from app.core.condition_evaluator import evaluate_condition


def test_compare_and_boolean_logic():
    context = {"amount": 250, "max_amount": 600}
    assert evaluate_condition("amount >= 200 and amount <= max_amount", context) is True
    assert evaluate_condition("amount > max_amount", context) is False


def test_nested_path_and_boolean_literals():
    context = {
        "application": {"approved": True},
        "_tool_result": {"recipient_id": "rec_123"},
    }
    assert evaluate_condition("application.approved == true", context) is True
    assert evaluate_condition("_tool_result.recipient_id is not None", context) is True


def test_snake_and_camel_path_resolution():
    context = {
        "_tool_result": {"recipient_id": "rec_999"},
    }
    assert evaluate_condition("_tool_result.recipientId is not None", context) is True


def test_legacy_in_syntax():
    context = {"stateData": {"carrier_id": "telcel"}, "carrier_id": "telcel"}
    assert evaluate_condition("carrier_id in stateData", context) is True
