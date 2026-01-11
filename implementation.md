# Felix Conversational Orchestrator - Implementation Specification

## Executive Summary

The Felix Conversational Orchestrator POC enables natural, context-aware conversations with users across multiple financial products through a hierarchical agent architecture. This document tracks implementation status against all requirements.

---

## Implementation Status Overview

### Core Components

| Component | Status | Requirements Covered |
|-----------|--------|---------------------|
| Database Models | ✅ Complete | FR-018 to FR-020 |
| Chat API Endpoints | ✅ Complete | FR-001 to FR-010 |
| Admin API Endpoints | ✅ Complete | FR-018 to FR-025 |
| Context Assembler | ✅ Complete | FR-011 to FR-017 |
| State Manager | ✅ Complete | FR-007 to FR-009 |
| Tool Executor | ✅ Complete | FR-004 to FR-006 |
| Orchestrator | ✅ Complete | FR-001 to FR-010 |
| Mock Services | ✅ Complete | US-006 to US-011 |
| Chat UI | ✅ Complete | US-020 to US-022 |
| Admin UI | ✅ Complete | US-012 to US-016 |
| Observability UI | 🔲 Not Started | US-017 to US-019 |
| LLM Integration | ✅ Complete | FR-001 |
| Template Renderer | ✅ Complete | FR-023 |
| Demo User Seeding | ✅ Complete | - |

---

## Quick Start

### 1. Start the Backend

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

### 2. Start the React Frontend

```bash
cd frontend/react-app
npm install
npm run dev
```

- **Chat UI**: http://localhost:3000/
- **Admin UI**: http://localhost:3000/admin
- **Observability UI**: Not yet migrated

### 3. API Documentation

Once the backend is running, visit: `http://localhost:8000/docs`

---

## Project Structure

```
conversationalBuilderPOC/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── orchestrator.py      # Main conversation handler
│   │   │   ├── state_manager.py     # Session/flow state
│   │   │   ├── tool_executor.py     # Tool execution
│   │   │   ├── context_assembler.py # Prompt assembly
│   │   │   ├── template_renderer.py # Response templates
│   │   │   └── llm_client.py        # OpenAI client
│   │   ├── models/
│   │   │   ├── agent.py             # Agent, Tool, ResponseTemplate
│   │   │   ├── subflow.py           # Subflow, SubflowState
│   │   │   ├── session.py           # ConversationSession
│   │   │   ├── conversation.py      # ConversationMessage
│   │   │   └── user.py              # UserContext
│   │   ├── routes/
│   │   │   ├── chat.py              # Chat API endpoints
│   │   │   ├── admin.py             # Admin API endpoints
│   │   │   └── observability.py     # Observability API endpoints
│   │   ├── schemas/
│   │   │   ├── chat.py              # Chat request/response schemas
│   │   │   ├── admin.py             # Admin request/response schemas
│   │   │   └── observability.py     # Observability schemas
│   │   ├── services/                # Mock external services
│   │   ├── seed/
│   │   │   └── agents.py            # Seed data
│   │   ├── main.py                  # FastAPI app entry point
│   │   ├── config.py                # Settings
│   │   └── database.py              # Database setup
│   ├── venv/                        # Virtual environment
│   ├── requirements.txt
│   └── .env                         # Environment variables
│
├── frontend/
│   ├── chat/
│   │   ├── index.html               # Chat interface
│   │   ├── chat.js                  # Chat client logic
│   │   └── styles.css               # Chat styling
│   ├── admin/
│   │   ├── index.html               # Admin dashboard
│   │   ├── agents.js                # Agent management
│   │   ├── tools.js                 # Tool/template management
│   │   ├── flows.js                 # Subflow/state management
│   │   ├── flow-builder.js          # Visual drag-and-drop builder
│   │   └── styles.css               # Admin styling
│   └── observability/
│       ├── index.html               # Conversation list view
│       ├── detail.html              # Conversation detail view
│       ├── observability.js         # Observability logic
│       └── styles.css               # Observability styling
│
└── docker-compose.yml               # Container orchestration
```

---

## API Endpoints

### Chat API (`/api/chat`)

