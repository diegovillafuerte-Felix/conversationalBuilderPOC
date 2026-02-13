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

COS (Conversational Orchestrator Service) is a multi-agent conversational AI system for handling financial services (remittances, credit, top-ups, bill payments, wallet) through natural language. It uses a hierarchical agent architecture where a main orchestrator routes conversations to specialized product agents, each with their own tools, subflows, and response templates. The system supports stateful multi-step flows, confirmation handling, and escalation to human agents.

## Architecture

The system follows a **layered architecture** with clear separation of concerns:

1. **API Layer** (`backend/routes/`) - FastAPI endpoints handling HTTP requests
2. **Orchestration Layer** (`backend/core/`) - Conversation flow management and LLM interaction
3. **Configuration Layer** (`backend/core/`) - In-memory agent/tool/subflow configuration via `AgentRegistry`
4. **Data Layer** (`backend/models/`) - SQLAlchemy ORM models for sessions, messages, users (PostgreSQL)
5. **Services Gateway** (`services/`) - **Independently deployable** mock backend services via REST API
6. **JSON Configs** (`backend/config/`) - Source of truth for agent definitions

**Key patterns:**
- **Agent hierarchy**: Root orchestrator with child product agents
- **Agent isolation**: Each agent is ignorant of others; can only interact via assigned tools
- **Team ownership**: Product teams own their agent configs (JSON) and services; Platform team owns orchestration
- **State machine flows**: Multi-step processes with defined states and transitions
- **Tool-based actions**: Agents invoke tools that call services via HTTP
- **Explicit routing**: Validated routing system with startup checks (no string parsing inference)
- **Context assembly**: Dynamic prompt construction based on user, session, and agent state
- **Service-presentation separation**: Services return raw data only; LLM/templates handle formatting
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
│   │   │   ├── config_types.py      # Dataclasses for agent/tool/subflow configs
│   │   │   ├── agent_registry.py    # In-memory config registry (singleton)
│   │   │   ├── routing.py           # Routing types and data classes
│   │   │   ├── routing_handler.py   # Unified routing execution
│   │   │   ├── context_enrichment.py # Condition evaluation utilities
│   │   │   ├── llm_client.py        # OpenAI API wrapper
│   │   │   ├── history_compactor.py # Conversation summarization
│   │   │   ├── config_loader.py     # Loads JSON configs
│   │   │   ├── i18n.py              # Language directive injection
│   │   │   ├── template_renderer.py # Response templating
│   │   │   └── event_trace.py       # Event tracing for debugging
│   │   ├── clients/           # HTTP clients for external services
│   │   │   ├── service_client.py    # Async HTTP client for services gateway
│   │   │   └── service_mapping.py   # Tool name → endpoint mapping
│   │   ├── models/            # SQLAlchemy ORM models (session/user data only)
│   │   │   ├── session.py     # ConversationSession
│   │   │   ├── conversation.py # ConversationMessage, ConversationHistoryCompacted
│   │   │   └── user.py        # UserContext
│   │   ├── routes/            # FastAPI routers
│   │   │   ├── chat.py        # Chat API endpoints
│   │   │   └── admin.py       # Admin CRUD endpoints
│   │   ├── schemas/           # Pydantic request/response models
│   │   ├── config/            # JSON configurations
│   │   │   ├── agents/        # Agent definitions (owned by product teams)
│   │   │   │   # felix.json (Platform), remittances.json (Chat team),
│   │   │   │   # topups.json (New Products), snpl.json (Credit team),
│   │   │   │   # billpay.json (New Products), wallet.json
│   │   │   ├── prompts/       # System prompt templates (Platform team)
│   │   │   ├── sample_data/   # Sample data for seeding
│   │   │   └── confirmation_templates.json  # Financial transaction confirmations
│   │   ├── seed/              # Database seeders (users only - agents loaded from JSON)
│   │   └── main.py            # FastAPI app entry point
│   ├── tests/
│   │   ├── e2e/               # E2E conversation tests (live servers)
│   │   │   ├── server_manager.py    # Server lifecycle management
│   │   │   ├── scenarios.py         # Scenario definitions with structural gates
│   │   │   ├── run_conversations.py # Main runner script (Claude Code's tool)
│   │   │   ├── test_e2e.py          # Pytest wrapper for CI regression
│   │   │   └── results/             # Output directory (gitignored)
│   │   ├── unit/              # Unit tests
│   │   ├── integration/       # API endpoint tests
│   │   └── conversational/    # LLM-based scenario tests
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
│   └── react-app/             # React-based UI
│       ├── src/components/
│       │   ├── chat/          # Chat interface components
│       │   │   ├── ChatContainer.jsx, ChatHeader.jsx, ChatInput.jsx
│       │   │   ├── MessageList.jsx, Message.jsx, TypingIndicator.jsx
│       │   │   ├── ConfirmationButtons.jsx, SessionInfo.jsx
│       │   │   ├── DebugPanel.jsx, EventTracePanel.jsx
│       │   │   └── UserSidebar.jsx
│       │   ├── visualize/     # Agent/flow visualization
│       │   │   ├── VisualizePage.jsx, HierarchyDiagram.jsx
│       │   │   ├── StateMachineDiagram.jsx, ToolCatalog.jsx
│       │   │   └── nodes/ (AgentNode.jsx, StateNode.jsx)
│       │   └── admin/         # Admin layout (simplified)
│       ├── src/pages/         # ChatPage.jsx, AdminPage.jsx
│       ├── src/store/         # Zustand stores (chatStore, visualizeStore)
│       └── src/services/      # API clients (chatApi, adminApi)
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
| Frontend chat | `frontend/react-app/` | React chat + admin UI |

