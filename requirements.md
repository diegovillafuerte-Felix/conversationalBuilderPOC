# Felix Conversational Orchestrator - Requirements Specification

**Last Updated:** January 2025  

---

## 1. Executive Summary

### 1.1 Purpose
This document defines the requirements for building a proof-of-concept (POC) conversational AI orchestrator for Felix Pago. The system will enable natural, context-aware conversations with users across multiple financial products through a hierarchical agent architecture.

### 1.2 Product Vision
Create an intelligent conversational interface that feels like talking to a knowledgeable support agent who knows everything about the user—their history, preferences, and context—while seamlessly navigating across Felix's product suite (remittances, credit, wallet, top-ups, bill payments).

### 1.3 Success Criteria
| Metric | Target |
|--------|--------|
| Complete end-to-end remittance flow via conversation | 100% functional |
| Average response latency | < 3 seconds |
| Successful agent navigation (routing accuracy) | > 90% |
| Confirmation flow completion rate | > 95% |
| Admin can create new agent via UI | Fully functional |
| Admin can create new subflow via visual builder | Fully functional |

### 1.4 Document Scope
This requirements specification covers the POC phase only. Production scaling, WhatsApp integration, and real backend service integration are explicitly out of scope.

---

## 2. User Stories and Requirements

### 2.1 User Roles

| Role | Description |
|------|-------------|
| End User | Felix customer interacting via chat |
| Admin | Felix team member managing agents/flows |
| Observer | Felix team member reviewing conversations |

---

### 2.2 Epic 1: Conversational Experience

**EP-001: As an end user, I want to have natural conversations with Felix that feel personalized and context-aware.**

#### US-001: Contextual Greeting
**As an** end user  
**I want** the assistant to greet me by name and acknowledge our relationship  
**So that** the conversation feels personal from the start

**Acceptance Criteria:**
- AC-001.1: Assistant uses user's preferred name in greeting
- AC-001.2: If user has recent activity, assistant can reference it naturally
- AC-001.3: Greeting adapts based on time of day (buenos días/tardes/noches)

**Priority:** Should Have

---

#### US-002: Product Navigation
**As an** end user  
**I want** to ask about any Felix product and be routed to the right specialist  
**So that** I get accurate help without having to navigate menus

**Acceptance Criteria:**
- AC-002.1: User can say "quiero enviar dinero" and be routed to remittances agent
- AC-002.2: User can say "cuánto debo en mi crédito" and be routed to credit agent
- AC-002.3: Routing happens transparently without explicit "transferring you" messages unless helpful
- AC-002.4: User can ask about multiple products in sequence

**Priority:** Must Have

---

#### US-003: Return Navigation
**As an** end user  
**I want** to go back to the main menu or previous context when I change topics  
**So that** I'm not stuck in a product flow when I need something else

**Acceptance Criteria:**
- AC-003.1: User can say "mejor ayúdame con otra cosa" to return to main orchestrator
- AC-003.2: User can naturally change topics mid-flow and system adapts
- AC-003.3: Pending operations are gracefully abandoned with optional save-for-later

**Priority:** Must Have

---

#### US-004: Conversation Continuity
**As an** end user  
**I want** the assistant to remember what we discussed earlier in the conversation  
**So that** I don't have to repeat myself

**Acceptance Criteria:**
- AC-004.1: Recent messages (last 2000 tokens) are included verbatim in context
- AC-004.2: Older messages are summarized but key decisions/preferences retained
- AC-004.3: User can reference "lo que dijiste antes" and assistant understands
- AC-004.4: Flow state data persists across messages within a session

**Priority:** Must Have

---

#### US-005: Human Escalation
**As an** end user  
**I want** to request a human agent when the bot can't help me  
**So that** I can resolve complex issues

**Acceptance Criteria:**
- AC-005.1: User can say "quiero hablar con alguien" at any point
- AC-005.2: System acknowledges escalation and provides expected wait time (mocked)
- AC-005.3: Conversation context is preserved for human agent handoff
- AC-005.4: Session status changes to "escalated"