| Method | Endpoint | Description | Requirement |
|--------|----------|-------------|-------------|
| POST | `/api/chat/message` | Send message and get response | FR-001 |
| POST | `/api/chat/session` | Create new session | FR-002 |
| GET | `/api/chat/session/{id}` | Get session info | FR-002 |
| POST | `/api/chat/session/{id}/end` | End session | FR-002 |
| POST | `/api/chat/session/{id}/escalate` | Escalate to human | FR-010, US-005 |
| POST | `/api/chat/session/{id}/confirm` | Confirm pending action | FR-005 |
| POST | `/api/chat/session/{id}/cancel` | Cancel pending action | FR-005 |

### Admin API (`/api/admin`)

| Method | Endpoint | Description | Requirement |
|--------|----------|-------------|-------------|
| GET | `/agents` | List all agents | FR-018 |
| GET | `/agents/{id}` | Get agent with relationships | FR-018 |
| POST | `/agents` | Create agent | FR-018, US-012 |
| PUT | `/agents/{id}` | Update agent | FR-018, US-012 |
| DELETE | `/agents/{id}` | Delete agent (cascades) | FR-018 |
| POST | `/agents/{id}/clone` | Clone agent with tools/templates | US-012 |
| GET | `/agents/{id}/tools` | List agent's tools | FR-019 |
| POST | `/agents/{id}/tools` | Add tool | FR-019, US-013 |
| PUT | `/tools/{id}` | Update tool | FR-019, US-013 |
| DELETE | `/tools/{id}` | Delete tool | FR-019 |
| GET | `/agents/{id}/subflows` | List agent's subflows | FR-020 |
| POST | `/agents/{id}/subflows` | Create subflow | FR-020, US-014 |
| PUT | `/subflows/{id}` | Update subflow | FR-020 |
| DELETE | `/subflows/{id}` | Delete subflow (cascades states) | FR-020 |
| GET | `/subflows/{id}/states` | List subflow states | FR-020 |
| POST | `/subflows/{id}/states` | Add state | FR-020, US-014 |
| PUT | `/states/{id}` | Update state | FR-020 |
| DELETE | `/states/{id}` | Delete state | FR-020 |
| POST | `/subflows/{id}/validate` | Validate subflow (orphans, dead ends) | FR-022 |
| GET | `/subflows/{id}/export` | Export subflow as JSON | US-014 |
| GET | `/agents/{id}/templates` | List response templates | FR-023 |
| POST | `/agents/{id}/templates` | Create template | FR-023, US-015 |
| PUT | `/templates/{id}` | Update template | FR-023 |
| DELETE | `/templates/{id}` | Delete template | FR-023 |
| POST | `/templates/{id}/preview` | Preview template with sample data | US-015 |

### Observability API (`/api/observability`)

| Method | Endpoint | Description | Requirement |
|--------|----------|-------------|-------------|
| GET | `/conversations` | List conversations with filters | FR-030, US-017 |
| GET | `/conversations/{id}` | Get full conversation detail | FR-031, US-018 |
| GET | `/conversations/{id}/messages` | Get message timeline | FR-026, US-018 |
| GET | `/conversations/{id}/prompts` | Get prompts sent to LLM | FR-027, US-018 |
| GET | `/conversations/{id}/tool-calls` | Get tool calls with results | FR-028, US-018 |
| GET | `/conversations/{id}/state-transitions` | Get state transitions | FR-029, US-018 |
| GET | `/conversations/{id}/flow-path` | Get flow visualization data | US-019 |
| GET | `/conversations/search` | Search by content | US-017 |

---

## Feature Implementation Details

### Epic 1: Conversational Experience

#### US-001: Contextual Greeting
| Acceptance Criteria | Status | Implementation |
|---------------------|--------|----------------|
| AC-001.1: Use preferred name | ✅ | Context assembler includes user profile |
| AC-001.2: Reference recent activity | ✅ | Product summaries in context |
| AC-001.3: Time-based greeting | ✅ | Orchestrator system prompt |

#### US-002: Product Navigation
| Acceptance Criteria | Status | Implementation |
|---------------------|--------|----------------|
| AC-002.1: Route "quiero enviar dinero" to remittances | ✅ | Navigation tools in orchestrator |
| AC-002.2: Route credit queries | ✅ | Navigation tools |
| AC-002.3: Transparent routing | ✅ | No explicit transfer messages |
| AC-002.4: Multi-product sequence | ✅ | State manager handles transitions |

