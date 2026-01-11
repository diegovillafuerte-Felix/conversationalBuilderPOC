# Felix Conversational Orchestrator - Codebase Overview

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

Felix is a multi-agent conversational AI system for handling financial services (remittances, credit, top-ups, bill payments, wallet) through natural language. It uses a hierarchical agent architecture where a main orchestrator routes conversations to specialized product agents, each with their own tools, subflows, and response templates. The system supports stateful multi-step flows, confirmation handling, and escalation to human agents.

## Architecture

The system follows a **layered architecture** with clear separation of concerns:

1. **API Layer** (`routes/`) - FastAPI endpoints handling HTTP requests
2. **Orchestration Layer** (`core/`) - Conversation flow management and LLM interaction
3. **Data Layer** (`models/`) - SQLAlchemy ORM models with PostgreSQL
4. **Service Layer** (`services/`) - Mock backend integrations for each product vertical
5. **Configuration Layer** (`config/`) - JSON-based agent/tool/prompt configurations

**Key patterns:**
- **Agent hierarchy**: Root orchestrator with child product agents
- **State machine flows**: Multi-step processes with defined states and transitions
- **Tool-based actions**: Agents invoke tools that map to backend services
- **Context assembly**: Dynamic prompt construction based on user, session, and agent state

## Directory Structure

```
conversationalBuilderPOC/
├── backend/
│   ├── app/
│   │   ├── core/              # Orchestration engine
│   │   │   ├── orchestrator.py      # Main conversation handler
│   │   │   ├── context_assembler.py # Builds LLM prompts
│   │   │   ├── state_manager.py     # Session/flow state
│   │   │   ├── tool_executor.py     # Runs tools, calls services
│   │   │   ├── llm_client.py        # Anthropic API wrapper
│   │   │   ├── history_compactor.py # Conversation summarization
│   │   │   ├── config_loader.py     # Loads JSON configs
│   │   │   ├── i18n.py              # Localization
│   │   │   └── template_renderer.py # Response templating
│   │   ├── models/            # SQLAlchemy ORM models
│   │   │   ├── agent.py       # Agent, Tool, ResponseTemplate
│   │   │   ├── session.py     # ConversationSession
│   │   │   ├── conversation.py # ConversationMessage
│   │   │   ├── subflow.py     # Subflow, SubflowState
│   │   │   └── user.py        # UserContext
│   │   ├── routes/            # FastAPI routers
│   │   │   ├── chat.py        # Chat API endpoints
│   │   │   └── admin.py       # Admin CRUD endpoints
│   │   ├── schemas/           # Pydantic request/response models
│   │   ├── services/          # Mock product backends
│   │   │   ├── remittances.py
│   │   │   ├── topups.py
│   │   │   ├── billpay.py
│   │   │   ├── credit.py
│   │   │   └── wallet.py
│   │   ├── config/            # JSON configurations
│   │   │   ├── agents/        # Agent definitions (felix, remittances, etc.)
│   │   │   ├── prompts/       # System prompt templates
│   │   │   ├── messages/      # Service response messages
│   │   │   └── sample_data/   # Sample data for seeding (users.json)
│   │   ├── seed/              # Database seeders
│   │   └── main.py            # FastAPI app entry point
│   └── requirements.txt
├── frontend/
│   ├── chat/                  # Simple vanilla JS chat UI
│   ├── admin/                 # Simple vanilla JS admin UI
│   └── react-app/             # React-based UI (in development)
│       └── src/
│           ├── components/    # Chat and Admin components
│           ├── pages/         # ChatPage, AdminPage
│           ├── services/      # API clients
│           ├── store/         # Zustand state management
│           └── styles/        # CSS files
└── docker-compose.yml         # PostgreSQL + Redis + Backend
```

## Key Entry Points

| Flow | Entry Point | Description |
|------|-------------|-------------|
| Chat API | `backend/app/routes/chat.py` | POST `/api/chat/message` |
| Message handling | `backend/app/core/orchestrator.py:handle_message()` | Main conversation loop |
| App startup | `backend/app/main.py` | FastAPI lifespan, seeding |
| Admin API | `backend/app/routes/admin.py` | Agent/Tool CRUD |
| Frontend chat | `frontend/chat/index.html` or `frontend/react-app/` | User interfaces |

## Module Relationships

```
User Request
     │
     ▼
[routes/chat.py] ──► [Orchestrator] ──► [LLMClient] ──► Anthropic API
                           │
                           ├──► [ContextAssembler] (builds prompt from session + agent + user)
                           │
                           ├──► [StateManager] (manages session, agent stack, flows)
                           │
                           └──► [ToolExecutor] ──► [services/*] (mock backends)
```

**Data flow:**
1. Request arrives at `routes/chat.py`
2. `Orchestrator` loads session via `StateManager`
3. `ContextAssembler` builds system prompt + messages from agent config, user context, history
4. `LLMClient` calls Claude API with assembled context
5. `ToolExecutor` processes any tool calls, invoking appropriate `services/`
6. Response returned with updated session state

## Conventions

- **Agent configs**: JSON files in `config/agents/` define tools, prompts, navigation
- **Tool naming**: `verb_noun` format (e.g., `get_exchange_rate`, `create_transfer`)
- **Navigation tools**: `enter_<agent>`, `up_one_level`, `go_home`, `escalate_to_human`
- **Flow tools**: `start_flow_<flowname>` triggers stateful subflows
- **Service methods**: Return dicts with `_message` key for display text
- **i18n**: Service messages stored in `config/messages/services.json`
- **Models**: Use GUID primary keys, JSON columns for flexible configs
- **Frontend state**: Zustand stores in `react-app/src/store/`
- **Sample data**: Sample users defined in `config/sample_data/users.json`, seeded at startup if not present

## Current State

**Implemented:** Multi-agent orchestration, all product agents (remittances, credit, topups, billpay, wallet), tool execution with mock backends, stateful subflows, confirmation handling, history compaction, debug panel, i18n (es/en), vanilla JS + React UIs, admin CRUD API.

**Planned:** Visual flow editor, analytics dashboard, WhatsApp integration, real backend services, auth, rate limiting.

## Running Tests

The project uses pytest with a virtual environment in `backend/venv/`.

```bash
# Run all tests
cd backend && ./venv/bin/python -m pytest tests/ -v

# Unit tests only
./venv/bin/python -m pytest tests/unit -v

# Integration tests
./venv/bin/python -m pytest tests/integration -v -m integration

# Conversational scenario tests (requires seeded database)
./venv/bin/python -m pytest tests/conversational -v -m conversational

# With coverage report
./venv/bin/python -m pytest --cov=app --cov-report=html

# Skip slow/conversational tests
./venv/bin/python -m pytest tests/ -v -m "not slow and not conversational"
```

**Test Structure:**
- `tests/unit/core/` - State manager, tool executor tests
- `tests/unit/services/` - Mock service tests (topups, etc.)
- `tests/integration/` - API endpoint tests
- `tests/conversational/` - LLM-based scenario tests defined in agent JSON configs (`test_scenarios` field)
