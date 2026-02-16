# Development Workflow

## Autonomous Operation

Claude Code operates as the engineering team. The human PM provides requirements and answers product questions.

### After every code change:
1. `make test-unit` — must pass
2. `make test-services` — must pass
3. `make lint` — must pass
4. For orchestration/routing changes: `make test-e2e` — run live conversations
5. Read `tests/e2e/results/*.txt` — assess quality of responses
6. Fix issues, repeat

### Consult the PM for:
- New feature requirements / scope changes
- Product direction and prioritization
- UX decisions (how should X behave?)
- Architecture tradeoffs that affect product

### Do NOT consult the PM for:
- Test results, logs, debugging
- Implementation details
- "Does the system still work?" — run the tests
- Mechanical tasks (server management, DB issues, config loading)

## E2E Test Cost
- Smoke (~$0.03): 3 scenarios, 1 turn each
- Full (~$0.13): 5 scenarios, 10 turns total
- Run full suite after significant orchestration/routing/agent changes

## Running Tests

```bash
# All checks (lint + typecheck + unit + services)
make check

# Individual targets
make lint           # Lint both backend and services
make lint-fix       # Auto-fix lint issues
make format         # Format code
make typecheck      # Run mypy on backend
make test-unit      # Backend unit tests
make test-services  # Services gateway tests
make test-e2e       # E2E tests (requires live servers)
make test-e2e-smoke # Smoke E2E tests only

# Direct pytest usage
cd backend && ./venv/bin/python -m pytest tests/unit -v
cd backend && ./venv/bin/python -m pytest tests/integration -v -m integration
cd backend && ./venv/bin/python -m pytest tests/conversational -v -m conversational
cd services && ../backend/venv/bin/python -m pytest tests/ -v
```

## Test Structure
- `backend/tests/unit/` — Unit tests (state manager, tool executor, architecture, conventions)
- `backend/tests/unit/core/` — Core module unit tests
- `backend/tests/integration/` — API endpoint tests
- `backend/tests/conversational/` — LLM-based scenario tests
- `backend/tests/e2e/` — E2E conversation tests against live servers
- `services/tests/` — Services gateway endpoint tests
