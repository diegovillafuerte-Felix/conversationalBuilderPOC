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

1. **API Layer** (`backend/routes/`) - FastAPI endpoints handling HTTP requests
2. **Orchestration Layer** (`backend/core/`) - Conversation flow management and LLM interaction
3. **Data Layer** (`backend/models/`) - SQLAlchemy ORM models with PostgreSQL
4. **Services Gateway** (`services/`) - **Independently deployable** mock backend services via REST API
5. **Configuration Layer** (`backend/config/`) - JSON-based agent/tool/prompt configurations

**Key patterns:**
- **Agent hierarchy**: Root orchestrator with child product agents
- **State machine flows**: Multi-step processes with defined states and transitions
- **Tool-based actions**: Agents invoke tools that call services via HTTP
- **Explicit routing**: Validated routing system with startup checks (no string parsing inference)
- **Context assembly**: Dynamic prompt construction based on user, session, and agent state
- **Shadow service**: Parallel evaluation system for contextual tips and promotions
- **Service separation**: Services deployed independently, communicate via REST API

## Directory Structure

```
conversationalBuilderPOC/
├── backend/                   # Core orchestration platform
│   ├── app/
│   │   ├── core/              # Orchestration engine
│   │   │   ├── orchestrator.py      # Main conversation handler
│   │   │   ├── context_assembler.py # Builds LLM prompts
│   │   │   ├── state_manager.py     # Session/flow state
│   │   │   ├── tool_executor.py     # Runs tools via HTTP to services gateway
│   │   │   ├── routing.py           # Routing types and data classes
│   │   │   ├── routing_registry.py  # Startup validation and routing cache
│   │   │   ├── routing_handler.py   # Unified routing execution
│   │   │   ├── llm_client.py        # OpenAI API wrapper
│   │   │   ├── history_compactor.py # Conversation summarization
│   │   │   ├── config_loader.py     # Loads JSON configs
│   │   │   ├── i18n.py              # Localization
│   │   │   ├── template_renderer.py # Response templating
│   │   │   ├── shadow_service.py    # Shadow service orchestrator
│   │   │   └── shadow_subagent.py   # Shadow subagent base class
│   │   ├── clients/           # HTTP clients for external services
│   │   │   ├── service_client.py    # Async HTTP client for services gateway
│   │   │   └── service_mapping.py   # Tool name → endpoint mapping
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
│   │   ├── config/            # JSON configurations
│   │   │   ├── agents/        # Agent definitions
│   │   │   ├── prompts/       # System prompt templates
│   │   │   ├── messages/      # Service response messages
│   │   │   ├── sample_data/   # Sample data for seeding
│   │   │   └── shadow_service.json  # Shadow service configuration
│   │   ├── seed/              # Database seeders
│   │   └── main.py            # FastAPI app entry point
│   └── requirements.txt
├── services/                  # Independently deployable services gateway
│   ├── app/
│   │   ├── main.py            # FastAPI entry point (port 8001)
│   │   ├── config.py          # Services gateway configuration
│   │   ├── routers/           # REST API routers
│   │   │   ├── remittances.py # /api/v1/remittances/*
│   │   │   ├── snpl.py        # /api/v1/snpl/*
│   │   │   ├── topups.py      # /api/v1/topups/*
│   │   │   ├── billpay.py     # /api/v1/billpay/*
│   │   │   ├── wallet.py      # /api/v1/wallet/*
│   │   │   ├── financial_data.py  # /api/v1/financial-data/*
│   │   │   └── campaigns.py   # /api/v1/campaigns/*
│   │   ├── services/          # Mock service implementations
│   │   │   ├── remittances.py
│   │   │   ├── snpl.py
│   │   │   ├── topups.py
│   │   │   ├── billpay.py
│   │   │   ├── wallet.py
│   │   │   ├── financial_data.py
│   │   │   └── campaigns.py
│   │   └── schemas/           # Pydantic models for API
│   │       └── common.py      # ServiceResponse, ErrorResponse
│   ├── tests/                 # Gateway tests
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── chat/                  # Simple vanilla JS chat UI
│   ├── admin/                 # Simple vanilla JS admin UI
│   └── react-app/             # React-based UI (in development)
└── docker-compose.yml         # PostgreSQL + Redis + Backend + Services Gateway
```

## Key Entry Points

| Flow | Entry Point | Description |
|------|-------------|-------------|
| Chat API | `backend/app/routes/chat.py` | POST `/api/chat/message` |
| Message handling | `backend/app/core/orchestrator.py:handle_message()` | Main conversation loop |
| Backend startup | `backend/app/main.py` | FastAPI lifespan, seeding |
| Admin API | `backend/app/routes/admin.py` | Agent/Tool CRUD |
| Services Gateway | `services/app/main.py` | FastAPI on port 8001 |
| Frontend chat | `frontend/chat/index.html` or `frontend/react-app/` | User interfaces |

