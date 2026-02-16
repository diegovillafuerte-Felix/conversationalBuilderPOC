"""Convention enforcement tests.

Verifies naming conventions, required config fields, and service layer rules.
"""

import json
import re
from pathlib import Path

import pytest

# Paths
CONFIG_DIR = Path(__file__).parent.parent.parent / "app" / "config" / "agents"
SERVICES_DIR = Path(__file__).parent.parent.parent.parent / "services" / "app" / "services"

# Tool naming: verb_noun pattern (allows verb_noun_qualifier too)
TOOL_NAME_PATTERN = re.compile(r"^[a-z]+(_[a-z]+)+$")

# Allowed verb prefixes for tools
ALLOWED_VERBS = {
    "get",
    "list",
    "create",
    "update",
    "delete",
    "send",
    "cancel",
    "calculate",
    "detect",
    "validate",
    "check",
    "pay",
    "save",
    "link",
    "make",
    "submit",
    "add",
    "start",  # start_flow_*
    "enter",  # enter_*
    "up",  # up_one_level
    "go",  # go_home
    "escalate",  # escalate_to_human
    "set",
    "change",
}


def _load_all_agent_configs() -> list[tuple[str, dict]]:
    """Load all agent JSON configs. Returns list of (filename, config) tuples."""
    configs = []
    if not CONFIG_DIR.exists():
        return configs
    for json_file in sorted(CONFIG_DIR.glob("*.json")):
        with open(json_file) as f:
            configs.append((json_file.stem, json.load(f)))
    return configs


class TestToolNamingConventions:
    """Verify tool names follow verb_noun convention."""

    @pytest.fixture(scope="class")
    def all_tools(self) -> list[tuple[str, dict]]:
        """Collect all tools from all agent configs."""
        tools = []
        for agent_id, config in _load_all_agent_configs():
            for tool in config.get("tools", []):
                tools.append((agent_id, tool))
        return tools

    def test_tools_exist(self, all_tools):
        """At least some tools should be defined."""
        assert len(all_tools) > 0, "No tools found in any agent config"

    def test_tool_names_match_pattern(self, all_tools):
        """All tool names should match verb_noun pattern."""
        violations = []
        for agent_id, tool in all_tools:
            name = tool.get("name", "")
            if not TOOL_NAME_PATTERN.match(name):
                violations.append(f"  {agent_id}: '{name}' doesn't match verb_noun pattern")

        if violations:
            pytest.fail("Tool naming violations:\n" + "\n".join(violations))

    def test_tool_names_use_allowed_verbs(self, all_tools):
        """Tool name verbs should be from the allowed list."""
        violations = []
        for agent_id, tool in all_tools:
            name = tool.get("name", "")
            verb = name.split("_")[0] if "_" in name else name
            if verb not in ALLOWED_VERBS:
                violations.append(f"  {agent_id}: '{name}' uses verb '{verb}' (not in allowed list)")

        if violations:
            pytest.fail("Unknown tool verbs:\n" + "\n".join(violations))


class TestAgentConfigValidity:
    """Verify required fields in agent configs."""

    @pytest.fixture(scope="class")
    def configs(self) -> list[tuple[str, dict]]:
        return _load_all_agent_configs()

    def test_configs_exist(self, configs):
        """At least some agent configs should exist."""
        assert len(configs) > 0, "No agent configs found"

    def test_required_agent_fields(self, configs):
        """Each agent config must have id, name, description, tools."""
        required = {"id", "name", "description", "tools"}
        violations = []
        for agent_id, config in configs:
            missing = required - set(config.keys())
            if missing:
                violations.append(f"  {agent_id}: missing {sorted(missing)}")

        if violations:
            pytest.fail("Agent configs missing required fields:\n" + "\n".join(violations))

    def test_required_tool_fields(self, configs):
        """Each tool must have name and description."""
        violations = []
        for agent_id, config in configs:
            for i, tool in enumerate(config.get("tools", [])):
                missing = []
                if "name" not in tool:
                    missing.append("name")
                if "description" not in tool:
                    missing.append("description")
                if missing:
                    violations.append(f"  {agent_id} tool #{i}: missing {missing}")

        if violations:
            pytest.fail("Tools missing required fields:\n" + "\n".join(violations))

    def test_routing_targets_exist(self, configs):
        """Routing targets in tools should reference existing agents or subflows."""
        # Build set of all known agent IDs and subflow IDs
        agent_ids = {config.get("id") for _, config in configs}
        subflow_ids = set()
        for _, config in configs:
            for subflow in config.get("subflows", []):
                subflow_ids.add(subflow.get("id"))

        violations = []
        for agent_id, config in configs:
            for tool in config.get("tools", []):
                routing = tool.get("routing")
                if not routing:
                    continue

                action = routing.get("action")
                target = routing.get("target")

                if action == "enter_agent" and target and target not in agent_ids:
                    violations.append(f"  {agent_id}/{tool['name']}: routes to unknown agent '{target}'")

                if action == "start_flow" and target:
                    if target not in subflow_ids:
                        violations.append(f"  {agent_id}/{tool['name']}: routes to unknown subflow '{target}'")

        if violations:
            pytest.fail("Routing targets not found:\n" + "\n".join(violations))


class TestServiceConventions:
    """Verify service layer follows raw-data-only convention."""

    def test_no_message_fields_in_services(self):
        """Service methods should not return _message fields (formatting is presentation layer's job)."""
        if not SERVICES_DIR.exists():
            pytest.skip("services/ directory not found")

        violations = []
        for py_file in sorted(SERVICES_DIR.glob("*.py")):
            if py_file.name == "__init__.py":
                continue

            source = py_file.read_text()
            for i, line in enumerate(source.splitlines(), 1):
                # Look for _message being set in return dicts
                if '"_message"' in line or "'_message'" in line:
                    # Skip comments
                    stripped = line.lstrip()
                    if stripped.startswith("#"):
                        continue
                    violations.append(f"  {py_file.name}:{i}: {stripped.strip()}")

        if violations:
            pytest.fail(
                "Services should not return _message fields (formatting belongs in presentation layer):\n"
                + "\n".join(violations)
            )
