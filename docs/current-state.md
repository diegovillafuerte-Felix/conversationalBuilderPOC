# Current State

## Implemented

Multi-agent orchestration, all product agents (remittances, credit, topups, billpay, wallet), tool execution with mock backends, stateful subflows, confirmation handling, history compaction, debug panel, i18n (es/en), React UI, admin CRUD API.

## Remittances Agent (Full Implementation)

- Supports 7 countries: MX, GT, HN, CO, DO, SV, NI
- 17 tools: 3 flow triggers, 8 info tools, 4 action tools, 2 navigation tools
- 3 subflows: `send_money_flow` (8 states), `add_recipient_flow` (6 states), `quick_send_flow` (3 states)
- Delivery methods: Bank, Cash, Wallet (Nequi/Daviplata/Mercado Pago), Debit Card
- KYC-based limits with 3 levels
- Response templates for success/error scenarios

## Routing System

- Explicit routing via `routing` field in ToolConfig (no string parsing inference)
- `AgentRegistry` validates all routing targets exist at startup (fail-fast)
- `RoutingHandler` provides unified execution for: enter_agent, start_flow, navigation
- Supports cross-agent flows via `cross_agent` field (e.g., SNPL → remittances flow)
- AgentConfig and SubflowConfig use `config_id` for stable identifier lookups
- Tool configs can use `routing` (explicit) or `starts_flow` (legacy) fields
- Invalid routing configs prevent application startup with clear error messages

## Declarative State Transitions

- **State-level transitions**: The `transitions` list in SubflowStateConfig is evaluated after service tool execution
- **tool_trigger field**: Explicit mapping from tool name to transition (e.g., `"tool_trigger": "detect_carrier"`)
- **Condition evaluation**: Supports `key is not None`, `key in stateData`, `key == 'value'`, nested paths (`_tool_result.carrier`)
- **First match wins**: Transitions are evaluated in config order
- **Automatic state change**: When a transition matches, the system transitions to the target state and signals chain continuation
- **Tool result storage**: Tool results are stored in stateData as `_result_{tool_name}` for condition evaluation
- **Condition utilities**: `context_enrichment.py` provides `evaluate_condition()` for declarative transition evaluation

## Services Gateway

- **Independent deployment**: Services run in separate Docker container (port 8001)
- **REST API**: All services exposed via `/api/v1/{service}/*` endpoints
- **7 service modules**: remittances, snpl, topups, billpay, wallet, financial_data, campaigns
- **60+ endpoints**: Full coverage of all service methods
- **HTTP client**: `backend/app/clients/service_client.py` handles all service communication
- **Service mapping**: `backend/app/clients/service_mapping.py` maps tool names to endpoints
- **Headers**: `X-User-Id` for user context, `Accept-Language` for i18n
- **Response format**: `{"success": true, "data": {...}}` or `{"success": false, "error": "...", "error_code": "..."}`

## JSON-Only Agent Configuration

- Dataclasses in `config_types.py` define AgentConfig, ToolConfig, SubflowConfig, SubflowStateConfig, ResponseTemplateConfig
- In-memory `AgentRegistry` singleton loads all agent configs from JSON at startup
- Synchronous lookups (no async DB queries)
- Startup validation: Registry validates all routing targets exist — fail-fast on invalid configs
- Hot reload: Admin endpoint `/api/admin/agents/reload` reinitializes registry

## Prompt Architecture Optimization

- **Prompt Modes**: `ContextAssembler` supports `FULL` (default) and `ROUTING` modes
  - `FULL`: Full context with all sections (~3000 tokens)
  - `ROUTING`: Minimal context for routing decisions (~500 tokens)
- **Token savings**: ~80% reduction for routing chain iterations

## Default Tools Whitelist

- `default_tools` field in AgentConfig for tool whitelisting when not in a flow
- Tool selection priority: 1) Flow state_tools → 2) Agent default_tools → 3) All agent tools
- Configured agents: remittances.json (6 default tools), snpl.json (6 default tools)
- ~70% tool token reduction for agents with many tools

## Event Tracing

- Debug system for tracking routing, tool calls, and orchestration flow
- `EventTracer` class captures events during message processing
- Categories: session, agent, flow, routing, LLM, tool, service, error
- `EventTracePanel.jsx` displays trace events in React UI

## Visualization System

- `VisualizePage.jsx` — agent hierarchy, state machine, tool catalog
- Uses React Flow for interactive diagrams

## E2E Conversation Testing

- Framework in `backend/tests/e2e/` — runs multi-turn conversations against live servers
- Design philosophy: Framework produces rich readable output; quality judgment comes from Claude Code reading the output
- 5 scenarios (3 smoke + 2 multi-turn) with structural gates
- Pytest wrapper for CI-style regression

## Infrastructure (Feb 2026)

- **Linting**: ruff for both backend and services (lint + format)
- **Type checking**: mypy on backend (permissive start)
- **CI**: GitHub Actions with 4 parallel jobs (lint, typecheck, test-unit, test-services)
- **Architecture tests**: AST-based import boundary enforcement
- **Convention tests**: Tool naming, config validity, service layer rules
- **Doc freshness tests**: Verify key files and directories exist
- **Makefile**: Single entry point for all checks (`make check`)

## Planned

Analytics dashboard, WhatsApp integration, real backend services, auth, rate limiting.
