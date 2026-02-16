"""Architecture enforcement tests.

Uses AST parsing to verify import boundaries between layers.
These tests ensure the layered architecture is maintained as the codebase grows.
"""

import ast
from pathlib import Path

import pytest

# Root of the backend app
APP_DIR = Path(__file__).parent.parent.parent / "app"

# Define allowed imports for each layer.
# Keys are directory names relative to app/, values are allowed app.* import prefixes.
LAYER_RULES = {
    "routes": {"core", "schemas", "models", "database", "auth", "config"},
    "clients": {"config", "clients"},
    "models": {"database", "models"},
    "schemas": set(),  # schemas should not import other app modules
    "seed": {"models", "database", "config"},
}


def _get_app_imports(filepath: Path) -> list[tuple[str, int]]:
    """Extract all app.* imports from a Python file using AST parsing.

    Returns list of (module_path, line_number) tuples.
    """
    try:
        source = filepath.read_text()
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("app."):
                    imports.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("app."):
                imports.append((node.module, node.lineno))
    return imports


def _get_layer(module_path: str) -> str:
    """Extract the layer name from an app.* import path.

    e.g. 'app.core.orchestrator' -> 'core'
         'app.models.session' -> 'models'
         'app.database' -> 'database'
    """
    parts = module_path.split(".")
    if len(parts) >= 2:
        return parts[1]
    return ""


def _collect_violations() -> list[str]:
    """Scan all Python files in layer directories and find import violations."""
    violations = []

    for layer_name, allowed_targets in LAYER_RULES.items():
        layer_dir = APP_DIR / layer_name
        if not layer_dir.exists():
            continue

        for py_file in layer_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue

            rel_path = py_file.relative_to(APP_DIR.parent)
            app_imports = _get_app_imports(py_file)

            for module_path, lineno in app_imports:
                target_layer = _get_layer(module_path)

                if target_layer not in allowed_targets:
                    violations.append(
                        f"{rel_path}:{lineno} — {layer_name}/ imports app.{target_layer} "
                        f"(allowed: {sorted(allowed_targets) if allowed_targets else 'none'})"
                    )

    return violations


class TestArchitectureBoundaries:
    """Verify that import boundaries between layers are respected."""

    def test_no_import_violations(self):
        """Each layer should only import from its allowed dependencies."""
        violations = _collect_violations()
        if violations:
            msg = "Architecture import violations found:\n" + "\n".join(f"  {v}" for v in violations)
            pytest.fail(msg)

    def test_layer_directories_exist(self):
        """Verify that all layer directories we're testing actually exist."""
        for layer_name in LAYER_RULES:
            layer_dir = APP_DIR / layer_name
            assert layer_dir.exists(), f"Layer directory app/{layer_name}/ does not exist"

    def test_schemas_has_no_app_imports(self):
        """Schemas should be pure data definitions with no internal imports."""
        schemas_dir = APP_DIR / "schemas"
        if not schemas_dir.exists():
            pytest.skip("schemas/ directory not found")

        all_imports = []
        for py_file in schemas_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
            imports = _get_app_imports(py_file)
            all_imports.extend((py_file.relative_to(APP_DIR.parent), m, ln) for m, ln in imports)

        if all_imports:
            lines = [f"  {f}:{ln} imports {m}" for f, m, ln in all_imports]
            pytest.fail("schemas/ should not import other app modules:\n" + "\n".join(lines))