## Module Relationships

```
User Request
     │
     ▼
[routes/chat.py] ──► [Orchestrator] (Three-Phase Flow)
                           │
                    PHASE 1: SETUP
                           │
                           ├──► [StateManager] (load/create session, get agent)
                           │
                    PHASE 2: CONTEXT ENRICHMENT
                           │
                           ├──► [ContextEnrichment] ──► [ToolExecutor] (execute on_enter tools)
                           │         │
                           │         └──► Stores enriched data in session.current_flow.stateData
                           │
                    PHASE 3: LLM GENERATION
                           │
                           ├──► [ContextAssembler] (builds prompt with enriched data)
                           │
                           ├──► [LLMClient] ────────┐
                           │                        │  (parallel execution)
                           ├──► [ShadowService] ────┘
                           │
                    TOOL EXECUTION (from LLM response)
                           │
                           ├──► [RoutingHandler] ──► [RoutingRegistry] (validated routing)
                           │         │
                           │         └──► Returns state_changed flag (no recursion)
                           │
                           ├──► [ToolExecutor] ──► [ServiceClient] ──► Services Gateway (HTTP)
                           │                              │
                           │                              ▼
                           │                      [services/app/routers/*]
                           │                              │
                           │                              ▼
                           │                      [services/app/services/*]
                           │
                           └──► Response with enriched data in context
```

**Data flow (Three-Phase Architecture):**

**Phase 1: Setup**
1. Request arrives at `routes/chat.py`
2. `Orchestrator` loads session via `StateManager`
3. Current agent loaded with tools, subflows, and response templates

**Phase 2: Context Enrichment** (NEW - Jan 2026)
4. `ContextEnrichment` checks if enrichment needed (first message in flow state)
5. Executes `on_enter.callTool` actions automatically
6. Fetches context requirements (frequent numbers, user limits, etc.)
7. Stores enriched data in `session.current_flow.stateData`

**Phase 3: LLM Generation**
8. `ContextAssembler` builds prompt including enriched data in "Available Context Data" section
9. `LLMClient` and `ShadowService` run **in parallel**
10. `ShadowService` evaluates all enabled subagents (financial advisor, campaigns)

**Tool Execution:**
11. **For routing tools** (enter_*, start_flow_*, navigation): `RoutingHandler` executes via validated registry
    - Returns `state_changed=True/False` (NO recursion - enrichment happens on next message)
12. **For service tools**: `ToolExecutor` calls `ServiceClient` which makes HTTP requests to Services Gateway
13. Services Gateway routes to appropriate service and returns JSON response
14. If shadow activation detected, user is routed to the relevant agent (flow preserved)
15. Response returned with main message + optional shadow messages

**Key Improvements (Jan 2026):**
- ✅ **No recursion:** State changes trigger enrichment on next message, not immediate recursion
- ✅ **Proactive data loading:** Frequent numbers, etc. loaded automatically when entering flow states
- ✅ **LLM-only formatting:** Services return raw data, LLM handles ALL user-facing formatting
- ✅ **Predictable flow:** Clear three-phase execution prevents "frozen" responses

## Conventions

- **Agent configs**: JSON files in `config/agents/` define tools, prompts, navigation
- **Tool naming**: `verb_noun` format (e.g., `get_exchange_rate`, `create_transfer`)
- **Navigation tools**: `enter_<agent>`, `up_one_level`, `go_home`, `escalate_to_human`
- **Flow tools**: `start_flow_<flowname>` triggers stateful subflows
- **Service methods**: Return ONLY raw data (JSON objects/arrays) - NO formatting, NO `_message` fields
- **Service-Presentation Separation**: Clean architectural boundary between service layer (data) and presentation layer (formatting)
  - **Service Layer** (`services/*.py`): Returns pure business data, UI-agnostic, usable by any client (chat, web, mobile, API)
  - **Presentation Layer** (`orchestrator.py`, `template_renderer.py`, agent configs): Handles all formatting via response templates or LLM
  - **No `_message` backdoor**: Orchestrator does NOT check for `_message` fields - all formatting must go through proper channels
- **i18n**: System prompts are always in English; only the final language directive tells LLM to respond in user's language (Spanish default). Service messages for user-facing content are bilingual in `config/messages/services.json`
- **Models**: Use GUID primary keys, JSON columns for flexible configs
- **Frontend state**: Zustand stores in `react-app/src/store/`
- **Sample data**: Sample users defined in `config/sample_data/users.json`, seeded at startup if not present

## Current State

**Implemented:** Multi-agent orchestration, all product agents (remittances, credit, topups, billpay, wallet), tool execution with mock backends, stateful subflows, confirmation handling, history compaction, debug panel, i18n (es/en), vanilla JS + React UIs, admin CRUD API, shadow service with parallel contextual messaging.