## Module Relationships

```
User Request
     │
     ▼
[routes/chat.py] ──► [Orchestrator] (Routing Chain Flow)
                           │
                    PHASE 1: SETUP
                           │
                           ├──► [StateManager] (load/create session, get agent)
                           │
                    PHASE 2: ROUTING CHAIN
                           │
                           ├──► [ContextAssembler] (builds prompt)
                           │
                           ├──► [LLMClient] (call model)
                           │
                    TOOL EXECUTION (from LLM response)
                           │
                           ├──► [RoutingHandler] ──► [AgentRegistry] (validated routing)
                           │         │
                           │         └──► Returns state_changed flag
                           │
                           ├──► [ToolExecutor] ──► [ServiceClient] ──► Services Gateway (HTTP)
                           │                              │
                           │                              ▼
                           │                      [services/app/routers/*]
                           │                              │
                           │                              ▼
                           │                      [services/app/services/*]
                           │
                           └──► Loop until stable state (no routing)
```

**Data flow:**

**Phase 1: Setup**
1. Request arrives at `routes/chat.py`
2. `Orchestrator` loads session via `StateManager`
3. Current agent loaded with tools, subflows, and response templates

**Phase 2: Routing Chain**
4. `ContextAssembler` builds prompt with current agent/flow context
5. `LLMClient` calls the model
6. Tools executed from LLM response:
   - **Routing tools** (enter_*, start_flow_*, navigation): `RoutingHandler` handles, may trigger chain continuation
   - **Service tools**: `ToolExecutor` calls `ServiceClient` which makes HTTP requests to Services Gateway
7. If state changed, loop back to step 4 with new agent context
8. When stable (no routing), return response to user

**Key Design Decisions:**
- ✅ **No recursion:** Routing chain iterates until stable state
- ✅ **LLM-only formatting:** Services return raw data, LLM handles ALL user-facing formatting
- ✅ **Simple flow:** LLM explicitly calls tools to fetch data when needed

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
- **i18n (Simplified)**: ALL prompts and configs are in English. The ONLY language-related code is:
  1. User's `language` attribute stored in their profile (default: "es")
  2. Language directive injected at the end of every system prompt telling the LLM what language to respond in
  - This means: LLM gets English instructions, responds in user's preferred language
  - No localized config files, no `get_localized()` calls, no bilingual dictionaries
- **Models**: Use GUID primary keys, JSON columns for flexible configs
- **Frontend state**: Zustand stores in `react-app/src/store/`
- **Sample data**: Sample users defined in `config/sample_data/users.json`, seeded at startup if not present

## Current State

**Implemented:** Multi-agent orchestration, all product agents (remittances, credit, topups, billpay, wallet), tool execution with mock backends, stateful subflows, confirmation handling, history compaction, debug panel, i18n (es/en), React UI, admin CRUD API.

**Remittances Agent (Full Implementation):**
- Supports 7 countries: MX, GT, HN, CO, DO, SV, NI
- 17 tools: 3 flow triggers, 8 info tools, 4 action tools, 2 navigation tools
- 3 subflows: `send_money_flow` (8 states), `add_recipient_flow` (6 states), `quick_send_flow` (3 states)
- Delivery methods: Bank, Cash, Wallet (Nequi/Daviplata/Mercado Pago), Debit Card
- KYC-based limits with 3 levels
- Response templates for success/error scenarios

