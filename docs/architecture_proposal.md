# Proposed Conversational Architecture: Enabling Multi-Product Development

## The Problem

Our current conversations-api was built to do one thing well: guide users through sending remittances via WhatsApp. It succeeded at that. But the architecture that made it work for a single product is now the primary obstacle to becoming a multi-product company.

**The core issue is coupling.** Every piece of logic—business rules, conversation flow, message formatting, product-specific behavior—lives in one intertwined codebase of 100,000+ lines of Python. When the Credit team wants to add a new loan flow, they must modify the same behavior tree that handles remittances. When the Wallet team wants to change how balances are displayed, they're editing files alongside remittance confirmation logic. When we want to improve intent recognition, we're navigating through 988 Python files just in the flow builder module.

This coupling creates three concrete problems:

**1. Slow feature velocity.** Adding a new partner flow is rated "high effort" in our own documentation—it requires implementing a full behavior tree subtree, understanding implicit blackboard dependencies, and coordinating with whoever else is touching the same files. The delivery method subtree alone has 179 files. Every new product we add makes the next one harder.

**2. High coordination cost.** Teams cannot work independently. A change to how we collect beneficiary information affects remittances, credit disbursements, and any future product that sends money. There's no way for the Credit team to ship their feature without the Chat team reviewing it, because there's no boundary between their code.

**3. Fragile deployments.** One codebase means one deployment. A bug in credit logic can take down remittances. A performance issue in the new top-ups flow affects everyone. Teams are afraid to ship because the blast radius is the entire product.

The behavior tree architecture compounds these problems. Flow logic is implicit—encoded in Python class hierarchies and selector/sequence node arrangements, not in readable configuration. Understanding "what happens when a user says X" requires tracing through dozens of files. The blackboard (shared state) creates hidden dependencies that only surface at runtime. Adding a new condition means understanding how it interacts with hundreds of existing conditions.

We built a system optimized for one product with one team. We now have five teams trying to build five products in that same system.

---

## The Proposed Solution: Service-Oriented Architecture with Clear Boundaries

We propose replacing the monolithic behavior tree with a layered architecture where each layer has one job and teams own distinct pieces.

**Three layers, three responsibilities:**

```
┌─────────────────────────────────────────────────────────────┐
│  ORCHESTRATION LAYER (Platform Team)                        │
│  "Route the conversation to the right place"                │
│  - Understands user intent via LLM                          │
│  - Routes to specialized product agents                     │
│  - Manages conversation state and multi-step flows          │
│  - Handles confirmations and escalations                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTP/REST API
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  SERVICES LAYER (Product Teams)                             │
│  "Execute business logic, return data"                      │
│  - Remittances service (Chat team)                          │
│  - Credit service (Credit team)                             │
│  - Wallet service (Wallet team)                             │
│  - Top-ups, Bill Pay, P2P (New Products team)               │
│  Each service: independent deployment, own database, own API │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ Structured data (JSON)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  PRESENTATION LAYER (Platform Team + Product Teams)         │
│  "Format responses for users"                               │
│  - LLM generates natural language from data                 │
│  - Response templates for consistent messaging              │
│  - Supports any channel: WhatsApp, web, mobile app          │
└─────────────────────────────────────────────────────────────┘
```

**The key insight: services return data, not messages.** When the remittances service calculates an exchange rate, it returns `{"rate": 17.45, "from": "USD", "to": "MXN"}`. It does not return "El tipo de cambio es 17.45 pesos por dólar." The orchestration layer—using LLM or templates—handles all user-facing text.

This separation would mean: the Credit team can modify how credit limits are calculated without touching any conversation logic. The Platform team can improve how we explain exchange rates without touching the calculation. Neither team needs to coordinate with the other.

---

## Ownership Model: Teams Control Their Own Experience

A critical principle of this proposal is **distributed ownership with clear boundaries**. We propose a model where product teams own not just their backend services, but also the conversational experience for their product—without needing to touch platform code.

**How it would work:**

Each product has an **agent configuration**—a JSON file that defines:
- The agent's personality and instructions
- What tools (actions) the agent can use
- Multi-step flows and their states
- Response templates for common scenarios

These configuration files would live in a **central repository** accessible to all teams. A configuration management UI would handle permissions and approval flows—ensuring teams can only modify their own agents while preventing conflicting changes.

**Ownership boundaries:**

| Team | Owns | Cannot Touch |
|------|------|--------------|
| Platform | Orchestration infrastructure, root agent config, routing logic | Product-specific agent configs |
| Chat (Remittances) | Remittances agent config, remittances service | Credit, Wallet, other agent configs |
| Credit | Credit agent config, credit service | Remittances, Wallet, other agent configs |
| Wallet | Wallet agent config, wallet service | Other agent configs |
| New Products | Top-ups/Bill Pay/P2P agent configs and services | Other agent configs |

**Agent isolation is enforced by design.** Each agent would be completely ignorant of every other agent. A product agent cannot directly call another product's service or reference another agent's flows. The only way to interact across boundaries is through the tools explicitly assigned to that agent—and those tools are the API contract negotiated between teams.

For example, the Credit agent might have a `disburse_via_remittance` tool that calls the remittances service. But the Credit agent doesn't know how remittances work internally—it just calls a tool and gets a result. If the Chat team changes how remittances are processed, the Credit agent is unaffected as long as the tool contract holds.

This means:
- **Product teams control their user experience** within the bounds of the routing architecture
- **Changes are isolated**—modifying the credit flow cannot break remittances
- **The Platform team focuses on infrastructure**, not product-specific conversations
- **Approval flows prevent chaos** while enabling autonomy

