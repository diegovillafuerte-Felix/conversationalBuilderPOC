# Design Decisions

Architectural rationale for key choices in the system.

## No Recursion in Routing Chain

**Decision**: The routing chain iterates until stable state rather than using recursive agent calls.

**Why**: Recursive routing creates unpredictable call stacks and makes debugging difficult. The iterative approach has a clear loop with explicit exit conditions (stable state, loop detection, max iterations). Each iteration is independent — load agent, build context, call LLM, process tools. This makes the flow easy to trace and debug via event tracing.

**Trade-off**: The iterative model requires explicit chain state tracking (`ChainState` dataclass) and loop detection. But this is simpler than managing recursive call stacks.

## Raw-Data-Only Services

**Decision**: Service methods return ONLY raw data (dicts/lists). No formatting, no `_message` fields, no user-facing strings.

**Why**: Services should be UI-agnostic. The same `get_exchange_rate` call should work for a chat interface, a web dashboard, a mobile app, or a direct API consumer. If services embed formatting, every new client needs to strip it out or work around it.

**Enforcement**: The convention test `TestServiceConventions.test_no_message_fields_in_services` scans all service files for `_message` field usage.

**Trade-off**: The LLM or response templates must handle ALL formatting. This adds a bit of complexity to the presentation layer but keeps the service layer clean and reusable.

## JSON Configs Instead of Database

**Decision**: Agent definitions (tools, subflows, prompts) are stored as JSON files, not in the database.

**Why**:
1. **Version control**: JSON files are in git — full history, diffs, PRs, blame
2. **Speed**: In-memory `AgentRegistry` lookups are synchronous, no async DB queries
3. **Simplicity**: No ORM models for agent/tool/subflow, no DB migrations for config changes
4. **Team workflow**: Product teams edit their agent JSON directly, no admin UI required
5. **Startup validation**: Registry validates all routing targets exist — catches misconfigs immediately

**Trade-off**: No runtime config editing without file system access (mitigated by admin API that writes to JSON files and hot-reloads).

## Separate Services Gateway

**Decision**: Mock backend services run as an independent FastAPI app on port 8001, not embedded in the main backend.

**Why**:
1. **Realistic architecture**: Production will have real backend services as separate deployments
2. **Independent development**: Services team and orchestration team can work independently
3. **Clear contract**: REST API with defined schemas forces explicit contracts
4. **Easy swap**: When real services are ready, just change the URL — the HTTP client interface stays the same

**Trade-off**: Extra deployment complexity (two services instead of one), HTTP overhead for service calls. But the architectural clarity is worth it for a system that will eventually connect to real backends.

## Agent Isolation

**Decision**: Each agent is ignorant of other agents. Agents can only interact via their assigned tools (navigation tools like `enter_<agent>` or `go_home`).

**Why**: Agent isolation enables team ownership. The remittances team can modify their agent config without understanding or affecting the credit agent. The orchestrator handles routing; agents just respond within their domain.

**Trade-off**: Cross-agent features require explicit routing config (`cross_agent` field). You can't have one agent directly call another's tools. But this prevents coupling between product domains.

## Explicit Routing (No Inference)

**Decision**: Routing is configured via the `routing` field in ToolConfig. The system does NOT infer routing from tool names or string patterns.

**Why**: Implicit routing (e.g., "any tool starting with `enter_` routes to an agent") is fragile and hard to debug. Explicit routing means every routing decision is declared in config and validated at startup. If a routing target doesn't exist, the app fails to start with a clear error message.

**Enforcement**: Architecture test validates routing targets reference existing agents/subflows.

## LLM-Driven Formatting

**Decision**: The LLM handles all user-facing formatting. No hardcoded response strings in the orchestration layer.

**Why**: The LLM can adapt formatting to context — language, conversation history, user preferences. Hardcoded strings can't do this. Response templates provide consistent formatting for specific scenarios (e.g., transfer confirmations), while the LLM handles dynamic content.

**Trade-off**: Slightly less deterministic responses. But for a conversational interface, natural language variation is a feature, not a bug.