#### US-003: Return Navigation
| Acceptance Criteria | Status | Implementation |
|---------------------|--------|----------------|
| AC-003.1: Return to main orchestrator | ✅ | go_home navigation tool |
| AC-003.2: Natural topic changes | ✅ | Intent detection in agents |
| AC-003.3: Graceful abandonment | 🔲 | Save-for-later not implemented |

#### US-004: Conversation Continuity
| Acceptance Criteria | Status | Implementation |
|---------------------|--------|----------------|
| AC-004.1: Recent messages verbatim | ✅ | Context assembler token budget |
| AC-004.2: Summarized older messages | ✅ | History compactor with LLM summarization |
| AC-004.3: Reference earlier context | ✅ | Full history in context window |
| AC-004.4: Flow state persistence | ✅ | State manager |

#### US-005: Human Escalation
| Acceptance Criteria | Status | Implementation |
|---------------------|--------|----------------|
| AC-005.1: Request human at any point | ✅ | Escalation tool |
| AC-005.2: Acknowledge with wait time | ✅ | Mock response |
| AC-005.3: Preserve context | ✅ | Session persisted |
| AC-005.4: Session status change | ✅ | Status enum includes "escalated" |

### Epic 2: Financial Transactions

#### US-006: Send Remittance Flow
| Acceptance Criteria | Status | Implementation |
|---------------------|--------|----------------|
| AC-006.1: Natural initiation | ✅ | Intent routing |
| AC-006.2: Show exchange rate/fees | ✅ | Mock remittance service |
| AC-006.3: Confirm recipient | ✅ | Subflow state |
| AC-006.4: Transaction summary | ✅ | Confirmation message |
| AC-006.5: Explicit confirmation | ✅ | Confirmation flow |
| AC-006.6: Success with confirmation # | ✅ | Response template |

#### US-007: Transaction Confirmation
| Acceptance Criteria | Status | Implementation |
|---------------------|--------|----------------|
| AC-007.1: Explicit confirmation required | ✅ | Tool requires_confirmation flag |
| AC-007.2: Clear confirmation message | ✅ | Template with placeholders |
| AC-007.3: 5-minute expiration | ✅ | Confirmation timeout |
| AC-007.4: Cancel option | ✅ | Cancel endpoint |
| AC-007.5: Wait before executing | ✅ | Tool executor logic |

#### US-008: Check Transaction Status
| Acceptance Criteria | Status | Implementation |
|---------------------|--------|----------------|
| AC-008.1: Ask about transfers | ✅ | Status check tool |
| AC-008.2: Default to recent | ✅ | Mock service |
| AC-008.3: Query by confirmation # | ✅ | Parameter support |
| AC-008.4: Status details | ✅ | Response mapping |

#### US-009: Check Balances
| Acceptance Criteria | Status | Implementation |
|---------------------|--------|----------------|
| AC-009.1: Wallet balance query | ✅ | Wallet mock service |
| AC-009.2: Credit balance query | ✅ | Credit mock service |
| AC-009.3: Available credit info | ✅ | Response includes details |
| AC-009.4: No confirmation for reads | ✅ | side_effect = "read" |

#### US-010: Send Top-Up
| Acceptance Criteria | Status | Implementation |
|---------------------|--------|----------------|
| AC-010.1: Natural initiation | ✅ | Intent routing |
| AC-010.2: Carrier identification | ✅ | Mock topup service |
| AC-010.3: Available amounts | ✅ | Service response |
| AC-010.4: Confirmation required | ✅ | Financial tool |

#### US-011: Pay Bills
| Acceptance Criteria | Status | Implementation |
|---------------------|--------|----------------|
| AC-011.1: Natural initiation | ✅ | Intent routing |
| AC-011.2: Bill lookup | ✅ | Mock billpay service |
| AC-011.3: Partial payment | ✅ | Amount parameter |
| AC-011.4: Confirmation details | ✅ | Template |

### Epic 3: Admin Management

