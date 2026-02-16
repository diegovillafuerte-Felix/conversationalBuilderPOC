.PHONY: check lint lint-fix format format-check typecheck test-unit test-services test-e2e test-e2e-smoke install

VENV := backend/venv/bin
RUFF := $(VENV)/ruff
MYPY := $(VENV)/mypy
PYTHON := $(VENV)/python

# Run all checks (lint + typecheck + tests)
check: lint format-check typecheck test-unit test-services

# Lint both backend and services
lint:
	$(RUFF) check backend/app/ backend/tests/ --config backend/pyproject.toml
	$(RUFF) check services/app/ services/tests/ --config services/pyproject.toml

# Lint and auto-fix
lint-fix:
	$(RUFF) check --fix backend/app/ backend/tests/ --config backend/pyproject.toml
	$(RUFF) check --fix services/app/ services/tests/ --config services/pyproject.toml

# Format both backend and services
format:
	$(RUFF) format backend/app/ backend/tests/ --config backend/pyproject.toml
	$(RUFF) format services/app/ services/tests/ --config services/pyproject.toml

# Check formatting without changing files
format-check:
	$(RUFF) format --check backend/app/ backend/tests/ --config backend/pyproject.toml
	$(RUFF) format --check services/app/ services/tests/ --config services/pyproject.toml

# Type checking
typecheck:
	cd backend && ../$(MYPY) app/ --config-file pyproject.toml

# Backend unit tests
test-unit:
	cd backend && ../$(PYTHON) -m pytest tests/unit -v

# Services gateway tests
test-services:
	cd services && ../$(PYTHON) -m pytest tests/ -v

# E2E tests (requires live servers on ports 8000/8001)
test-e2e:
	cd backend && ../$(PYTHON) -m tests.e2e.run_conversations

# E2E smoke tests only
test-e2e-smoke:
	cd backend && ../$(PYTHON) -m tests.e2e.run_conversations --smoke

# Install all dependencies into backend venv
install:
	$(VENV)/pip install -r backend/requirements.txt
	$(VENV)/pip install -r services/requirements.txt