**Routing System:**
- Explicit routing via `routing` field in ToolConfig (no string parsing inference)
- `AgentRegistry` validates all routing targets exist at startup (fail-fast)
- `RoutingHandler` provides unified execution for: enter_agent, start_flow, navigation
- Supports cross-agent flows via `cross_agent` field (e.g., SNPL → remittances flow)
- AgentConfig and SubflowConfig use `config_id` for stable identifier lookups
- Tool configs can use `routing` (explicit) or `starts_flow` (legacy) fields
- Invalid routing configs prevent application startup with clear error messages

**Declarative State Transitions:**
- **State-level transitions**: The `transitions` list in SubflowStateConfig is evaluated after service tool execution
- **tool_trigger field**: Explicit mapping from tool name to transition (e.g., `"tool_trigger": "detect_carrier"`)
- **Condition evaluation**: Supports `key is not None`, `key in stateData`, `key == 'value'`, nested paths (`_tool_result.carrier`)
- **First match wins**: Transitions are evaluated in config order
- **Automatic state change**: When a transition matches, the system transitions to the target state and signals chain continuation
- **Tool result storage**: Tool results are stored in stateData as `_result_{tool_name}` for condition evaluation
- **Condition utilities**: `context_enrichment.py` provides `evaluate_condition()` for declarative transition evaluation

**Service-Presentation Separation:**
- **Clean architectural boundary**: Service layer returns ONLY raw data, presentation layer handles ALL formatting
- **Benefits**: Services are now UI-agnostic and can be used by chat, web app, mobile app, or direct API calls
- **Team independence**: Backend/service team can work independently from conversational/frontend team
- **Formatting options**: Response templates (preferred for consistency) or LLM formatting (preferred for dynamic content)

**Services Gateway:**
- **Independent deployment**: Services run in separate Docker container (port 8001)
- **REST API**: All services exposed via `/api/v1/{service}/*` endpoints
- **7 service modules**: remittances, snpl, topups, billpay, wallet, financial_data, campaigns
- **60+ endpoints**: Full coverage of all service methods
- **HTTP client**: `backend/app/clients/service_client.py` handles all service communication
- **Service mapping**: `backend/app/clients/service_mapping.py` maps tool names to endpoints
- **Headers**: `X-User-Id` for user context, `Accept-Language` for i18n
- **Response format**: `{"success": true, "data": {...}}` or `{"success": false, "error": "...", "error_code": "..."}`
- **Benefits**: Teams can work independently, services can scale separately, easy to swap mock for real

**i18n Simplification:**
- **English-only configs**: All JSON configs (agents, prompts, tools) now use plain English strings
- **Removed localization layer**: Deleted `get_localized()`, `get_message()`, `get_prompt_section()`, `get_base_system_prompt()` from i18n.py
- **Confirmation templates**: New centralized `confirmation_templates.json` with enable/disable toggle per template
- **Only language code remaining**: `get_language_directive()` in i18n.py - injects user's language preference at end of every system prompt
- **Benefits**: Simpler codebase, better LLM performance with English instructions, no dead bilingual code

**JSON-Only Agent Configuration:**
- **Removed SQLAlchemy models**: Deleted `models/agent.py` (Agent, Tool, ResponseTemplate) and `models/subflow.py` (Subflow, SubflowState)
- **New dataclasses**: `config_types.py` defines AgentConfig, ToolConfig, SubflowConfig, SubflowStateConfig, ResponseTemplateConfig
- **In-memory registry**: `AgentRegistry` singleton loads all agent configs from JSON at startup
- **Synchronous lookups**: Agent/tool/subflow lookups no longer require async DB queries
- **Startup validation**: Registry validates all routing targets exist (agents, subflows) - fail-fast on invalid configs
- **Hot reload**: Admin endpoint `/api/admin/agents/reload` reinitializes registry without DB sync
- **Benefits**: Faster lookups (no DB roundtrips), simpler code (no ORM mapping), easier testing (no DB fixtures for agent configs)

**Event Tracing:**
- Debug system for tracking routing, tool calls, and orchestration flow
- `EventTracer` class captures events during message processing
- Categories: session, agent, flow, routing, LLM, tool, service, error
- `EventTracePanel.jsx` component displays trace events in React UI
- Helps diagnose routing issues and understand conversation flow

**Visualization System:**
- `VisualizePage.jsx` - Main visualization interface
- `HierarchyDiagram.jsx` - Agent hierarchy visualization
- `StateMachineDiagram.jsx` - Subflow state machine visualization
- `ToolCatalog.jsx` - Browsable tool catalog
- Uses React Flow for interactive diagrams
- `visualizeStore.js` - Zustand store for visualization state