#### US-012: Manage Agents
| Acceptance Criteria | Status | Implementation |
|---------------------|--------|----------------|
| AC-012.1: Create with name, description, parent | ✅ | Admin API |
| AC-012.2: Configure model per agent | ✅ | model_name field |
| AC-012.3: System prompt additions | ✅ | system_prompt_addition |
| AC-012.4: Context requirements | ✅ | context_requirements JSON |
| AC-012.5: Activate/deactivate | ✅ | is_active flag |
| AC-012.6: No restart required | ✅ | Dynamic loading |

#### US-013: Manage Tools
| Acceptance Criteria | Status | Implementation |
|---------------------|--------|----------------|
| AC-013.1: Add with name, description, params | ✅ | Tool model |
| AC-013.2: Configure API endpoint | ✅ | api_endpoint, method, headers |
| AC-013.3: Mark as requiring confirmation | ✅ | requires_confirmation flag |
| AC-013.4: Confirmation message template | ✅ | confirmation_message field |
| AC-013.5: Side effect classification | ✅ | side_effect enum |
| AC-013.6: Response field mappings | ✅ | response_mapping JSON |

#### US-014: Visual Subflow Builder
| Acceptance Criteria | Status | Implementation |
|---------------------|--------|----------------|
| AC-014.1: Pan/zoom with minimap | 🔲 | Not implemented |
| AC-014.2: Drag to create states | 🔲 | Not implemented |
| AC-014.3: Connect with arrows | 🔲 | Not implemented |
| AC-014.4: Side panel properties | 🔲 | Form-based only |
| AC-014.5: Transition triggers | ✅ | State transitions |
| AC-014.6: Visual indicators | 🔲 | Not implemented |
| AC-014.7: Real-time validation | 🔲 | API endpoint exists |
| AC-014.8: Save/load/duplicate | ✅ | CRUD operations |
| AC-014.9: Export as JSON | 🔲 | Endpoint needed |

#### US-015: Response Templates
| Acceptance Criteria | Status | Implementation |
|---------------------|--------|----------------|
| AC-015.1: Create with trigger | ✅ | ResponseTemplate model |
| AC-015.2: Placeholders | ✅ | Template renderer |
| AC-015.3: Mandatory/suggested | ✅ | enforcement_level field |
| AC-015.4: Preview with sample data | 🔲 | Endpoint needed |

#### US-016: Test Flows in Builder
| Acceptance Criteria | Status | Implementation |
|---------------------|--------|----------------|
| AC-016.1: Test button opens chat | 🔲 | Not implemented |
| AC-016.2: State highlighted on canvas | 🔲 | Not implemented |
| AC-016.3: Real-time transitions | 🔲 | Not implemented |
| AC-016.4: Mock tool responses | 🔲 | Not implemented |
| AC-016.5: Variable inspector | 🔲 | Not implemented |

### Epic 4: Observability

#### US-017: Conversation List
| Acceptance Criteria | Status | Implementation |
|---------------------|--------|----------------|
| AC-017.1: Show user, time, duration, count, status | 🔲 | Endpoint needed |
| AC-017.2: Filter by date, status | 🔲 | Query params |
| AC-017.3: Search by content | 🔲 | Full-text search |
| AC-017.4: Sort by recency/duration | 🔲 | Query params |

#### US-018: Conversation Detail View
| Acceptance Criteria | Status | Implementation |
|---------------------|--------|----------------|
| AC-018.1: Full message timeline | 🔲 | Endpoint needed |
| AC-018.2: Expandable details (prompts, tools, tokens) | 🔲 | Logging required |
| AC-018.3: User context snapshot | 🔲 | Capture at session start |
| AC-018.4: Agent change indicators | 🔲 | Track in messages |

#### US-019: Flow Visualization in Review
| Acceptance Criteria | Status | Implementation |
|---------------------|--------|----------------|
| AC-019.1: Open flow visualization | 🔲 | Not implemented |
| AC-019.2: Highlight path taken | 🔲 | State history needed |
| AC-019.3: Click to see messages | 🔲 | Not implemented |

### Epic 5: Chat Interface