---

## Configuration Over Code

In the current system, adding a new conversation flow requires writing Python—behavior tree nodes, conditions, actions, blackboard management. Understanding the flow requires reading code.

In the proposed architecture, flows would be defined in JSON:

```json
{
  "id": "send_money_flow",
  "states": [
    {
      "state_id": "select_recipient",
      "agent_instructions": "Ask user to select a recipient from their saved list or add a new one",
      "on_enter": {
        "callTool": "list_recipients"
      },
      "transitions": [
        {"condition": "recipient_id is not None", "target": "collect_amount"}
      ]
    },
    {
      "state_id": "collect_amount",
      "agent_instructions": "Ask how much to send, show exchange rate",
      "state_tools": ["get_exchange_rate", "create_quote"]
    }
  ]
}
```

A product manager can read this and understand the flow. A new engineer can modify it without understanding the entire codebase. Product teams can adjust their conversation behavior without touching platform code. The flow is explicit, not implicit in code structure.

Agent capabilities would also be configuration:

```json
{
  "id": "remittances",
  "name": "Remittances Agent",
  "description": "Handles international money transfers",
  "tools": ["list_recipients", "get_exchange_rate", "create_transfer", ...],
  "subflows": ["send_money_flow", "add_recipient_flow"],
  "navigation": {"canGoUp": true, "canEscalate": true}
}
```

Adding a new product agent wouldn't require touching remittances code or configuration. It would be a new JSON file (owned by that product team) and a new service.

---

## Why LLM Routing Instead of Behavior Trees

Behavior trees are deterministic: given input X, always take path Y. This is good for reliability but bad for natural conversation. Users don't follow scripts. They say "actually, never mind, I want credit instead" in the middle of a remittance flow. They ask about their wallet balance while confirming a transfer.

The current system handles this with increasingly complex condition nodes—explicit checks for every possible user deviation. Each new case adds more nodes, more implicit dependencies, more files to maintain.

The proposed architecture would use LLM-based routing: the AI understands intent from natural language and routes to the appropriate agent or flow. "Actually, I want credit instead" would naturally route to the credit agent, even mid-remittance. The conversation feels natural because the routing is natural.

But LLM routing wouldn't be magic or unpredictable. The system would have explicit boundaries:

- **Validated routing targets**: At startup, the system would verify every routing destination exists. Invalid configurations would fail immediately, not at runtime.
- **Structured tools**: Agents could only call defined tools with defined parameters. The LLM decides *when* to call them, not *what* they can do.
- **Confirmation gates**: Sensitive actions (sending money, applying for credit) would always require explicit user confirmation before execution.
- **Deterministic flows**: Multi-step processes (send money flow) would use state machines with defined transitions. The LLM operates within the structure, not around it.

We would get natural conversation without sacrificing predictability.

---

## What This Architecture Would Enable

**Faster time to market.** Adding a new product would involve:
1. Create a service with business logic (product team, their pace)
2. Create an agent JSON config (product team, days not weeks)
3. Define tools that call the service (contract negotiation with Platform team)
4. Submit config through approval flow, deploy independently

Compare to current: implement full behavior tree subtree, understand blackboard dependencies, coordinate with everyone touching the same codebase.

**True team autonomy.** Product teams would own their conversational experience end-to-end—from service logic to agent behavior—without needing Platform team involvement for every change. The Credit team could iterate on their loan application flow daily if they wanted, without affecting anyone else.

**Reduced blast radius.** Services and agent configs would be isolated. A bug in credit couldn't take down remittances. A misconfigured flow in one agent couldn't affect others. Each team would have their own error boundaries, monitoring, and rollback capability.

**Easier debugging.** Conversation flow would be visible in JSON configuration, not buried in 988 Python files. Event tracing would show exactly which agent handled a message, which tools were called, which service endpoints were hit. When something goes wrong, finding the cause would take minutes, not hours.

**Multi-channel ready.** Because services return data (not formatted messages), the same business logic could serve WhatsApp, web app, mobile app, and direct API access. The presentation layer would adapt to the channel. Adding a new channel would mean adding a new presentation adapter, not rewriting business logic.

---

## The Cost of Not Changing

Every month we continue with the current architecture, we accumulate more behavior tree nodes, more implicit dependencies, more coordination overhead. The system that made us successful with one product is actively preventing us from becoming multi-product.

The teams are already experiencing this:
- Feature work takes longer because of cross-team dependencies
- Deployments are risky because of shared codebase
- Onboarding is slow because understanding the system requires understanding all of it
- Adding new products requires copying and modifying existing flows rather than composing independent pieces

This proposal isn't about replacing something broken. It's about building the foundation for the next phase of the company. The current architecture was the right choice for a single-product startup. It's the wrong choice for a multi-product company with multiple independent teams.

---

## Summary: The Objectives We're Pursuing

| Objective | Current State | Proposed Architecture |
|-----------|---------------|----------------------|
| Team autonomy | Low - shared codebase, implicit dependencies | High - teams own their configs and services |
| Adding products | Weeks (full subtree implementation) | Days (JSON config + service) |
| Deployment independence | None - single deployment | Full - each service and config deploys separately |
| Blast radius | Entire system | Isolated to single agent/service |
| Flow visibility | Implicit in 988 Python files | Explicit in JSON configuration |
| Cross-team coordination | Required for most changes | Required only for API contracts |
| Multi-channel support | Tightly coupled to WhatsApp | Presentation layer adapts per channel |

---

*This document describes the proposed conversational architecture direction. Implementation details, migration path, and timeline would be developed upon alignment on these objectives.*