**Simplification (Jan 2026):**
- **Simplified Context Enrichment**: Now only provides `evaluate_condition()` for declarative transitions
- **Removed proactive data fetching**: LLM now explicitly calls tools when it needs data (via `agent_instructions`)
- **Benefits**: ~50% reduction in core orchestration code, simpler mental model, predictable flow

**Prompt Architecture Optimization (Jan 2026):**
- **Prompt Modes**: `ContextAssembler` now supports `mode: PromptMode` parameter with two modes:
  - `FULL` (default): Full context with all sections (base prompt, agent desc, user profile, product context, history, flow state, navigation, language)
  - `ROUTING`: Minimal context for routing decisions (~500 tokens vs ~3000 for FULL). Used for chain iterations after routing occurs.
- **PromptMode enum**: Added to `config_types.py` with `FULL` and `ROUTING` values
- **`_build_routing_context()`**: New method builds minimal prompt with only routing tools and brief system prompt
- **`_build_routing_tools()`**: New method extracts only tools with routing config (enter_agent, start_flow, navigation)
- **Orchestrator integration**: After first routing iteration, subsequent iterations use ROUTING mode automatically
- **Token savings**: ~80% reduction for routing chain iterations (from ~3000 to ~500 tokens)

**Default Tools Whitelist:**
- **`default_tools` field**: New optional field in AgentConfig for tool whitelisting when not in a flow
- **Tool selection priority**: 1) Flow state_tools → 2) Agent default_tools → 3) All agent tools
- **Configured agents**: remittances.json (6 default tools), snpl.json (6 default tools)
- **Token savings**: ~70% tool token reduction for agents with many tools (19 → 6 + navigation)
- **Backward compatible**: Agents without `default_tools` continue to expose all tools

**E2E Conversation Testing:**
- **Framework**: `backend/tests/e2e/` — runs multi-turn conversations against live servers (backend + services gateway + real LLM)
- **Design philosophy**: Framework produces rich readable output; quality judgment comes from Claude Code reading the output, not from assertions
- **Runner script**: `backend/tests/e2e/run_conversations.py` — primary tool for testing, outputs to `tests/e2e/results/`
- **Scenarios**: `backend/tests/e2e/scenarios.py` — 5 scenarios (3 smoke + 2 multi-turn)
- **Structural gates**: Minimal hard-fail checks (non-empty response, HTTP 200, escalation flag) — catches "system is broken" not "wrong answer"
- **Pytest wrapper**: `backend/tests/e2e/test_e2e.py` — same scenarios via pytest for CI-style regression (`-m e2e`)
- **Server manager**: `backend/tests/e2e/server_manager.py` — health checks and optional auto-start for backend/services gateway

**Planned:** Analytics dashboard, WhatsApp integration, real backend services, auth, rate limiting.

## Development Workflow (Autonomous)

Claude Code operates as the engineering team. The human PM provides requirements and answers product questions.

### After every code change:
1. `./venv/bin/python -m pytest tests/unit -v` — must pass
2. `./venv/bin/python -m tests.e2e.run_conversations` — run live conversations
3. Read `tests/e2e/results/*.txt` — assess quality of responses
4. Fix issues, repeat

### Consult the PM for:
- New feature requirements / scope changes
- Product direction and prioritization
- UX decisions (how should X behave?)
- Architecture tradeoffs that affect product

### Do NOT consult the PM for:
- Test results, logs, debugging
- Implementation details
- "Does the system still work?" — run the E2E tests
- Mechanical tasks (server management, DB issues, config loading)

### E2E Test Cost
- Smoke (~$0.03): 3 scenarios, 1 turn each
- Full (~$0.13): 5 scenarios, 10 turns total
- Run full suite after significant orchestration/routing/agent changes

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

# E2E conversation tests (requires live servers on ports 8000/8001)
./venv/bin/python -m tests.e2e.run_conversations              # All scenarios, readable output
./venv/bin/python -m tests.e2e.run_conversations --smoke       # Smoke tests only
./venv/bin/python -m tests.e2e.run_conversations --scenario remittance_flow  # Single scenario
./venv/bin/python -m pytest tests/e2e/ -v -m e2e               # Pytest mode for CI
```

**Test Structure:**
- `backend/tests/unit/core/` - State manager, tool executor tests
- `backend/tests/integration/` - API endpoint tests
- `backend/tests/conversational/` - LLM-based scenario tests defined in agent JSON configs (`test_scenarios` field)
- `backend/tests/e2e/` - E2E conversation tests against live servers (see Development Workflow section)
- `services/tests/` - Services gateway endpoint tests

**Running Services Gateway Tests:**
```bash
cd services && pip install -r requirements.txt
pytest tests/ -v
```