**Priority:** Must Have

---

### 2.3 Epic 2: Financial Transactions

**EP-002: As an end user, I want to complete financial transactions through conversation with appropriate safeguards.**

#### US-006: Send Remittance Flow
**As an** end user  
**I want** to send money to my family in Mexico through conversation  
**So that** I can complete transfers without navigating complex UI

**Acceptance Criteria:**
- AC-006.1: User can initiate with "quiero enviar $200 a mi mamá"
- AC-006.2: System shows current exchange rate and fees
- AC-006.3: System confirms recipient details before proceeding
- AC-006.4: System shows full transaction summary before final confirmation
- AC-006.5: User must explicitly confirm before money moves
- AC-006.6: Success message includes confirmation number and estimated arrival

**Priority:** Must Have

---

#### US-007: Transaction Confirmation
**As an** end user  
**I want** clear confirmation requests before any money moves  
**So that** I don't accidentally send money to the wrong place

**Acceptance Criteria:**
- AC-007.1: All financial operations require explicit confirmation
- AC-007.2: Confirmation message clearly shows: amount, recipient, fees, total
- AC-007.3: Confirmation expires after 5 minutes
- AC-007.4: User can say "no" or "cancelar" to abort
- AC-007.5: System waits for confirmation before executing tool with side effects

**Priority:** Must Have

---

#### US-008: Check Transaction Status
**As an** end user  
**I want** to ask about my recent transfers  
**So that** I know if my money arrived

**Acceptance Criteria:**
- AC-008.1: User can ask "¿ya llegó mi envío?"
- AC-008.2: System shows status of most recent transfer by default
- AC-008.3: User can ask about specific transfer by confirmation number
- AC-008.4: Status includes: current state, last update, estimated completion

**Priority:** Should Have

---

#### US-009: Check Balances
**As an** end user  
**I want** to ask about my wallet balance and credit status  
**So that** I know my financial position with Felix

**Acceptance Criteria:**
- AC-009.1: User can ask "¿cuánto tengo en mi cartera?"
- AC-009.2: User can ask "¿cuánto debo?" for credit balance
- AC-009.3: Response includes available credit and minimum payment due
- AC-009.4: No confirmation required for read-only operations

**Priority:** Should Have

---

#### US-010: Send Top-Up
**As an** end user  
**I want** to send phone credit to a number in Mexico  
**So that** my family can stay connected

**Acceptance Criteria:**
- AC-010.1: User can say "recarga de $100 al celular de mi mamá"
- AC-010.2: System identifies carrier from phone number or asks
- AC-010.3: System shows available amounts for that carrier
- AC-010.4: Confirmation required before sending

**Priority:** Should Have

---

#### US-011: Pay Bills
**As an** end user  
**I want** to pay utility bills in Mexico  
**So that** I can help my family with household expenses

**Acceptance Criteria:**
- AC-011.1: User can say "quiero pagar la luz de mi mamá"
- AC-011.2: System can look up bill amount from account number
- AC-011.3: User can pay full amount or partial
- AC-011.4: Confirmation includes biller name and account details

**Priority:** Could Have

---

### 2.4 Epic 3: Admin Management

**EP-003: As an admin, I want to configure and manage the conversational system without code changes.**

#### US-012: Manage Agents
**As an** admin  
**I want** to create, edit, and delete product agents  
**So that** I can expand Felix's conversational capabilities

**Acceptance Criteria:**
- AC-012.1: Admin can create new agent with name, description, parent
- AC-012.2: Admin can configure model (gpt-4o, gpt-4o-mini, etc.) per agent
- AC-012.3: Admin can add system prompt additions
- AC-012.4: Admin can set context requirements (what data to fetch)
- AC-012.5: Admin can activate/deactivate agents
- AC-012.6: Changes take effect without system restart

**Priority:** Must Have

---

#### US-013: Manage Tools
**As an** admin  
**I want** to add and configure tools for each agent  
**So that** agents can perform actions on behalf of users

