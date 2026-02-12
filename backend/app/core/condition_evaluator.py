"""Safe condition evaluator for declarative flow transitions."""

from __future__ import annotations

import ast
import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


_CAMEL_BOUNDARY = re.compile(r"(?<!^)(?=[A-Z])")


def camel_to_snake(value: str) -> str:
    """Convert camelCase/PascalCase to snake_case."""
    return _CAMEL_BOUNDARY.sub("_", value).lower()


def snake_to_camel(value: str) -> str:
    """Convert snake_case to camelCase."""
    parts = value.split("_")
    if not parts:
        return value
    return parts[0] + "".join(p[:1].upper() + p[1:] for p in parts[1:])


@dataclass(frozen=True)
class MissingValue:
    """Represents a missing reference while evaluating an expression."""

    path: str


class ConditionEvaluator:
    """Evaluate condition strings using a restricted Python expression AST."""

    _ALLOWED_COMPARE_OPS = (
        ast.Eq,
        ast.NotEq,
        ast.Gt,
        ast.GtE,
        ast.Lt,
        ast.LtE,
        ast.In,
        ast.NotIn,
        ast.Is,
        ast.IsNot,
    )

    _LITERAL_NAMES = {
        "true": True,
        "false": False,
        "null": None,
        "none": None,
    }

    def evaluate(self, condition: str, context: dict[str, Any]) -> bool:
        """Evaluate a condition against context. Returns False on parse/eval errors."""
        if not isinstance(condition, str):
            return False

        condition = condition.strip()
        if not condition:
            return False

        try:
            tree = ast.parse(condition, mode="eval")
            result = self._eval_node(tree.body, context, context)
            return self._truthy(result)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to evaluate condition '%s': %s", condition, exc)
            return False

    def _eval_node(self, node: ast.AST, root: dict[str, Any], scope: Any) -> Any:
        if isinstance(node, ast.BoolOp):
            values = [self._eval_node(v, root, scope) for v in node.values]
            if isinstance(node.op, ast.And):
                return all(self._truthy(v) for v in values)
            if isinstance(node.op, ast.Or):
                return any(self._truthy(v) for v in values)
            raise ValueError(f"Unsupported boolean operator: {type(node.op).__name__}")

        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.Not):
                return not self._truthy(self._eval_node(node.operand, root, scope))
            raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")

        if isinstance(node, ast.Compare):
            return self._eval_compare(node, root, scope)

        if isinstance(node, ast.Name):
            identifier = node.id
            lower_name = identifier.lower()
            if lower_name in self._LITERAL_NAMES:
                return self._LITERAL_NAMES[lower_name]
            if identifier in ("context", "stateData"):
                return root
            value, found = resolve_path(root, identifier)
            return value if found else MissingValue(identifier)

        if isinstance(node, ast.Attribute):
            base = self._eval_node(node.value, root, scope)
            if isinstance(base, MissingValue):
                candidate = f"{base.path}.{node.attr}"
                value, found = resolve_path(root, candidate)
                return value if found else MissingValue(candidate)

            value, found = resolve_path(base, node.attr)
            if found:
                return value
            return MissingValue(node.attr)

        if isinstance(node, ast.Subscript):
            container = self._eval_node(node.value, root, scope)
            key = self._eval_node(node.slice, root, scope)
            if isinstance(container, MissingValue):
                return container
            if isinstance(key, MissingValue):
                return key
            try:
                if isinstance(container, dict):
                    return container.get(key, MissingValue(str(key)))
                return container[key]
            except Exception:  # noqa: BLE001
                return MissingValue(str(key))

        if isinstance(node, ast.Constant):
            return node.value

        if isinstance(node, ast.List):
            return [self._eval_node(el, root, scope) for el in node.elts]

        if isinstance(node, ast.Tuple):
            return tuple(self._eval_node(el, root, scope) for el in node.elts)

        if isinstance(node, ast.Dict):
            keys = [self._eval_node(k, root, scope) for k in node.keys]
            values = [self._eval_node(v, root, scope) for v in node.values]
            return dict(zip(keys, values))

        raise ValueError(f"Unsupported AST node: {type(node).__name__}")

    def _eval_compare(self, node: ast.Compare, root: dict[str, Any], scope: Any) -> bool:
        left = self._eval_node(node.left, root, scope)
        current_left = left

        for op, comparator_node in zip(node.ops, node.comparators):
            if not isinstance(op, self._ALLOWED_COMPARE_OPS):
                raise ValueError(f"Unsupported comparison operator: {type(op).__name__}")

            right = self._eval_node(comparator_node, root, scope)
            passed = self._compare_values(current_left, right, op, root)
            if not passed:
                return False
            current_left = right

        return True

    def _compare_values(self, left: Any, right: Any, op: ast.AST, root: dict[str, Any]) -> bool:
        # Special handling for `key in stateData/context` when key is an unresolved name.
        if isinstance(op, (ast.In, ast.NotIn)) and isinstance(right, dict):
            if isinstance(left, MissingValue):
                contains = contains_key(right, left.path)
                return contains if isinstance(op, ast.In) else not contains

        left_value = None if isinstance(left, MissingValue) else left
        right_value = None if isinstance(right, MissingValue) else right

        try:
            if isinstance(op, ast.Eq):
                return left_value == right_value
            if isinstance(op, ast.NotEq):
                return left_value != right_value
            if isinstance(op, ast.Gt):
                return left_value > right_value
            if isinstance(op, ast.GtE):
                return left_value >= right_value
            if isinstance(op, ast.Lt):
                return left_value < right_value
            if isinstance(op, ast.LtE):
                return left_value <= right_value
            if isinstance(op, ast.In):
                return left_value in right_value
            if isinstance(op, ast.NotIn):
                return left_value not in right_value
            if isinstance(op, ast.Is):
                return left_value is right_value
            if isinstance(op, ast.IsNot):
                return left_value is not right_value
        except Exception:  # noqa: BLE001
            return False

        return False

    @staticmethod
    def _truthy(value: Any) -> bool:
        if isinstance(value, MissingValue):
            return False
        return bool(value)


def resolve_path(data: Any, path: str) -> tuple[Any, bool]:
    """Resolve dotted-path lookups with snake_case/camelCase fallback."""
    if not path:
        return None, False

    current = data
    for raw_part in path.split("."):
        if isinstance(current, MissingValue):
            return current, False

        if isinstance(current, dict):
            key, found = resolve_key(current, raw_part)
            if not found:
                return None, False
            current = current[key]
            continue

        # Support attribute access for non-dict values.
        if hasattr(current, raw_part):
            current = getattr(current, raw_part)
            continue

        return None, False

    return current, True


def resolve_key(mapping: dict[str, Any], key: str) -> tuple[str, bool]:
    """Resolve a key with exact, snake_case, camelCase, and normalized fallback."""
    if key in mapping:
        return key, True

    candidates = [
        camel_to_snake(key),
        snake_to_camel(key),
        key.lower(),
    ]

    normalized_target = key.replace("_", "").lower()
    for candidate in candidates:
        if candidate in mapping:
            return candidate, True

    for existing_key in mapping:
        if existing_key.replace("_", "").lower() == normalized_target:
            return existing_key, True

    return key, False


def contains_key(mapping: dict[str, Any], key: str) -> bool:
    """Check membership with key normalization fallback."""
    _, found = resolve_key(mapping, key)
    return found


_evaluator = ConditionEvaluator()


def evaluate_condition(condition: str, context: dict[str, Any]) -> bool:
    """Convenience function for evaluating transition conditions."""
    return _evaluator.evaluate(condition, context)