**Remittances Agent (Full Implementation):**
- Supports 7 countries: MX, GT, HN, CO, DO, SV, NI
- 17 tools: 3 flow triggers, 8 info tools, 4 action tools, 2 navigation tools
- 3 subflows: `send_money_flow` (8 states), `add_recipient_flow` (6 states), `quick_send_flow` (3 states)
- Delivery methods: Bank, Cash, Wallet (Nequi/Daviplata/Mercado Pago), Debit Card
- KYC-based limits with 3 levels
- Response templates for success/error scenarios

**Shadow Service (New):**
- Runs in parallel with main agent (no added latency)
- Two initial subagents: Financial Advisor (90% threshold) and Campaigns (70% threshold)
- Each subagent can inject contextual tips or "take over" the conversation
- Flow state preserved when shadow agent takes over - user returns to exact step
- Configurable via `config/shadow_service.json` (thresholds, tone, campaigns)
- Cooldown tracking to avoid tip fatigue
- Full Financial Advisor agent for deeper engagement when user shows interest

**Routing System:**
- Explicit routing via `routing` field in Tool model (no string parsing inference)
- `RoutingRegistry` validates all routing targets exist at startup (fail-fast)
- `RoutingHandler` provides unified execution for: enter_agent, start_flow, navigation
- Supports cross-agent flows via `cross_agent` field (e.g., SNPL → remittances flow)
- Agent and Subflow models have `config_id` for stable identifier lookups
- Tool configs can use `routing` (explicit) or `starts_flow` (legacy) fields
- Invalid routing configs prevent application startup with clear error messages

**Routing & Context Enrichment Refactor (Completed Jan 2026):**
- **Three-phase flow**: Setup → Context Enrichment → LLM Generation (no recursion)
- **Context enrichment**: Automatic execution of `on_enter.callTool` actions when entering flow states
- **Proactive data loading**: Frequent numbers, user limits, etc. loaded before LLM call
- **State tracking**: `state_changed` flag replaces `should_recurse` (no more recursion bugs)
- **Enriched data visibility**: Data shown in "Available Context Data" section of LLM prompt
- **Removed recursion**: Only shadow takeover can recurse (intentional); routing never recurses
- **Template cleanup**: Removed 8 success response templates; LLM handles all formatting
- **Benefits**: Predictable flow, no "frozen" responses, proactive data presentation
- **Files modified**: orchestrator.py, routing_handler.py, context_enrichment.py (new), 4 agent configs

**Service-Presentation Separation (Completed Jan 2026):**
- **Clean architectural boundary**: Service layer returns ONLY raw data, presentation layer handles ALL formatting
- **Service layer cleanup**: Removed 73 `_message` fields across all services (remittances: 31, snpl: 29, topups: 7, wallet: 3, billpay: 2)
- **Removed architectural backdoor**: Orchestrator no longer checks `result.data.get("_message")` - forces proper formatting channels
- **Benefits**: Services are now UI-agnostic and can be used by chat, web app, mobile app, or direct API calls
- **Team independence**: Backend/service team can work independently from conversational/frontend team
- **Formatting options**: Response templates (preferred for consistency) or LLM formatting (preferred for dynamic content)
- **All unit tests pass**: 68/68 service tests pass after refactoring

**Services Gateway (Completed Jan 2026):**
- **Independent deployment**: Services run in separate Docker container (port 8001)
- **REST API**: All services exposed via `/api/v1/{service}/*` endpoints
- **7 service modules**: remittances, snpl, topups, billpay, wallet, financial_data, campaigns
- **60+ endpoints**: Full coverage of all service methods
- **HTTP client**: `backend/app/clients/service_client.py` handles all service communication
- **Service mapping**: `backend/app/clients/service_mapping.py` maps tool names to endpoints
- **Headers**: `X-User-Id` for user context, `Accept-Language` for i18n
- **Response format**: `{"success": true, "data": {...}}` or `{"success": false, "error": "...", "error_code": "..."}`
- **Benefits**: Teams can work independently, services can scale separately, easy to swap mock for real

**Planned:** Shadow service admin UI, visual flow editor, analytics dashboard, WhatsApp integration, real backend services, auth, rate limiting.

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
- `backend/tests/unit/core/` - State manager, tool executor tests
- `backend/tests/unit/services/` - Mock service tests (topups, etc.)
- `backend/tests/integration/` - API endpoint tests
- `backend/tests/conversational/` - LLM-based scenario tests defined in agent JSON configs (`test_scenarios` field)
- `services/tests/` - Services gateway endpoint tests

**Running Services Gateway Tests:**
```bash
cd services && pip install -r requirements.txt
pytest tests/ -v
```