**Acceptance Criteria:**
- AC-013.1: Admin can add tool with name, description, parameters
- AC-013.2: Admin can configure API endpoint, method, headers, body template
- AC-013.3: Admin can mark tool as requiring confirmation
- AC-013.4: Admin can set confirmation message template with placeholders
- AC-013.5: Admin can classify side effects (none/read/write/financial)
- AC-013.6: Admin can configure response field mappings

**Priority:** Must Have

---

#### US-014: Visual Subflow Builder
**As an** admin  
**I want** to create conversation flows using a visual drag-and-drop editor  
**So that** I can design complex flows without writing code

**Acceptance Criteria:**
- AC-014.1: Canvas supports pan and zoom with minimap
- AC-014.2: Admin can drag to create state nodes
- AC-014.3: Admin can connect states with transition arrows
- AC-014.4: Admin can configure state properties in side panel (instructions, tools)
- AC-014.5: Admin can configure transition triggers (tool success/error, user intent)
- AC-014.6: Visual indicators show initial state (green) and final states (double border)
- AC-014.7: Real-time validation warns about orphan states and dead ends
- AC-014.8: Admin can save, load, and duplicate flows
- AC-014.9: Admin can export flow as JSON

**Priority:** Must Have

---

#### US-015: Response Templates
**As an** admin  
**I want** to define message templates for critical moments  
**So that** important messages are consistent and on-brand

**Acceptance Criteria:**
- AC-015.1: Admin can create template with trigger (tool success, state entry, etc.)
- AC-015.2: Admin can use {{placeholders}} for dynamic values
- AC-015.3: Admin can mark template as mandatory (must use) or suggested
- AC-015.4: Admin can preview template with sample data

**Priority:** Should Have

---

#### US-016: Test Flows in Builder
**As an** admin  
**I want** to test my subflows directly in the visual builder  
**So that** I can validate flows before publishing

**Acceptance Criteria:**
- AC-016.1: "Test" button opens chat overlay
- AC-016.2: Current state is highlighted on canvas during test
- AC-016.3: Admin can see state transitions in real-time
- AC-016.4: Admin can inject mock tool responses
- AC-016.5: Variable inspector shows current stateData

**Priority:** Should Have

---

### 2.5 Epic 4: Observability

**EP-004: As an observer, I want to review conversations and understand system behavior.**

#### US-017: Conversation List
**As an** observer  
**I want** to see a list of all conversations  
**So that** I can find and review specific interactions

**Acceptance Criteria:**
- AC-017.1: List shows: user, start time, duration, message count, status
- AC-017.2: Can filter by date range, status (active/completed/escalated)
- AC-017.3: Can search by conversation content
- AC-017.4: Can sort by recency or duration

**Priority:** Must Have

---

#### US-018: Conversation Detail View
**As an** observer  
**I want** to see the full detail of a conversation including internal state  
**So that** I can debug issues and understand system behavior

**Acceptance Criteria:**
- AC-018.1: Shows full message timeline with timestamps
- AC-018.2: Each assistant message is expandable to show:
  - Full prompt sent to LLM (with context sections labeled)
  - Raw LLM response
  - Tool calls with parameters and results
  - State transitions triggered
  - Model used and token counts
- AC-018.3: Shows user context snapshot at conversation start
- AC-018.4: Visual indicator of agent changes during conversation

**Priority:** Must Have

---

#### US-019: Flow Visualization in Review
**As an** observer  
**I want** to see which path a conversation took through a subflow  
**So that** I can understand the user journey

**Acceptance Criteria:**
- AC-019.1: When reviewing conversation that used a subflow, can open flow visualization
- AC-019.2: Path taken is highlighted on the state machine diagram
- AC-019.3: Can click on states to see messages exchanged at that point

**Priority:** Could Have

---

### 2.6 Epic 5: Chat Interface (POC)

**EP-005: As a tester, I want a functional chat interface to test the orchestrator.**

#### US-020: Basic Chat UI
**As a** tester  
**I want** a simple web chat interface  
**So that** I can interact with the orchestrator

