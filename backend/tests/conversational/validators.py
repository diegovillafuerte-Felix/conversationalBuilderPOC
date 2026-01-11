"""Validators for checking expected behaviors in responses."""

import re
from typing import Dict, Any, List

from .schemas import ExpectedBehavior, BehaviorResult


class ResponseValidator:
    """Validates responses against expected behaviors."""

    def validate(
        self,
        behavior: ExpectedBehavior,
        response_text: str,
        tool_calls: List[str],
        flow_state: str = None,
    ) -> BehaviorResult:
        """Validate a single expected behavior."""
        validators = {
            "tool_call": self._validate_tool_call,
            "contains_text": self._validate_contains_text,
            "contains_any": self._validate_contains_any,
            "not_contains": self._validate_not_contains,
            "regex_match": self._validate_regex_match,
            "flow_state": self._validate_flow_state,
        }

        validator = validators.get(behavior.type)
        if not validator:
            return BehaviorResult(
                behavior_type=behavior.type,
                passed=False,
                message=f"Unknown behavior type: {behavior.type}",
            )

        return validator(behavior, response_text, tool_calls, flow_state)

    def _validate_tool_call(
        self,
        behavior: ExpectedBehavior,
        response_text: str,
        tool_calls: List[str],
        flow_state: str,
    ) -> BehaviorResult:
        """Validate that a specific tool was called."""
        expected_tool = behavior.tool

        passed = expected_tool in tool_calls

        message = (
            f"Tool '{expected_tool}' was called"
            if passed
            else f"Tool '{expected_tool}' was NOT called. Called: {tool_calls}"
        )

        return BehaviorResult(
            behavior_type="tool_call",
            passed=passed,
            message=message,
            expected=expected_tool,
            actual=tool_calls,
        )

    def _validate_contains_text(
        self,
        behavior: ExpectedBehavior,
        response_text: str,
        tool_calls: List[str],
        flow_state: str,
    ) -> BehaviorResult:
        """Validate that response contains ALL specified texts."""
        texts = behavior.text or []

        if behavior.case_sensitive:
            check_text = response_text
            missing = [t for t in texts if t not in check_text]
        else:
            check_text = response_text.lower()
            missing = [t for t in texts if t.lower() not in check_text]

        passed = len(missing) == 0

        return BehaviorResult(
            behavior_type="contains_text",
            passed=passed,
            message=f"Missing texts: {missing}" if missing else "All texts found",
            expected=texts,
            actual=missing if missing else "all found",
        )

    def _validate_contains_any(
        self,
        behavior: ExpectedBehavior,
        response_text: str,
        tool_calls: List[str],
        flow_state: str,
    ) -> BehaviorResult:
        """Validate that response contains ANY of the specified texts."""
        texts = behavior.text or []

        if behavior.case_sensitive:
            check_text = response_text
            found = [t for t in texts if t in check_text]
        else:
            check_text = response_text.lower()
            found = [t for t in texts if t.lower() in check_text]

        passed = len(found) > 0

        return BehaviorResult(
            behavior_type="contains_any",
            passed=passed,
            message=f"Found: {found}" if found else "None of the texts found",
            expected=f"any of {texts}",
            actual=found if found else "none",
        )

    def _validate_not_contains(
        self,
        behavior: ExpectedBehavior,
        response_text: str,
        tool_calls: List[str],
        flow_state: str,
    ) -> BehaviorResult:
        """Validate that response does NOT contain specified texts."""
        texts = behavior.text or []

        if behavior.case_sensitive:
            check_text = response_text
            found = [t for t in texts if t in check_text]
        else:
            check_text = response_text.lower()
            found = [t for t in texts if t.lower() in check_text]

        passed = len(found) == 0

        return BehaviorResult(
            behavior_type="not_contains",
            passed=passed,
            message=f"Unexpectedly found: {found}" if found else "Good: none found",
            expected=f"none of {texts}",
            actual=found if found else "none",
        )

    def _validate_regex_match(
        self,
        behavior: ExpectedBehavior,
        response_text: str,
        tool_calls: List[str],
        flow_state: str,
    ) -> BehaviorResult:
        """Validate that response matches a regex pattern."""
        pattern = behavior.pattern or ""

        try:
            flags = 0 if behavior.case_sensitive else re.IGNORECASE
            match = re.search(pattern, response_text, flags)
            passed = match is not None
        except re.error as e:
            return BehaviorResult(
                behavior_type="regex_match",
                passed=False,
                message=f"Invalid regex: {e}",
                expected=pattern,
            )

        return BehaviorResult(
            behavior_type="regex_match",
            passed=passed,
            message=f"Pattern {'matched' if passed else 'did not match'}",
            expected=pattern,
            actual=match.group() if match else None,
        )

    def _validate_flow_state(
        self,
        behavior: ExpectedBehavior,
        response_text: str,
        tool_calls: List[str],
        flow_state: str,
    ) -> BehaviorResult:
        """Validate the current flow state."""
        expected_state = behavior.text[0] if behavior.text else None

        passed = flow_state == expected_state

        return BehaviorResult(
            behavior_type="flow_state",
            passed=passed,
            message=f"Flow state: {flow_state}" + (
                "" if passed else f", expected: {expected_state}"
            ),
            expected=expected_state,
            actual=flow_state,
        )
