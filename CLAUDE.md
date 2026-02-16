# Conversational Orchestrator Service (COS) - Codebase Overview

---
## Instructions for Claude

This file provides structural context for the codebase.

**IMPORTANT:** After completing any task that:
- Adds, removes, or renames files/folders
- Creates new modules or components
- Changes how modules interact
- Modifies the architecture

Update this CLAUDE.md to reflect those changes before finishing the task.

---

## Project Overview

COS is a multi-agent conversational AI system for financial services (remittances, credit, top-ups, bill payments, wallet) through natural language. Hierarchical agent architecture where a main orchestrator routes to specialized product agents, each with tools, subflows, and response templates.

## Architecture

1. **API Layer** (`backend/routes/`) — FastAPI endpoints
2. **Orchestration Layer** (`backend/core/`) — Conversation flow, LLM interaction
3. **Configuration Layer** (`backend/core/`) — In-memory `AgentRegistry` from JSON configs
4. **Data Layer** (`backend/models/`) — SQLAlchemy ORM (sessions, messages, users)
5. **Services Gateway** (`services/`) — Independent mock backend services via REST API
6. **JSON Configs** (`backend/config/`) — Source of truth for agent definitions

## Directory Structure

```
conversationalBuilderPOC/
├── backend/
│   ├── app/
│   │   ├── core/              # Orchestration engine
│   │   ├── clients/           # HTTP clients for services gateway
│   │   ├── models/            # SQLAlchemy ORM models
│   │   ├── routes/            # FastAPI routers (chat.py, admin.py)
│   │   ├── schemas/           # Pydantic request/response models
│   │   ├── config/agents/     # Agent JSON configs (6 agents)
│   │   ├── config/prompts/    # System prompt templates
│   │   ├── seed/              # Database seeders
│   │   └── main.py            # FastAPI entry point
│   └── tests/
│       ├── unit/              # Unit + architecture + convention tests
│       ├── integration/       # API endpoint tests
│       ├── conversational/    # LLM-based scenario tests
│       └── e2e/               # E2E conversation tests (live servers)
├── services/
│   └── app/
│       ├── routers/           # REST API routers (7 modules)
│       ├── services/          # Mock service implementations
│       └── schemas/           # API models
├── frontend/react-app/        # React UI (chat + admin + visualization)
├── docs/                      # Detailed documentation
├── Makefile                   # Build/test/lint commands
├── .github/workflows/ci.yml   # CI pipeline
└── docker-compose.yml
```

## Key Entry Points

| Flow | Entry Point |
|------|-------------|
| Chat API | `backend/app/routes/chat.py` → POST `/api/chat/message` |
| Message handling | `backend/app/core/orchestrator.py:handle_message()` |
| Backend startup | `backend/app/main.py` |
| Admin API | `backend/app/routes/admin.py` |
| Services Gateway | `services/app/main.py` (port 8001) |
| Frontend | `frontend/react-app/` |

## Module Relationships

```
User Request
     │
     ▼
[routes/chat.py] ──► [Orchestrator] (Routing Chain Flow)
                           │
                    PHASE 1: SETUP
                           ├──► [StateManager] (load/create session, get agent)
                           │
                    PHASE 2: ROUTING CHAIN (iterate until stable)
                           ├──► [ContextAssembler] (builds prompt)
                           ├──► [LLMClient] (call model)
                           ├──► [RoutingHandler] ──► [AgentRegistry] (routing)
                           ├──► [ToolExecutor] ──► [ServiceClient] ──► Services Gateway
                           └──► Loop until stable state (no routing)
```

## Documentation Index

| Document | Contents |
|----------|----------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Deep-dive architecture guide |
| [docs/design-decisions.md](docs/design-decisions.md) | Architectural rationale (why no recursion, why raw-data services, etc.) |
| [docs/conventions.md](docs/conventions.md) | Tool naming, service rules, i18n, model patterns |
| [docs/current-state.md](docs/current-state.md) | Implemented features, agent details, routing, services gateway |
| [docs/development-workflow.md](docs/development-workflow.md) | Autonomous workflow, test commands, E2E costs |

## Quick Reference

- **Tool naming**: `verb_noun` (e.g., `get_exchange_rate`). Navigation: `enter_<agent>`, `go_home`, `up_one_level`
- **Service rule**: Services return raw data ONLY. No `_message` fields. LLM handles formatting.
- **i18n**: All configs in English. LLM responds in user's language via directive injection.
- **Routing**: Explicit via `routing` field in ToolConfig. Validated at startup.
- **State transitions**: Declarative via `transitions` list in SubflowStateConfig. First match wins.

## Running Tests

```bash
make check              # All checks (lint + typecheck + unit + services)
make lint               # Lint both backend and services
make test-unit          # Backend unit tests
make test-services      # Services gateway tests
make test-e2e-smoke     # Smoke E2E tests (~$0.03)
make test-e2e           # Full E2E tests (~$0.13, requires live servers)
```