#### US-020: Basic Chat UI
| Acceptance Criteria | Status | Implementation |
|---------------------|--------|----------------|
| AC-020.1: Text input and send | ✅ | chat.js |
| AC-020.2: Message bubbles | ✅ | CSS styling |
| AC-020.3: Timestamps | ✅ | Message display |
| AC-020.4: Auto-scroll | ✅ | JavaScript |
| AC-020.5: Loading indicator | ✅ | Spinner |

#### US-021: Confirmation Buttons
| Acceptance Criteria | Status | Implementation |
|---------------------|--------|----------------|
| AC-021.1: Show Confirmar/Cancelar buttons | ✅ | ConfirmationButtons.jsx component |
| AC-021.2: Buttons send response | ✅ | API integration via chatStore |
| AC-021.3: Disable after click/timeout | ✅ | Countdown timer with expiration handling |

#### US-022: Session Management
| Acceptance Criteria | Status | Implementation |
|---------------------|--------|----------------|
| AC-022.1: New Conversation button | ✅ | SessionInfo.jsx component |
| AC-022.2: Preset test users | ✅ | UserSidebar.jsx with /api/chat/users |
| AC-022.3: User context in sidebar | ✅ | UserSidebar.jsx shows balances/products |

---

## Non-Functional Requirements

### Performance (NFR-001 to NFR-003)

| Requirement | Target | Status | Implementation |
|-------------|--------|--------|----------------|
| Response latency | < 3s P90 | 🔲 | Needs measurement |
| Context assembly | < 500ms | ✅ | Async operations |
| Admin UI load | < 2s | ✅ | Lightweight frontend |

### Reliability (NFR-004 to NFR-006)

| Requirement | Target | Status | Implementation |
|-------------|--------|--------|----------------|
| Uptime | 95% | ✅ | Standard deployment |
| LLM failure handling | Retry + fallback | ✅ | Exponential backoff retry in llm_client.py |
| No data loss on restart | Session persisted | ✅ | Database persistence |

### Usability (NFR-007 to NFR-009)

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| Desktop browsers (Chrome, Firefox, Safari) | ✅ | Standard HTML/CSS/JS |
| Admin UI usable without docs | ✅ | Intuitive design |
| Keyboard shortcuts in flow builder | 🔲 | Not implemented |

### Maintainability (NFR-010 to NFR-012)

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| Consistent code style | ✅ | Python/JS conventions |
| API documentation | ✅ | FastAPI auto-docs |
| Structured logging | 🔲 | Needs enhancement |

### Security (NFR-013 to NFR-014)

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| API keys not in client | ✅ | Backend only |
| Admin authentication | 🔲 | Basic auth needed |

---

## Data Requirements

### Data Entities

| Entity | Model | Persistence | Status |
|--------|-------|-------------|--------|
| Agent | `models/agent.py` | Database | ✅ |
| Tool | `models/agent.py` | Database | ✅ |
| Subflow | `models/subflow.py` | Database | ✅ |
| State | `models/subflow.py` | Database (embedded) | ✅ |
| Transition | `models/subflow.py` | Database (embedded) | ✅ |
| ResponseTemplate | `models/agent.py` | Database | ✅ |
| ConversationSession | `models/session.py` | Database + Cache | ✅ |
| UserContext | `models/user.py` | Database | ✅ |
| ConversationHistory | `models/conversation.py` | Database | ✅ |
| Message | `models/conversation.py` | Database (embedded) | ✅ |

### Data Retention

| Data Type | Retention | Status |
|-----------|-----------|--------|
| Conversations | Indefinite (POC) | ✅ |
| Session state | 24 hours | ✅ |
| User context | Indefinite (POC) | ✅ |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python FastAPI |
| Database | SQLite (dev) / PostgreSQL (prod) |
| ORM | SQLAlchemy 2.0 (async) |
| LLM | OpenAI gpt-4o |
| Frontend | React 18 + Vite + Zustand |
| Container | Docker Compose |

---

## Environment Variables

Create `backend/.env`:

```
OPENAI_API_KEY=your-api-key-here
DATABASE_URL=sqlite+aiosqlite:///./felix_orchestrator.db
DEBUG=true
CONFIRMATION_TIMEOUT_SECONDS=300
```

---

## POC Demo Scenarios