**Acceptance Criteria:**
- AC-020.1: Text input field and send button
- AC-020.2: Message bubbles distinguish user vs assistant
- AC-020.3: Timestamps on messages
- AC-020.4: Auto-scroll to latest message
- AC-020.5: Loading indicator while waiting for response

**Priority:** Must Have

---

#### US-021: Confirmation Buttons
**As a** tester  
**I want** clickable confirmation buttons when required  
**So that** I can confirm transactions without typing

**Acceptance Criteria:**
- AC-021.1: When confirmation is pending, show "Confirmar" and "Cancelar" buttons
- AC-021.2: Buttons send appropriate response to orchestrator
- AC-021.3: Buttons are disabled after clicking or after timeout

**Priority:** Should Have

---

#### US-022: Session Management
**As a** tester  
**I want** to start new sessions and switch between users  
**So that** I can test different scenarios

**Acceptance Criteria:**
- AC-022.1: "New Conversation" button starts fresh session
- AC-022.2: Can select from preset test users with different profiles
- AC-022.3: Current user context visible in sidebar

**Priority:** Should Have

---

## 3. Functional Requirements

### 3.1 Core Orchestration

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-001 | System shall route user messages to appropriate product agent based on intent | Must Have |
| FR-002 | System shall maintain conversation session state across multiple messages | Must Have |
| FR-003 | System shall support hierarchical agent navigation (enter child, return to parent, go home) | Must Have |
| FR-004 | System shall execute tool calls and process results | Must Have |
| FR-005 | System shall require explicit user confirmation for tools marked as requiring confirmation | Must Have |
| FR-006 | System shall timeout pending confirmations after configurable duration (default 5 min) | Must Have |
| FR-007 | System shall support subflows with statechart-based state management | Must Have |
| FR-008 | System shall transition between states based on tool results or user intent | Must Have |
| FR-009 | System shall persist flow state data across messages within a session | Must Have |
| FR-010 | System shall support human escalation from any point in conversation | Must Have |

### 3.2 Context Assembly

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-011 | System shall assemble prompts with user profile data | Must Have |
| FR-012 | System shall include recent conversation messages (configurable token limit) | Must Have |
| FR-013 | System shall include compacted summary of older conversation history | Should Have |
| FR-014 | System shall include product-specific context when in product agent | Should Have |
| FR-015 | System shall fetch additional context based on agent's contextRequirements | Should Have |
| FR-016 | System shall update user context asynchronously after interactions | Should Have |
| FR-017 | System shall compact conversation history when it exceeds threshold | Should Have |

### 3.3 Admin Functions

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-018 | System shall support CRUD operations for agents | Must Have |
| FR-019 | System shall support CRUD operations for tools within agents | Must Have |
| FR-020 | System shall support CRUD operations for subflows | Must Have |
| FR-021 | System shall provide visual drag-and-drop editor for subflow creation | Must Have |
| FR-022 | System shall validate subflow definitions (no orphans, no dead ends) | Must Have |
| FR-023 | System shall support response templates with placeholder substitution | Should Have |
| FR-024 | System shall allow testing subflows within the visual editor | Should Have |
| FR-025 | System shall apply configuration changes without restart | Should Have |

### 3.4 Observability

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-026 | System shall log all conversations with full message history | Must Have |
| FR-027 | System shall log prompts sent to LLM for each interaction | Must Have |
| FR-028 | System shall log tool calls with parameters and results | Must Have |
| FR-029 | System shall log state transitions | Must Have |
| FR-030 | System shall provide UI to browse and search conversations | Must Have |
| FR-031 | System shall provide detailed view of individual conversations | Must Have |

---

## 4. Non-Functional Requirements

### 4.1 Performance

| ID | Requirement | Target | Priority |
|----|-------------|--------|----------|
| NFR-001 | Response latency (user message to response) | < 3 seconds (P90) | Must Have |
| NFR-002 | Context assembly time | < 500ms | Should Have |
| NFR-003 | Admin UI page load time | < 2 seconds | Should Have |

