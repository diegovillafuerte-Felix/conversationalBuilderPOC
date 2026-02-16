"""Doc freshness tests.

Verifies that key documentation files and referenced directories exist.
Catches stale references when the codebase structure changes.
"""

from pathlib import Path

import pytest

# Project root (3 levels up from this test file)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


class TestDocFreshness:
    """Verify documentation files exist and reference valid paths."""

    def test_claude_md_exists(self):
        """CLAUDE.md must exist at project root."""
        assert (PROJECT_ROOT / "CLAUDE.md").exists(), "CLAUDE.md not found at project root"

    def test_docs_directory_exists(self):
        """docs/ directory must exist."""
        assert (PROJECT_ROOT / "docs").is_dir(), "docs/ directory not found"

    def test_expected_docs_exist(self):
        """All expected documentation files should exist."""
        expected_docs = [
            "docs/ARCHITECTURE.md",
            "docs/conventions.md",
            "docs/development-workflow.md",
            "docs/current-state.md",
            "docs/design-decisions.md",
        ]
        missing = [doc for doc in expected_docs if not (PROJECT_ROOT / doc).exists()]
        if missing:
            pytest.fail("Missing documentation files:\n" + "\n".join(f"  {m}" for m in missing))

    def test_all_agent_configs_exist(self):
        """All 6 expected agent config files should exist."""
        agents_dir = PROJECT_ROOT / "backend" / "app" / "config" / "agents"
        expected_agents = ["felix.json", "remittances.json", "snpl.json", "topups.json", "billpay.json", "wallet.json"]
        missing = [a for a in expected_agents if not (agents_dir / a).exists()]
        if missing:
            pytest.fail("Missing agent configs:\n" + "\n".join(f"  {m}" for m in missing))

    def test_key_directories_exist(self):
        """Key directories referenced in documentation should exist."""
        expected_dirs = [
            "backend/app/core",
            "backend/app/clients",
            "backend/app/models",
            "backend/app/routes",
            "backend/app/schemas",
            "backend/app/config/agents",
            "backend/app/config/prompts",
            "backend/tests/unit",
            "backend/tests/e2e",
            "services/app/routers",
            "services/app/services",
            "services/app/schemas",
            "frontend/react-app",
        ]
        missing = [d for d in expected_dirs if not (PROJECT_ROOT / d).is_dir()]
        if missing:
            pytest.fail("Missing directories:\n" + "\n".join(f"  {m}" for m in missing))

    def test_makefile_exists(self):
        """Makefile should exist at project root."""
        assert (PROJECT_ROOT / "Makefile").exists(), "Makefile not found at project root"

    def test_ci_workflow_exists(self):
        """GitHub Actions CI workflow should exist."""
        assert (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").exists(), "CI workflow not found"