### Scenario 1: Complete Remittance Flow
| Step | Description | Status |
|------|-------------|--------|
| 1 | User greets assistant | ✅ |
| 2 | User says "quiero enviar $200 a mi mamá" | ✅ |
| 3 | System identifies recipient | ✅ |
| 4 | System shows exchange rate and fees | ✅ |
| 5 | User selects payment method | ✅ |
| 6 | System shows confirmation | ✅ |
| 7 | User confirms | ✅ |
| 8 | System shows success with confirmation # | ✅ |

### Scenario 2: Multi-Product Navigation
| Step | Description | Status |
|------|-------------|--------|
| 1 | User asks about wallet balance | ✅ |
| 2 | System shows balance | ✅ |
| 3 | User asks about credit | ✅ |
| 4 | System navigates and shows credit | ✅ |
| 5 | User requests top-up | ✅ |
| 6 | System navigates to top-ups | ✅ |
| 7 | User completes top-up | ✅ |

### Scenario 3: Escalation
| Step | Description | Status |
|------|-------------|--------|
| 1 | User starts a flow | ✅ |
| 2 | User requests human agent | ✅ |
| 3 | System acknowledges | ✅ |
| 4 | Session status = escalated | ✅ |

### Scenario 4: Admin Creates New Flow
| Step | Description | Status |
|------|-------------|--------|
| 1 | Admin opens subflow editor | ✅ |
| 2 | Admin creates states (drag-and-drop) | 🔲 |
| 3 | Admin connects with transitions | 🔲 |
| 4 | Admin configures state properties | ✅ |
| 5 | Admin saves flow | ✅ |
| 6 | Admin tests in simulator | 🔲 |
| 7 | Flow available in agent | ✅ |

---

## Testing Checklist

### Backend
- [x] Backend starts without errors
- [x] Database migrations run successfully
- [x] Seed data loads correctly
- [x] LLM retry logic works on failure
- [x] Confirmation timeout enforced
- [x] History compaction triggers at threshold

### Chat UI (React)
- [x] Chat UI connects to backend
- [x] Messages display correctly
- [x] Loading indicator shows
- [x] Confirmation buttons appear with countdown
- [x] New conversation button works
- [x] User selector works
- [x] User context sidebar displays

### Admin UI
- [x] Admin UI loads agent tree
- [x] Create new agent via Admin UI
- [x] Add tool to agent
- [x] Create subflow with states
- [x] Create response template
- [ ] Visual drag-and-drop builder
- [ ] Flow validation warnings
- [ ] Export flow as JSON
- [ ] Test flow in simulator

### Observability UI
- [ ] Conversation list loads
- [ ] Filters work (date, status)
- [ ] Search works
- [ ] Detail view shows messages
- [ ] Expandable prompt/tool details
- [ ] Flow path visualization

### End-to-End
- [x] Test chat conversation with agent
- [x] Verify tool execution
- [x] Verify subflow transitions
- [ ] Complete remittance demo scenario
- [ ] Complete multi-product navigation scenario
- [ ] Complete escalation scenario

---

## Implementation Priorities

### Phase 1: Core Functionality (Complete)
- ✅ Database models and migrations
- ✅ Chat API and orchestrator
- ✅ Admin API for configuration
- ✅ Basic Chat UI
- ✅ Basic Admin UI
- ✅ Mock services

### Phase 2: Enhanced Chat Experience (Complete)
- ✅ React migration (Chat UI + Admin UI with Vite + Zustand)
- ✅ Confirmation buttons in Chat UI with countdown timer
- ✅ Session management (new conversation, user switching)
- ✅ LLM error handling with exponential backoff retry
- ✅ Conversation history compaction with LLM summarization

### Phase 3: Visual Builder
- 🔲 Drag-and-drop canvas with pan/zoom
- 🔲 Minimap navigation
- 🔲 Visual state indicators
- 🔲 Real-time validation warnings
- 🔲 Flow testing simulator

### Phase 4: Observability
- 🔲 Conversation list with filters
- 🔲 Full conversation detail view
- 🔲 Prompt/tool call inspection
- 🔲 Flow path visualization

### Phase 5: Production Readiness
- 🔲 Admin authentication
- 🔲 Structured logging
- 🔲 Performance monitoring
- 🔲 Error tracking