### 4.2 Reliability

| ID | Requirement | Target | Priority |
|----|-------------|--------|----------|
| NFR-004 | System uptime during POC testing | 95% | Should Have |
| NFR-005 | Graceful handling of LLM API failures | Retry with fallback message | Must Have |
| NFR-006 | No data loss on service restart | Session state persisted | Must Have |

### 4.3 Usability

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR-007 | Conversation interface shall be usable on desktop browsers (Chrome, Firefox, Safari) | Must Have |
| NFR-008 | Admin UI shall be usable without training documentation | Should Have |
| NFR-009 | Visual flow builder shall support keyboard shortcuts for common actions | Could Have |

### 4.4 Maintainability

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR-010 | Code shall follow consistent style guide | Should Have |
| NFR-011 | API endpoints shall be documented | Should Have |
| NFR-012 | System shall use structured logging | Must Have |

### 4.5 Security (POC Level)

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR-013 | API keys shall not be exposed in client code | Must Have |
| NFR-014 | Admin UI shall require authentication (basic auth acceptable for POC) | Should Have |

---

## 5. Data Requirements

### 5.1 Data Entities

| Entity | Description | Persistence |
|--------|-------------|-------------|
| Agent | Product agent configuration | Database |
| Tool | Tool definition within agent | Database |
| Subflow | Statechart flow definition | Database |
| State | State within a subflow | Database (embedded in Subflow) |
| Transition | Transition between states | Database (embedded in Subflow) |
| ResponseTemplate | Message template | Database |
| ConversationSession | Active conversation state | Database + Cache |
| UserContext | User profile and summaries | Database |
| ConversationHistory | Message history | Database |
| Message | Individual message | Database (embedded) |

### 5.2 Data Retention

| Data Type | Retention | Notes |
|-----------|-----------|-------|
| Conversations | Indefinite (POC) | For debugging and review |
| Session state | 24 hours after last activity | Can be extended |
| User context | Indefinite (POC) | Updated after each transaction |

---

## 6. Interface Requirements

### 6.1 External Interfaces

| Interface | Type | Description |
|-----------|------|-------------|
| OpenAI API | REST | LLM completions with function calling |
| Mock Services | REST | Dummy backend services for POC |

### 6.2 Internal Interfaces

| Interface | Type | Description |
|-----------|------|-------------|
| Orchestrator API | REST/WebSocket | Chat interface to orchestrator |
| Admin API | REST | CRUD operations for configuration |
| Observability API | REST | Conversation retrieval and search |

---

## 7. Acceptance Criteria Summary

### 7.1 POC Demo Scenarios

The POC will be considered successful if the following scenarios can be demonstrated:

**Scenario 1: Complete Remittance Flow**
1. User greets assistant
2. User says "quiero enviar $200 a mi mamá"
3. System identifies recipient from saved recipients
4. System shows exchange rate and fees
5. User selects payment method
6. System shows confirmation with all details
7. User confirms
8. System shows success message with confirmation number

**Scenario 2: Multi-Product Navigation**
1. User asks about wallet balance
2. System shows balance
3. User asks "¿y cuánto debo en mi crédito?"
4. System navigates to credit and shows balance
5. User says "mejor quiero hacer una recarga"
6. System navigates to top-ups
7. User completes top-up flow

**Scenario 3: Escalation**
1. User starts a flow
2. User says "esto es muy complicado, quiero hablar con alguien"
3. System acknowledges and escalates
4. Session status changes to escalated

**Scenario 4: Admin Creates New Flow**
1. Admin opens subflow editor
2. Admin creates 3 states using drag-and-drop
3. Admin connects states with transitions
4. Admin configures state instructions and tools
5. Admin saves flow
6. Admin tests flow in simulator
7. Flow is available in product agent

### 7.2 Quality Gates

| Gate | Criteria |
|------|----------|
| Development Complete | All Must Have requirements implemented |
| Testing Complete | All demo scenarios pass |
| POC Approved | Stakeholder sign-off on demo |

---