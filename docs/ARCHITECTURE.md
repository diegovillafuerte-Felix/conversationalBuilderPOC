# Felix Conversational Orchestrator - Architecture Guide

> A deep dive into how Felix works, designed for anyone curious about conversational AI systems.

---

## Table of Contents

1. [What is Felix?](#what-is-felix)
2. [The Big Picture](#the-big-picture)
3. [Core Concepts](#core-concepts)
4. [How a Message Flows Through the System](#how-a-message-flows-through-the-system)
5. [The Agent Hierarchy](#the-agent-hierarchy)
6. [Tools: How Agents Take Action](#tools-how-agents-take-action)
7. [Subflows: Multi-Step Conversations](#subflows-multi-step-conversations)
8. [The Shadow Service: Contextual Intelligence](#the-shadow-service-contextual-intelligence)
9. [State Management: Remembering Context](#state-management-remembering-context)
10. [Why This Architecture?](#why-this-architecture)
11. [Technical Reference](#technical-reference)

---

## What is Felix?

Felix is a **conversational AI assistant** that helps users with financial services like:

- Sending money to family abroad (remittances)
- Topping up mobile phones
- Paying bills
- Managing credit and loans (SNPL - Send Now Pay Later)

Instead of clicking through menus, users simply chat naturally:

```
User: "I want to send $200 to my mom in Mexico"
Felix: "I'd be happy to help you send money to Mexico!
        I see you have Maria Garcia saved as a recipient.
        Would you like to send to her?"
```

**What makes Felix special:**

- **Natural conversation** - No rigid menus or forms
- **Smart routing** - Automatically connects you to the right specialist
- **Contextual help** - Proactively offers relevant tips and promotions
- **Multi-step flows** - Guides you through complex processes step by step
- **Safe confirmations** - Always confirms before executing financial transactions

---

## The Big Picture

At its core, Felix is a **multi-agent system** where specialized AI agents collaborate to help users. Think of it like a company with different departments:

```
                            ┌─────────────────────────────────────┐
                            │           Felix (Main)              │
                            │      "How can I help today?"        │
                            └─────────────┬───────────────────────┘
                                          │
              ┌───────────────┬───────────┼───────────┬───────────────┐
              │               │           │           │               │
              ▼               ▼           ▼           ▼               ▼
        ┌───────────┐  ┌───────────┐ ┌─────────┐ ┌─────────┐  ┌───────────┐
        │Remittances│  │  Top-Ups  │ │Bill Pay │ │  SNPL   │  │ Financial │
        │  Agent    │  │   Agent   │ │  Agent  │ │  Agent  │  │  Advisor  │
        │           │  │           │ │         │ │         │  │  (Shadow) │
        │ "Send $   │  │ "Recharge │ │ "Pay    │ │ "Apply  │  │           │
        │  abroad"  │  │  phones"  │ │ bills"  │ │ for a   │  │ "Budget & │
        └───────────┘  └───────────┘ └─────────┘ │  loan"  │  │  savings" │
                                                 └─────────┘  └───────────┘
```

**Each agent is a specialist:**
- The main Felix agent is the "receptionist" who understands what you need
- Specialized agents handle specific domains with deep expertise
- Agents can hand off to each other seamlessly
- Financial Advisor is a **shadow agent** that activates when users need budgeting/savings help

> **Note:** Wallet functionality exists as a **service** (for balance checks, history) but not as a dedicated conversational agent. Wallet data is accessed by other agents as needed.

---

## Core Concepts

Before diving deeper, let's define the key building blocks:

### 1. **Agents**
An agent is an AI personality with specific expertise. Each agent has:
- A **description** of what it handles
- A set of **tools** it can use
- **Subflows** for multi-step processes
- **Navigation rules** (can it go back? escalate to human?)

### 2. **Tools**
Tools are actions an agent can take. Examples:
- `get_exchange_rate` - Look up currency conversion rates
- `create_transfer` - Initiate a money transfer
- `enter_remittances` - Switch to the remittances specialist

### 3. **Subflows**
A subflow is a guided multi-step conversation. Like filling out a form, but through natural dialogue:
- "Send Money Flow" walks through: recipient → amount → delivery method → confirmation

### 4. **Sessions**
A session tracks one conversation, including:
- Which agent is currently active
- What step of a flow you're on
- Data collected so far
- Confirmation state

### 5. **Shadow Service**
A parallel system that watches the conversation and can inject helpful tips or promotions without interrupting the main flow.

---

## How a Message Flows Through the System

When you send a message to Felix, here's what happens behind the scenes. The system uses a **Routing Chain Architecture** that loops until reaching a "stable state" - eliminating extra turns when routing between agents.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    ROUTING CHAIN MESSAGE FLOW DIAGRAM                         │
└──────────────────────────────────────────────────────────────────────────────┘

    User: "Quiero una recarga"
              │
══════════════╪══════════════════════════════════════════════════════════════
              │        PHASE 1: SETUP
══════════════╪══════════════════════════════════════════════════════════════
              ▼
    ┌─────────────────────┐
    │   1. API Endpoint   │   Receives the HTTP request
    │   (routes/chat.py)  │
    └─────────┬───────────┘
              │
              ▼
    ┌─────────────────────┐
    │ 2. Load Session     │   Retrieve or create conversation state
    │   (StateManager)    │   - Current agent, flow state, history
    └─────────┬───────────┘
              │
══════════════╪══════════════════════════════════════════════════════════════
              │        PHASE 2: ROUTING CHAIN (LOOPS UNTIL STABLE)
══════════════╪══════════════════════════════════════════════════════════════
              ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │                      ROUTING CHAIN LOOP                              │
    │                      (max 3 iterations)                              │
    │  ┌───────────────────────────────────────────────────────────────┐  │
    │  │                                                               │  │
    │  │  ┌─────────────────────┐                                      │  │
    │  │  │ 3. Get Current Agent│   May have changed from last iter    │  │
    │  │  └─────────┬───────────┘                                      │  │
    │  │            │                                                  │  │
    │  │            ▼                                                  │  │
    │  │  ┌─────────────────────┐                                      │  │
    │  │  │ 4. Context Enrich   │   Auto-execute on_enter.callTool     │  │
    │  │  │ (if state changed)  │   Fetch data before LLM call         │  │
    │  │  └─────────┬───────────┘                                      │  │
    │  │            │                                                  │  │
    │  │            ▼                                                  │  │
    │  │  ┌─────────────────────┐                                      │  │
    │  │  │ 5. Build Context &  │   Assemble prompt with enriched data │  │
    │  │  │    Call LLM         │   Get response + tool calls          │  │
    │  │  └─────────┬───────────┘                                      │  │
    │  │            │                                                  │  │
    │  │            ▼                                                  │  │
    │  │  ┌─────────────────────┐                                      │  │
    │  │  │ 6. Process Tools    │   Handle tool calls:                 │  │
    │  │  │                     │   - Routing → state changes          │  │
    │  │  │                     │   - Service → HTTP calls             │  │
    │  │  └─────────┬───────────┘   - Confirmation → pause             │  │
    │  │            │                                                  │  │
    │  │            ▼                                                  │  │
    │  │  ┌─────────────────────┐                                      │  │
    │  │  │ 7. Check Exit       │                                      │  │
    │  │  │    Conditions       │   Exit if:                           │  │
    │  │  │                     │   • No routing occurred (stable!)    │  │
    │  │  │                     │   • Confirmation pending             │  │
    │  │  │                     │   • Error occurred                   │  │
    │  │  │                     │   • Loop detected                    │  │
    │  │  └─────────┬───────────┘   • Max iterations reached           │  │
    │  │            │                                                  │  │
    │  │            │ routing_occurred?                                │  │
    │  │            │                                                  │  │
    │  │       YES ─┴─► LOOP BACK ─────────────────────────────────────┘  │
    │  │                (continue with new agent context)                 │
    │  │                                                                  │
    │  └──────────────────────────────────────────────────────────────────┘
    │              │                                                       │
    │         NO ──┴─► EXIT LOOP (stable state reached)                    │
    └──────────────────────────────────────────────────────────────────────┘
              │
══════════════╪══════════════════════════════════════════════════════════════
              │        PHASE 3: FINAL RESPONSE
══════════════╪══════════════════════════════════════════════════════════════
              ▼
    ┌─────────────────────┐
    │ 8. Shadow Service   │   Runs ONLY after chain completes
    │    (Final State)    │   Evaluates final agent context
    └─────────┬───────────┘   for tips/promotions
              │
              ▼
    ┌─────────────────────┐
    │ 9. Return Response  │   Send back to user:
    │                     │   - Message from stable agent
    └─────────────────────┘   - Debug info (chain iterations, path)
                              - Shadow tips (if any)
              │
              ▼

    TopUps: "¡Perfecto! Veo que tienes estos números guardados:
             1. Mamá (+52 55 1234 5678)
             2. Hermano (+52 33 8765 4321)
             ¿A cuál número quieres enviar la recarga?"

    ─────────────────────────────────────────────────────────────────
    Note: User asked "Quiero una recarga" and received the TopUps
    response directly - NO extra turn required! The chain handled:
    Iteration 1: Felix → enter_topups (routing)
    Iteration 2: TopUps → start_flow_recarga (routing)
    Iteration 3: TopUps flow → shows numbers (stable - no routing)
```

### Key Architectural Insights

**1. Routing Chain (Eliminates Extra Turns)**

The old architecture required extra user messages after routing:
```
Old behavior (defect):                New behavior (routing chain):
User: "Quiero recarga"               User: "Quiero recarga"
Felix: "Te conecto con recargas"     TopUps: "Veo tus números: 1.Mamá..."
User: (sends any message)            (Single response!)
TopUps: "Veo tus números: 1.Mamá..."
```

The routing chain loops until **stable state** (no routing tools called):
- Each iteration: enrich → LLM call → process tools
- If routing occurred, loop continues with new agent
- When no routing, user gets final response immediately
- Max 3 iterations prevents infinite loops

**2. Proactive Context Enrichment**

Instead of waiting for the LLM to call tools like `get_frequent_numbers`, the system **automatically** executes these when entering a flow state:

```
Before (reactive):                    After (proactive):
User: "Quiero recarga"               User: "Quiero recarga"
→ LLM: "¿A qué número?"              → System auto-loads frequent numbers
→ LLM calls get_frequent_numbers     → LLM already has the data
→ LLM: "Veo que tienes..."           → LLM: "Veo que tienes 1.Mamá 2.Hermano"
```

**3. Shadow Service (Final State Only)**

The Shadow Service runs **after** the routing chain completes:
- Evaluates the final agent/flow context
- No wasted evaluation on intermediate routing states
- Tips are relevant to where the user actually landed

**4. Services Gateway (HTTP)**

Services are **independently deployed** and communicate via HTTP:
- Backend (port 8000) ←→ Services Gateway (port 8001)
- Enables independent scaling and deployment
- Same API can be used by web app, mobile app, etc.

---

## The Agent Hierarchy

Agents are organized in a tree structure. This provides:

1. **Clear responsibility** - Each agent knows its domain
2. **Seamless handoffs** - Users move between agents naturally
3. **Scoped tools** - Each agent only sees relevant tools

```
                    Felix (Root Agent)
                    ├── Can escalate to human
                    └── Routes to specialists
                            │
        ┌───────────────────┼───────────────────┬───────────────────┐
        │                   │                   │                   │
        ▼                   ▼                   ▼                   ▼
   Remittances          Top-Ups            Bill Pay              SNPL
   ├── 17 tools         ├── 8 tools        ├── 6 tools        ├── 12 tools
   ├── 3 subflows       ├── 1 subflow      ├── 1 subflow      ├── 1 subflow
   └── Can go back      └── Can go back    └── Can go back    └── Can go back
       to Felix             to Felix            to Felix           to Felix

                            │
                            │ (Shadow Service)
                            ▼
                    Financial Advisor
                    ├── Activates on financial wellness topics
                    ├── 90% relevance threshold
                    └── Can be pushed onto agent stack
```

### Example: Agent Navigation

```
User: "I want to send money"
Felix: "I'll connect you with our remittances specialist."
       [Felix switches to Remittances Agent]

User: "Actually, nevermind. I want to apply for credit."
Remittances: "No problem! Let me take you back to Felix
              who can help with credit."
             [Returns to Felix, then to SNPL Agent]
```

### Agent Configuration

Each agent is configured through JSON files:

```json
{
  "id": "remittances",
  "name": "Remittances Agent",
  "description": "Specialist in international money transfers",

  "model_config": {
    "model": "gpt-4o",
    "temperature": 0.7
  },

  "navigation": {
    "canGoUp": true,      // Can return to parent (Felix)
    "canGoHome": true,    // Can jump straight to Felix
    "canEscalate": true   // Can transfer to human agent
  },

  "tools": [
    // Tools defined here...
  ],

  "subflows": [
    // Multi-step flows defined here...
  ]
}
```

---

## Tools: How Agents Take Action

Tools are the "verbs" of the system - they let agents do things beyond just talking.

### Types of Tools

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TOOL TYPES                                     │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ INFORMATION     │    │ ACTION          │    │ NAVIGATION      │
│                 │    │                 │    │                 │
│ Read-only       │    │ Changes state   │    │ Switches        │
│ lookups         │    │ or executes     │    │ context         │
│                 │    │ transactions    │    │                 │
│ Examples:       │    │ Examples:       │    │ Examples:       │
│ • get_rate      │    │ • create_txn    │    │ • enter_agent   │
│ • get_balance   │    │ • add_recipient │    │ • start_flow    │
│ • list_history  │    │ • cancel_order  │    │ • go_home       │
│                 │    │                 │    │ • escalate      │
│ No confirmation │    │ Often needs     │    │ No confirmation │
│ needed          │    │ confirmation    │    │ needed          │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Tool Definition Example

```json
{
  "name": "create_transfer",
  "description": "Execute a money transfer to a recipient",
  "parameters": [
    {
      "name": "recipient_id",
      "type": "string",
      "required": true
    },
    {
      "name": "amount",
      "type": "number",
      "required": true
    },
    {
      "name": "currency",
      "type": "string",
      "required": true
    }
  ],
  "requires_confirmation": true,
  "confirmation_message": "Send {{amount}} {{currency}} to {{recipient_name}}?"
}
```

### Confirmation Flow

For sensitive actions, Felix always asks for confirmation:

```
User: "Send $500 to Maria"

Felix: "I'm about to send $500 USD to Maria Garcia in Mexico.
        She'll receive 8,725 MXN via bank deposit.

        Please confirm: Should I proceed with this transfer?"

User: "Yes, go ahead"

Felix: "Transfer complete! Maria will receive the funds
        within 1-2 business days. Reference: TXN-123456"
```

---

## Subflows: Multi-Step Conversations

Subflows guide users through complex processes step by step. They're like forms, but conversational.

### Anatomy of a Subflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SEND MONEY FLOW                                      │
└─────────────────────────────────────────────────────────────────────────────┘

   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
   │ ask_recipient│────▶│  ask_amount  │────▶│  ask_method  │
   │              │     │              │     │              │
   │ "Who should  │     │ "How much do │     │ "How should  │
   │  receive the │     │  you want to │     │  they receive│
   │  money?"     │     │  send?"      │     │  it?"        │
   └──────────────┘     └──────────────┘     └──────────────┘
                                                    │
                                                    ▼
                        ┌──────────────┐     ┌──────────────┐
                        │ transfer_sent│◀────│   confirm    │
                        │   (FINAL)    │     │              │
                        │              │     │ "Send $200   │
                        │ "Success!    │     │  to Maria?"  │
                        │  Ref: 123"   │     │              │
                        └──────────────┘     └──────────────┘
```

### State Data Collection

As the user progresses through the flow, data is collected:

```
State: ask_recipient
Data: {}

User: "Send to Maria Garcia"

State: ask_amount
Data: { recipient: "Maria Garcia", recipient_id: "r_123" }

User: "$200"

State: ask_method
Data: { recipient: "Maria Garcia", recipient_id: "r_123", amount: 200 }

User: "Bank deposit"

State: confirm
Data: {
  recipient: "Maria Garcia",
  recipient_id: "r_123",
  amount: 200,
  method: "bank",
  exchange_rate: 17.45,
  recipient_gets: 3490
}
```

### Flow State Instructions

Each state tells the AI what to do:

```json
{
  "state_id": "ask_amount",
  "name": "Ask Amount",
  "agent_instructions": "Ask the user how much money they want to send. Show the current exchange rate and what the recipient will receive. If they mention an amount, validate it against their daily limit.",
  "on_enter": {
    "message": "How much would you like to send to {{recipient_name}}?"
  },
  "state_tools": [
    {
      "name": "set_amount",
      "flow_transition": {
        "onSuccess": "ask_method",
        "onError": "ask_amount"
      }
    }
  ]
}
```

---

## The Shadow Service: Contextual Intelligence

The Shadow Service runs **in parallel** with every conversation, looking for opportunities to help:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SHADOW SERVICE ARCHITECTURE                         │
└─────────────────────────────────────────────────────────────────────────────┘

                         Main Conversation
                               │
    User: "Send $200          │
           to Mexico"          │
                               │
              ┌────────────────┴────────────────┐
              │                                 │
              ▼                                 ▼
    ┌─────────────────┐              ┌─────────────────┐
    │   Main LLM      │              │ Shadow Service  │
    │                 │              │                 │
    │ "Process the    │              │ Evaluates:      │
    │  transfer       │              │ • Financial tips│
    │  request"       │              │ • Promotions    │
    │                 │              │ • Savings hints │
    └────────┬────────┘              └────────┬────────┘
             │                                │
             │                                │
             ▼                                ▼
    ┌─────────────────────────────────────────────────┐
    │              Combined Response                  │
    │                                                 │
    │ Felix: "I'll send $200 to Maria in Mexico.     │
    │         She'll receive 3,490 MXN."             │
    │                                                 │
    │ 💡 Tip: "Did you know? Sending $50 more        │
    │     would unlock our preferred rate!"          │
    └─────────────────────────────────────────────────┘
```

### Shadow Subagents

Different subagents watch for different opportunities:

```
┌─────────────────┐     ┌─────────────────┐
│ Financial       │     │ Campaigns       │
│ Advisor         │     │ (DISABLED)      │
│                 │     │                 │
│ Watches for:    │     │ Would watch for:│
│ • Budgeting     │     │ • Promotions    │
│   questions     │     │ • Seasonal      │
│ • Savings       │     │   offers        │
│   opportunities │     │ • Loyalty       │
│ • Financial     │     │   rewards       │
│   planning      │     │                 │
│                 │     │                 │
│ Threshold: 90%  │     │ Threshold: 70%  │
│ relevance       │     │ relevance       │
│                 │     │                 │
│ ✅ ENABLED      │     │ ❌ DISABLED     │
│ Has full agent  │     │ Config only     │
│ (financial_     │     │ (no agent file) │
│  advisor.json)  │     │                 │
└─────────────────┘     └─────────────────┘
```

> **Current Status:** Only the Financial Advisor subagent is enabled. The Campaigns subagent is configured but disabled (`enabled: false` in shadow_service.json).

### Activation vs. Tips

The Shadow Service operates in two modes:

**1. Tip Mode** - Adds a helpful message without changing the flow:
```
User: "How much did I send last month?"
Felix: "Last month you sent a total of $450 across 3 transfers."
💡 Tip: "You're close to our Gold tier! Two more transfers
        this month unlocks 0.5% better rates."
```

**2. Activation Mode** - Takes over the conversation when relevant:
```
User: "I'm worried about my spending habits"
Felix: "I understand financial wellness is important to you.
        Let me connect you with our Financial Advisor who
        specializes in budgeting and savings strategies."
        [Switches to Financial Advisor agent]
```

### Cooldown System

To avoid overwhelming users, the shadow service has cooldowns:

```
Global cooldown: 3 messages between any shadow tips
Per-subagent cooldown: 5 messages for Financial Advisor
                       3 messages for Campaigns
```

---

## State Management: Remembering Context

Every conversation maintains state across multiple dimensions:

### Session State Structure

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SESSION STATE                                     │
└─────────────────────────────────────────────────────────────────────────────┘

{
  "session_id": "sess_abc123",
  "user_id": "user_456",
  "status": "active",

  "agent_stack": [
    ─────────────────────────────────────────────────────────
    │ Stack of agents (most recent on top)                 │
    ─────────────────────────────────────────────────────────
    {
      "agent_id": "remittances",     ◀─── Currently active
      "entered_at": "2024-01-15T10:30:00Z",
      "entry_reason": "User wanted to send money"
    },
    {
      "agent_id": "felix",           ◀─── Previous (can go back)
      "entered_at": "2024-01-15T10:28:00Z",
      "entry_reason": "Session start"
    }
  ],

  "current_flow": {
    ─────────────────────────────────────────────────────────
    │ Active multi-step flow state                         │
    ─────────────────────────────────────────────────────────
    "flow_id": "send_money_flow",
    "current_state": "ask_amount",
    "state_data": {
      "recipient_id": "r_123",
      "recipient_name": "Maria Garcia",
      "country": "MX"
    },
    "entered_at": "2024-01-15T10:31:00Z"
  },

  "pending_confirmation": null,
  │   OR when waiting for user confirmation:
  │   {
  │     "tool_name": "create_transfer",
  │     "tool_params": { "amount": 200, ... },
  │     "display_message": "Send $200 to Maria?",
  │     "expires_at": "2024-01-15T10:40:00Z"
  │   }

  "message_count": 12
}
```

### The Agent Stack Explained

The agent stack works like browser history - you can go back:

```
Start: [Felix]
"I want to send money" → [Felix, Remittances]
"Actually, I need credit" → [Felix, Remittances, SNPL]
"Go back" → [Felix, Remittances]
"Go home" → [Felix]
```

### Preserving Flow State

When the Shadow Service activates, your flow state is preserved:

```
1. User is in: Remittances → Send Money Flow → Step 3 of 5
2. Shadow detects user needs financial advice
3. Financial Advisor agent is pushed onto stack
4. Original flow state saved in stack frame
5. User chats with Financial Advisor
6. User says "go back" or advisor completes
7. Financial Advisor popped from stack
8. User returns to: Send Money Flow → Step 3 of 5 (exactly where they left off!)
```

---

## Why This Architecture?

Every architectural decision solves a specific problem:

### Problem 1: Conversations Get Messy

**Challenge:** Long conversations lose context. The AI forgets what was discussed.

**Solution:** History Compaction
- Recent messages kept verbatim
- Older messages summarized by AI
- Token budget ensures we never exceed limits
- Summary preserves key facts and decisions

```
Messages 1-50:   [Summarized] "User sent $200 to Maria, asked about rates..."
Messages 51-80: [Summarized] "User added new recipient Juan..."
Messages 81-100: [Full verbatim messages]
```

### Problem 2: Routing is Fragile

**Challenge:** String-based routing like "if tool name contains 'enter'" breaks easily.

**Solution:** Explicit Routing Registry
- Every tool declares its routing intent explicitly
- Registry validates all routes at startup
- Application won't start if routes are misconfigured
- Routing returns `state_changed` flag (no recursion)

```json
// Explicit routing (what we do)
{
  "name": "enter_remittances",
  "routing": {
    "type": "enter_agent",
    "target": "remittances"
  }
}

// vs. Implicit routing (fragile, what we avoid)
// "if 'enter' in tool_name: parse target from name"
```

### Problem 3: Extra Turns After Routing

**Challenge:** The intermediate architecture (with `state_changed` flag but no loop) required extra user messages after routing:
- User says "Quiero recarga" → Felix responds "Te conecto..."
- User must send another message → TopUps finally responds with actual content
- This felt broken to users

**Solution:** Routing Chain (Iterative Loop)
- Routing chain loops until **stable state** (no routing tools called)
- Each iteration: get agent → enrich → LLM call → process tools
- If routing occurred, continue loop with new agent context
- When stable, return response immediately to user
- Max 3 iterations with loop detection for safety

```
Old (extra turn):                    New (routing chain):
User: "Quiero recarga"              User: "Quiero recarga"
Felix: "Te conecto..."              ─────────────────────────────
(User must send another msg)        │ Chain iteration 1:        │
TopUps: "Veo tus números..."        │  Felix → enter_topups     │
                                    │ Chain iteration 2:        │
                                    │  TopUps → start_flow      │
                                    │ Chain iteration 3:        │
                                    │  Flow → no routing (stable)│
                                    ─────────────────────────────
                                    TopUps: "Veo tus números..."
                                    (Single response!)
```

### Problem 4: Slow Contextual Help

**Challenge:** Running extra AI calls for tips adds latency.

**Solution:** Parallel Shadow Service
- Shadow service runs simultaneously with main LLM
- No added wait time for the user
- Errors in shadow don't break the main conversation

```
Time:    0ms ─────────────────────────────────────────▶ 800ms
Main:    [======================LLM Call==============]
Shadow:  [=======Shadow Eval=======]
Result:  ────────────────────────────────────────────▶ Combined at 800ms
```

### Problem 5: Services and UI Are Coupled

**Challenge:** Services that return formatted messages can't be reused.

**Solution:** Strict Separation
- Services return **raw data only** (numbers, objects, arrays)
- Presentation layer handles all formatting
- Same service works for chat, web app, mobile app, API

```python
# Service layer (raw data)
def get_exchange_rate(from_currency, to_currency):
    return {
        "rate": 17.45,
        "from": "USD",
        "to": "MXN",
        "timestamp": "2024-01-15T10:00:00Z"
    }

# Presentation layer (formatting)
# Chat: "The current rate is $1 USD = 17.45 MXN"
# Web:  <ExchangeRateWidget rate={17.45} />
# API:  { "rate": 17.45, "from": "USD", "to": "MXN" }
```

### Problem 6: Configuration Scattered Everywhere

**Challenge:** Agent behaviors defined in code are hard to modify.

**Solution:** Configuration-Driven Design
- Agents, tools, flows defined in JSON
- Admin API for runtime modifications
- Database stores runtime state
- Code is generic; configuration is specific

```
┌─────────────────────────────────────────────────────────────┐
│                Configuration vs. Code                       │
├─────────────────────────────────────────────────────────────┤
│  CONFIGURATION (JSON/DB)     │  CODE (Python)              │
│  ─────────────────────────   │  ─────────────────────────  │
│  • Agent personalities       │  • Orchestration logic      │
│  • Tool definitions          │  • State management         │
│  • Flow states & transitions │  • LLM communication        │
│  • Response templates        │  • Database operations      │
│  • System prompts            │  • HTTP handling            │
│                              │                             │
│  "What" and "Who"            │  "How"                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Technical Reference

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SYSTEM ARCHITECTURE                                  │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────┐
                              │   Client    │
                              │  (Web/App)  │
                              └──────┬──────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                         BACKEND (Port 8000)                                │
├────────────────────────────────────────────────────────────────────────────┤
│                              API LAYER                                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐        │
│  │  routes/chat.py │    │ routes/admin.py │    │  schemas/*.py   │        │
│  │                 │    │                 │    │                 │        │
│  │ POST /message   │    │ CRUD operations │    │ Request/Response│        │
│  │ GET /session    │    │ for agents,     │    │ validation      │        │
│  │ GET /history    │    │ tools, flows    │    │                 │        │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘        │
├────────────────────────────────────────────────────────────────────────────┤
│                          ORCHESTRATION LAYER                               │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                    Orchestrator (Routing Chain)                      │  │
│  │   Phase 1: Setup → Phase 2: Chain Loop → Phase 3: Final Response    │  │
│  │   Chain loops until stable state (no routing tools called)          │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│           │              │              │              │                   │
│           ▼              ▼              ▼              ▼                   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐     │
│  │   Context    │ │    State     │ │   Routing    │ │    Tool      │     │
│  │  Enrichment  │ │   Manager    │ │   Handler    │ │   Executor   │     │
│  │              │ │              │ │              │ │              │     │
│  │ Auto-execute │ │ Session,     │ │ Returns      │ │ HTTP calls   │     │
│  │ on_enter     │ │ flows,       │ │ state_changed│ │ to Services  │     │
│  │ callTool     │ │ confirmations│ │ (no recurse) │ │ Gateway      │     │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘     │
│           │                                                │               │
│           ▼                                                ▼               │
│  ┌──────────────┐    ┌──────────────┐             ┌──────────────┐        │
│  │   Context    │    │  LLM Client  │             │   Shadow     │        │
│  │  Assembler   │    │              │             │   Service    │        │
│  │              │    │ OpenAI API   │             │              │        │
│  │ Builds prompt│    │ parallel w/  │◄───────────►│ Parallel     │        │
│  │ with enriched│    │ shadow       │             │ contextual   │        │
│  │ data         │    │              │             │ messaging    │        │
│  └──────────────┘    └──────────────┘             └──────────────┘        │
├────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                        Service Client (HTTP)                         │  │
│  │   Async HTTP client for communicating with Services Gateway          │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────┘
                                 │
                                 │ HTTP (REST API)
                                 ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                    SERVICES GATEWAY (Port 8001)                            │
│                    Independently Deployable                                │
├────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                         REST API Routers                             │  │
│  │  /api/v1/remittances/*  /api/v1/topups/*  /api/v1/snpl/*            │  │
│  │  /api/v1/billpay/*      /api/v1/wallet/*  /api/v1/campaigns/*       │  │
│  │  /api/v1/financial-data/*                                           │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                    │                                       │
│                                    ▼                                       │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐│
│  │Remittances │ │  Top-Ups   │ │  Bill Pay  │ │   SNPL     │ │ Wallet*  ││
│  │  Service   │ │  Service   │ │  Service   │ │  Service   │ │ Service  ││
│  │            │ │            │ │            │ │            │ │          ││
│  │ • Transfers│ │ • Recharges│ │ • Payments │ │ • Loans    │ │ • Balance││
│  │ • Recipients│ │ • Carriers │ │ • Billers  │ │ • Payments │ │ • History││
│  │ • Rates    │ │ • Promos   │ │ • Schedules│ │ • Status   │ │ • Cards  ││
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘ └──────────┘│
│  * Wallet is a service only (no dedicated agent - accessed by other agents) │
│                                                                            │
│  Response Format: {"success": true, "data": {...}}                        │
│                   {"success": false, "error": "...", "error_code": "..."}  │
└────────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                            DATA LAYER                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                        PostgreSQL Database                           │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │  │
│  │  │  Agent   │ │   Tool   │ │ Subflow  │ │ Session  │ │ Message  │  │  │
│  │  │          │ │          │ │          │ │          │ │          │  │  │
│  │  │ Hierarchy│ │ Actions  │ │ States & │ │ User     │ │ History  │  │  │
│  │  │ & config │ │ & params │ │ transitions│ │ state    │ │          │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
conversationalBuilderPOC/
├── backend/                         # Core orchestration platform (Port 8000)
│   ├── app/
│   │   ├── core/                    # Orchestration engine
│   │   │   ├── orchestrator.py      # Main conversation handler (three-phase)
│   │   │   ├── context_enrichment.py# Auto-executes on_enter.callTool
│   │   │   ├── context_assembler.py # Builds LLM prompts with enriched data
│   │   │   ├── state_manager.py     # Session/flow state
│   │   │   ├── tool_executor.py     # Runs tools via HTTP to Services Gateway
│   │   │   ├── routing.py           # Routing types and data classes
│   │   │   ├── routing_handler.py   # Returns state_changed (no recursion)
│   │   │   ├── routing_registry.py  # Startup validation
│   │   │   ├── shadow_service.py    # Parallel contextual tips
│   │   │   ├── llm_client.py        # OpenAI API wrapper
│   │   │   └── i18n.py              # Language directive injection
│   │   │
│   │   ├── clients/                 # HTTP clients for external services
│   │   │   ├── service_client.py    # Async HTTP client for Services Gateway
│   │   │   └── service_mapping.py   # Tool name → endpoint mapping
│   │   │
│   │   ├── models/                  # Database models
│   │   │   ├── agent.py             # Agent, Tool, ResponseTemplate
│   │   │   ├── session.py           # ConversationSession
│   │   │   ├── conversation.py      # ConversationMessage
│   │   │   ├── subflow.py           # Subflow, SubflowState
│   │   │   └── user.py              # UserContext
│   │   │
│   │   ├── routes/                  # API endpoints
│   │   │   ├── chat.py              # Chat API
│   │   │   └── admin.py             # Admin CRUD
│   │   │
│   │   ├── config/                  # JSON configurations (English only)
│   │   │   ├── agents/              # Agent definitions (felix, remittances, topups, snpl, billpay, financial_advisor)
│   │   │   ├── prompts/             # System prompts (base_system.json, sections.json)
│   │   │   ├── shadow_service.json  # Shadow service config
│   │   │   └── confirmation_templates.json  # Financial transaction confirmations
│   │   │
│   │   └── main.py                  # FastAPI entry point
│   │
│   └── tests/                       # Backend test suites
│
├── services/                        # Independently deployable (Port 8001)
│   ├── app/
│   │   ├── main.py                  # FastAPI entry point
│   │   ├── config.py                # Services gateway configuration
│   │   ├── routers/                 # REST API routers
│   │   │   ├── remittances.py       # /api/v1/remittances/*
│   │   │   ├── topups.py            # /api/v1/topups/*
│   │   │   ├── snpl.py              # /api/v1/snpl/*
│   │   │   ├── billpay.py           # /api/v1/billpay/*
│   │   │   ├── wallet.py            # /api/v1/wallet/*
│   │   │   ├── campaigns.py         # /api/v1/campaigns/*
│   │   │   └── financial_data.py    # /api/v1/financial-data/*
│   │   │
│   │   └── services/                # Mock service implementations
│   │       ├── remittances.py
│   │       ├── topups.py
│   │       ├── snpl.py
│   │       ├── billpay.py
│   │       ├── wallet.py
│   │       ├── campaigns.py
│   │       └── financial_data.py
│   │
│   └── tests/                       # Services Gateway tests
│
├── frontend/
│   ├── chat/                        # Simple vanilla JS chat UI
│   ├── admin/                       # Admin interface
│   └── react-app/                   # React application
│
└── docker-compose.yml               # PostgreSQL + Redis + Backend + Services
```

### Key Files Quick Reference

| Purpose | File |
|---------|------|
| Handle incoming messages | `backend/app/routes/chat.py` |
| Main orchestration (three-phase) | `backend/app/core/orchestrator.py` |
| Auto-enrich context | `backend/app/core/context_enrichment.py` |
| Build LLM prompts | `backend/app/core/context_assembler.py` |
| Manage session state | `backend/app/core/state_manager.py` |
| Execute tool calls via HTTP | `backend/app/core/tool_executor.py` |
| Handle routing (state_changed) | `backend/app/core/routing_handler.py` |
| Validate routes at startup | `backend/app/core/routing_registry.py` |
| Shadow contextual tips | `backend/app/core/shadow_service.py` |
| HTTP client for services | `backend/app/clients/service_client.py` |
| Tool → endpoint mapping | `backend/app/clients/service_mapping.py` |
| Agent configurations | `backend/app/config/agents/*.json` |
| Confirmation templates | `backend/app/config/confirmation_templates.json` |
| Shadow service config | `backend/app/config/shadow_service.json` |
| Services Gateway entry | `services/app/main.py` |

### Current Agent Configurations

| Agent | File | Description |
|-------|------|-------------|
| Felix | `felix.json` | Root orchestrator - routes to specialists |
| Remittances | `remittances.json` | International money transfers (17 tools, 3 subflows) |
| Top-Ups | `topups.json` | Mobile phone recharges (8 tools, 1 subflow) |
| Bill Pay | `billpay.json` | Bill payments (6 tools, 1 subflow) |
| SNPL | `snpl.json` | Send Now Pay Later credit (12 tools, 1 subflow) |
| Financial Advisor | `financial_advisor.json` | Shadow agent for budgeting/savings |

---

## Complete Walkthrough: A Real Conversation

Let's trace through a complete conversation to see exactly how all the pieces work together. This example demonstrates agent switching, flow management, mind-changing, and transaction execution.

**Scenario:** A user says hello, asks for a phone top-up, gives a phone number, changes their mind and asks for credit, then changes their mind again and sends a remittance to an existing recipient.

---

### Turn 1: User Says Hello

```
USER: "Hola"
```

#### What Happens Inside the System

**Step 1: API Receives Request**
```
POST /api/chat/message
{
  "message": "Hola",
  "user_id": "user_demo"
}
```

**Step 2: Session Created**
```
StateManager.get_or_create_session()
→ New session created (no existing session_id provided)
```

**Session State After:**
```json
{
  "session_id": "sess_001",
  "user_id": "user_demo",
  "status": "active",
  "message_count": 0,
  "agent_stack": [
    {
      "agent_id": "felix",
      "entered_at": "2026-01-12T10:00:00Z",
      "entry_reason": "Session start"
    }
  ],
  "current_flow": null,
  "pending_confirmation": null
}
```

**Step 3: Context Assembly**
```
ContextAssembler builds system prompt:
├── Base system prompt (English)
├── Felix agent description
├── Felix's tools: [enter_remittances, enter_credit,
│                   enter_topups, change_language]
├── User profile: "Carlos Martinez, Spanish speaker"
├── Conversation history: (empty - first message)
└── Language directive: "Respond in Spanish"
```

**Step 4: Parallel Execution**
```
┌─────────────────────────────┐    ┌─────────────────────────────┐
│        Main LLM             │    │      Shadow Service         │
│                             │    │                             │
│  Input: "Hola"              │    │  Evaluates context...       │
│  Context: Felix agent       │    │  Financial Advisor: 5%      │
│                             │    │  Campaigns: 10%             │
│  Decision: Simple greeting  │    │  → Below thresholds         │
│  → No tool calls needed     │    │  → No messages to inject    │
│                             │    │                             │
└─────────────────────────────┘    └─────────────────────────────┘
```

**Step 5: Response Generated**
```
LLM Response:
  message: "¡Hola! Soy Felix, tu asistente financiero. ¿En qué puedo ayudarte hoy?
            Puedo ayudarte con remesas, recargas de celular, pago de servicios,
            crédito o tu cartera."
  tool_calls: []
```

**Session State After Turn 1:**
```
┌─────────────────────────────────────────────────────────────┐
│  AGENT STACK          │  CURRENT FLOW     │  CONFIRMATION   │
│  ─────────────────    │  ─────────────    │  ─────────────  │
│  [Felix]              │  None             │  None           │
└─────────────────────────────────────────────────────────────┘
```

```
FELIX: "¡Hola! Soy Felix, tu asistente financiero. ¿En qué puedo ayudarte hoy?
        Puedo ayudarte con remesas, recargas de celular, pago de servicios,
        crédito o tu cartera."
```

---

### Turn 2: User Asks for Top-Up (Recarga)

```
USER: "Quiero una recarga"
```

#### What Happens Inside the System

**Step 1: Session Loaded**
```
StateManager.get_or_create_session(session_id="sess_001")
→ Existing session loaded
→ Current agent: Felix
→ No active flow
```

**Step 2: ROUTING CHAIN BEGINS**

The routing chain will loop until reaching a stable state (no routing tools called).

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                     CHAIN ITERATION 1: Felix Agent                        ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║  Context Assembly:                                                        ║
║  ├── Felix agent description                                              ║
║  ├── Felix system_prompt_addition: "DELEGATION RULES..."                  ║
║  ├── Felix's tools (6 tools)                                              ║
║  └── Language directive: "Respond in Spanish"                             ║
║                                                                           ║
║  LLM Decision:                                                            ║
║  → Analyzes: "Quiero una recarga" (I want a top-up)                       ║
║  → Matches delegation rule for enter_topups                               ║
║  → Tool call: enter_topups                                                ║
║                                                                           ║
║  Routing Handler:                                                         ║
║  → push_agent(topups)                                                     ║
║  → state_changed: true                                                    ║
║  → routing_occurred: true  ──► CONTINUE CHAIN                             ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
                                    │
                                    ▼
╔═══════════════════════════════════════════════════════════════════════════╗
║                     CHAIN ITERATION 2: TopUps Agent                       ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║  Context Assembly:                                                        ║
║  ├── TopUps agent description                                             ║
║  ├── TopUps system_prompt: "Use start_flow_recarga IMMEDIATELY..."        ║
║  └── TopUps tools (including start_flow_recarga)                          ║
║                                                                           ║
║  LLM Decision:                                                            ║
║  → User wants a top-up, start the flow immediately                        ║
║  → Tool call: start_flow_recarga                                          ║
║                                                                           ║
║  Routing Handler:                                                         ║
║  → enter_subflow(recarga)                                                 ║
║  → current_state: "collect_number"                                        ║
║  → state_changed: true                                                    ║
║  → routing_occurred: true  ──► CONTINUE CHAIN                             ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
                                    │
                                    ▼
╔═══════════════════════════════════════════════════════════════════════════╗
║                   CHAIN ITERATION 3: TopUps + Recarga Flow                ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║  Context Enrichment (on_enter.callTool):                                  ║
║  → Auto-execute: get_frequent_numbers                                     ║
║  → HTTP: GET /api/v1/topups/frequent-numbers                              ║
║  → Returns: [{phone: "+52 55 1234 5678", name: "Mamá"}, ...]              ║
║  → Stored in flow stateData                                               ║
║                                                                           ║
║  Context Assembly:                                                        ║
║  ├── TopUps agent + recarga flow state instructions                       ║
║  ├── Available Context Data: frequentNumbersData                          ║
║  └── Flow state: "collect_number"                                         ║
║                                                                           ║
║  LLM Decision:                                                            ║
║  → Has frequent numbers data, present them to user                        ║
║  → NO routing tools called                                                ║
║                                                                           ║
║  routing_occurred: false  ──► STABLE STATE REACHED                        ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

**Step 3: Chain Complete - Return Response**

After 3 iterations, the chain reached stable state. The user receives the TopUps response directly:

**Session State After Turn 2:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  AGENT STACK              │  CURRENT FLOW              │  CONFIRMATION      │
│  ─────────────────────    │  ────────────────────────  │  ─────────────     │
│  [Felix, TopUps]          │  flow_id: "recarga"        │  None              │
│       ▲                   │  current_state:            │                    │
│       └── active          │    "collect_number"        │                    │
│                           │  state_data: {}            │                    │
│                           │  context:                  │                    │
│                           │    frequentNumbersData:    │                    │
│                           │    [Mamá, Hermano]         │                    │
│                           │                            │                    │
│  Debug info:              │                            │                    │
│  chain_iterations: 3      │                            │                    │
│  stable_state: true       │                            │                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

```
TOPUPS: "¡Perfecto! Veo que tienes estos números guardados:

         1. Mamá (+52 55 1234 5678)
         2. Hermano (+52 33 8765 4321)

         ¿A cuál número quieres enviar la recarga? También puedes darme
         un número diferente."
```

**Key Point:** The user asked "Quiero una recarga" and received the TopUps response with their frequent numbers **in a single turn**. No extra message required!

---

### Turn 3: User Provides Phone Number

```
USER: "+52 55 9999 8888"
```

#### What Happens Inside the System

**Step 1: Session Loaded**
```
Current state:
├── Agent stack: [Felix, TopUps]
├── Current agent: TopUps
├── Current flow: recarga @ collect_number
└── Flow data: {}
```

**Step 2: Context Assembly**
```
ContextAssembler builds:
├── Top-Ups agent description
├── Current flow state instructions (collect_number):
│   "Estás recolectando el número para una recarga. El 'frequentNumbersData'
│    contiene los números frecuentes... Cuando proporcionen un número,
│    usa detect_carrier para identificar el operador."
├── Available context data: frequentNumbersData
├── Top-Ups tools
└── Language directive
```

**Step 3: LLM Decision**
```
LLM sees: User provided a phone number (+52 55 9999 8888)
→ Flow instructions say: use detect_carrier
→ Generates tool call
```

**Step 4: Tool Execution**
```json
{
  "tool_calls": [
    {
      "name": "detect_carrier",
      "parameters": {
        "phone_number": "+52 55 9999 8888"
      }
    }
  ]
}
```

**Step 5: Service Call**
```
ToolExecutor.execute("detect_carrier", {phone_number: "+52 55 9999 8888"})
→ Calls MockTopUpsService.detect_carrier("+52 55 9999 8888")
→ Service returns raw data:
  {
    "phone_number": "+52 55 9999 8888",
    "carrier_id": "telcel_mx",
    "carrier_name": "Telcel",
    "country": "MX",
    "valid": true
  }
```

**Step 6: Flow State Transition**
```
LLM receives carrier data
→ Updates flow state_data:
  {
    "phone_number": "+52 55 9999 8888",
    "carrier_id": "telcel_mx",
    "carrier_name": "Telcel"
  }
→ Transitions to "select_amount" state

StateManager.transition_state(session, "select_amount")
→ Triggers on_enter message for select_amount:
  "El número es de {carrier_name}. Estas son las opciones de recarga..."
```

**Session State After Turn 3:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  AGENT STACK              │  CURRENT FLOW              │  CONFIRMATION      │
│  ─────────────────────    │  ────────────────────────  │  ─────────────     │
│  [Felix, TopUps]          │  flow_id: "recarga"        │  None              │
│       ▲                   │  current_state:            │                    │
│       └── active          │    "select_amount"         │                    │
│                           │  state_data:               │                    │
│                           │    phone: +52 55 9999 8888 │                    │
│                           │    carrier_id: telcel_mx   │                    │
│                           │    carrier_name: Telcel    │                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

```
TOPUPS: "El número +52 55 9999 8888 es de Telcel. Estas son las opciones
         de recarga disponibles:

         • $50 MXN
         • $100 MXN
         • $200 MXN
         • $500 MXN

         ¿Cuánto quieres recargar?"
```

---

### Turn 4: User Changes Mind - Wants Credit Instead

```
USER: "Sabes qué, mejor no. Quiero un crédito"
```

#### What Happens Inside the System

**Step 1: Context Assembly**
```
ContextAssembler includes:
├── Current flow state (select_amount) with instructions
├── But user is expressing desire to change context
└── Top-Ups tools include navigation: go_home
```

**Step 2: LLM Decision**
```
LLM analyzes: "Sabes qué, mejor no. Quiero un crédito"
→ User is explicitly abandoning current flow
→ User wants credit (different agent domain)
→ Top-Ups agent has navigation.canGoUp = true
→ Should use go_home to exit and let Felix route to credit
```

**Step 3: Navigation Tool Called**
```json
{
  "tool_calls": [
    {
      "name": "go_home",
      "parameters": {}
    }
  ],
  "message": "¡Sin problema! Regresamos con Felix para ayudarte con el crédito."
}
```

**Step 4: Routing Handler Processes go_home**
```
RoutingHandler.handle_tool_routing("go_home")

1. Recognized as navigation action
2. Execute:
   StateManager.go_home(session)
   → Clears current_flow (recarga flow abandoned)
   → Resets agent_stack to just [Felix]

3. Return RoutingOutcome:
   → handled: true
   → state_changed: true     ◀─── NO RECURSION
   → response_text: null
```

**Step 5: Response Returned (No Recursion)**
```
Orchestrator sees state_changed=true
→ Does NOT recurse
→ Felix will handle the credit request on the SAME message
→ Since go_home clears to Felix, the LLM is called again with Felix context
```

**Step 6: Felix Routes to Credit Agent (Same Turn)**
```
Felix LLM analyzes: "Sabes qué, mejor no. Quiero un crédito"
→ Delegation rules say: use enter_credit IMMEDIATELY
→ Tool call: enter_credit
→ RoutingHandler sets state_changed=true
→ Agent stack becomes [Felix, SNPL]
```

**Step 7: Response to User**
```
LLM generates transition message
→ "¡Sin problema! Te ayudo con el crédito."
→ SNPL agent context will be used on NEXT message
```

**On Next Message: Context Enrichment for SNPL**

When user sends next message, the system:
1. Detects SNPL agent is now active
2. LLM calls start_flow_apply_snpl (IMMEDIATELY per system prompt)
3. Flow enters "check_eligibility" state
4. On NEXT message, ContextEnrichment auto-calls get_snpl_eligibility

**Eligibility Check (via Context Enrichment)**
```
ContextEnrichment detects on_enter.callTool: "get_snpl_eligibility"

HTTP call to Services Gateway:
GET http://localhost:8001/api/v1/snpl/eligibility?user_id=user_demo
→ Returns:
  {
    "eligible": true,
    "tier": "SILVER",
    "max_amount": 600,
    "reason": "Good payment history"
  }

Data stored in stateData, available to LLM immediately
```

**Session State After Turn 4:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  AGENT STACK              │  CURRENT FLOW              │  CONFIRMATION      │
│  ─────────────────────    │  ────────────────────────  │  ─────────────     │
│  [Felix, SNPL]            │  flow_id: "apply_snpl_flow"│  None              │
│       ▲                   │  current_state:            │                    │
│       └── active          │    "check_eligibility"     │                    │
│                           │  state_data:               │                    │
│  (TopUps removed,         │    eligible: true          │                    │
│   recarga flow cleared)   │    tier: SILVER            │                    │
│                           │    max_amount: 600         │                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

```
SNPL: "¡Sin problema! Te ayudo con el crédito.

       Déjame verificar tu elegibilidad... ¡Buenas noticias! Estás
       pre-aprobado para SNPL.

       Tu límite: $600 USD
       Nivel: SILVER

       Puedes pedir prestado entre $200 y $600. El dinero se usa para
       enviar remesas y lo pagas en cuotas semanales.

       ¿Cuánto te gustaría solicitar?"
```

---

### Turn 5: User Changes Mind Again - Wants Remittance

```
USER: "Mmm pensándolo bien, mejor quiero enviar dinero a mi mamá"
```

#### What Happens Inside the System

**Step 1: LLM Analysis**
```
SNPL agent sees: User wants to send money to mom
→ This is remittances domain, not credit
→ User is abandoning credit application
→ SNPL has navigation.canGoUp = true
→ Should navigate away
```

**Step 2: Navigation Executed**
```json
{
  "tool_calls": [
    {
      "name": "go_home",
      "parameters": {}
    }
  ],
  "message": "¡Entendido! Te regreso con Felix para ayudarte con la remesa."
}
```

**Step 3: go_home Processed**
```
RoutingHandler.handle_tool_routing("go_home")
→ StateManager.go_home(session)
→ Clears apply_snpl_flow (abandoned)
→ Resets stack to [Felix]
→ Returns state_changed: true (no recursion)
```

**Step 4: Felix Routes to Remittances (Same Turn)**
```
Felix LLM: User wants to send money to mom
→ Delegation: enter_remittances IMMEDIATELY
→ Tool: enter_remittances
→ RoutingHandler sets state_changed: true
→ Agent stack becomes [Felix, Remittances]
```

**Step 5: Response to User**
```
LLM generates transition message
→ "¡Entendido! Te ayudo a enviar dinero."
→ Remittances agent context will be used on NEXT message
```

**On Next Message: Context Enrichment + Flow Start**

When user sends "A mi mamá, María":
1. Remittances agent is now active
2. LLM calls start_flow_send_money (per system prompt)
3. Flow enters "select_recipient" state
4. ContextEnrichment auto-calls list_recipients

**Recipient List Fetched (via Context Enrichment)**
```
ContextEnrichment detects on_enter.callTool: "list_recipients"

HTTP call to Services Gateway:
GET http://localhost:8001/api/v1/remittances/recipients?user_id=user_demo
→ Returns:
  [
    {
      "id": "rec_001",
      "name": "María García",
      "relationship": "Mamá",
      "country": "MX",
      "delivery_methods": ["bank", "cash"]
    },
    {
      "id": "rec_002",
      "name": "Juan García",
      "relationship": "Hermano",
      "country": "MX",
      "delivery_methods": ["bank"]
    }
  ]

Data stored in stateData, available to LLM in "Available Context Data"
```

**Session State After Turn 5:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  AGENT STACK              │  CURRENT FLOW              │  CONFIRMATION      │
│  ─────────────────────    │  ────────────────────────  │  ─────────────     │
│  [Felix, Remittances]     │  flow_id: "send_money_flow"│  None              │
│          ▲                │  current_state:            │                    │
│          └── active       │    "select_recipient"      │                    │
│                           │  state_data: {}            │                    │
│  (SNPL removed,           │  context:                  │                    │
│   credit flow cleared)    │    recipients: [María,Juan]│                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

```
REMITTANCES: "¡Perfecto! Te ayudo a enviar dinero.

              Veo que tienes estos destinatarios guardados:

              1. María García (Mamá) - México 🇲🇽
                 Métodos: Banco, Efectivo

              2. Juan García (Hermano) - México 🇲🇽
                 Método: Banco

              ¿A quién quieres enviar? También puedes agregar un nuevo
              destinatario."
```

---

### Turn 6: User Selects Recipient (Mom)

```
USER: "A mi mamá, María"
```

#### What Happens Inside the System

**Step 1: LLM Decision**
```
LLM sees: User selected "Mamá, María"
→ Matches recipient "María García" (rec_001)
→ Updates flow state_data:
  {
    "recipient_id": "rec_001",
    "recipient_name": "María García",
    "country": "MX"
  }
→ Transitions to "collect_amount"
```

**Step 2: State Transition**
```
StateManager.transition_state(session, "collect_amount")
→ on_enter.message: "¿Cuánto te gustaría enviar a {recipient_name}?"
→ Rendered: "¿Cuánto te gustaría enviar a María García?"
```

**Session State After Turn 6:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  CURRENT FLOW                                                               │
│  ────────────────────────────────────────────────────────────────────────   │
│  flow_id: "send_money_flow"                                                 │
│  current_state: "collect_amount"                                            │
│  state_data:                                                                │
│    recipient_id: "rec_001"                                                  │
│    recipient_name: "María García"                                           │
│    country: "MX"                                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

```
REMITTANCES: "¡Excelente! María García recibirá el dinero.

              ¿Cuánto te gustaría enviar a María García?"
```

---

### Turn 7: User Specifies Amount

```
USER: "200 dólares"
```

#### What Happens Inside the System

**Step 1: LLM Processes Amount**
```
LLM sees: "$200 USD"
→ State instructions say: use get_exchange_rate and create_quote
```

**Step 2: Multiple Tool Calls**
```json
{
  "tool_calls": [
    {
      "name": "get_exchange_rate",
      "parameters": {"country": "MX"}
    },
    {
      "name": "create_quote",
      "parameters": {"amount_usd": 200, "country": "MX"}
    },
    {
      "name": "get_user_limits",
      "parameters": {}
    }
  ]
}
```

**Step 3: Service Calls (Parallel)**
```
get_exchange_rate → {"rate": 17.45, "from": "USD", "to": "MXN"}

create_quote → {
  "amount_usd": 200,
  "fee_usd": 3.99,
  "total_usd": 203.99,
  "exchange_rate": 17.45,
  "recipient_gets": 3490,
  "recipient_currency": "MXN",
  "eta": "2-4 hours"
}

get_user_limits → {
  "kyc_level": 2,
  "daily_limit": 2000,
  "daily_used": 0,
  "monthly_limit": 5000,
  "monthly_used": 300
}
```

**Step 4: Flow State Updated**
```
state_data updated:
{
  "recipient_id": "rec_001",
  "recipient_name": "María García",
  "country": "MX",
  "amount_usd": 200,
  "fee_usd": 3.99,
  "total_usd": 203.99,
  "exchange_rate": 17.45,
  "recipient_gets": 3490
}

→ Transitions to "select_delivery_method"
```

**Session State After Turn 7:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  CURRENT FLOW                                                               │
│  ────────────────────────────────────────────────────────────────────────   │
│  flow_id: "send_money_flow"                                                 │
│  current_state: "select_delivery_method"                                    │
│  state_data:                                                                │
│    recipient_id: "rec_001"                                                  │
│    recipient_name: "María García"                                           │
│    country: "MX"                                                            │
│    amount_usd: 200                                                          │
│    fee_usd: 3.99                                                            │
│    total_usd: 203.99                                                        │
│    exchange_rate: 17.45                                                     │
│    recipient_gets: 3490 MXN                                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

```
REMITTANCES: "Perfecto, $200 USD.

              📊 Desglose:
              • Envías: $200.00 USD
              • Comisión: $3.99 USD
              • Total a pagar: $203.99 USD

              💱 Tipo de cambio: 1 USD = 17.45 MXN

              📬 María García recibirá: $3,490.00 MXN

              ¿Cómo quieres que María reciba el dinero?
              1. 🏦 Depósito bancario (2-4 horas)
              2. 💵 Efectivo en sucursal (1 hora)"
```

---

### Turn 8: User Selects Bank Deposit

```
USER: "Por banco"
```

#### What Happens Inside the System

**Step 1: Delivery Method Selected**
```
LLM: User selected bank deposit
→ María has bank configured
→ Updates state_data:
  {
    ...existing data,
    "delivery_method_id": "bank_mx_001",
    "delivery_type": "BANK"
  }
→ Transitions to "review_summary"
```

**Step 2: Review State Entered**
```
on_enter.message: "Aquí está el resumen de tu envío. Por favor revisa y confirma."

LLM generates comprehensive summary for user review
```

**Session State After Turn 8:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  CURRENT FLOW                                                               │
│  ────────────────────────────────────────────────────────────────────────   │
│  flow_id: "send_money_flow"                                                 │
│  current_state: "review_summary"                                            │
│  state_data:                                                                │
│    recipient_id: "rec_001"                                                  │
│    recipient_name: "María García"                                           │
│    country: "MX"                                                            │
│    amount_usd: 200                                                          │
│    fee_usd: 3.99                                                            │
│    total_usd: 203.99                                                        │
│    exchange_rate: 17.45                                                     │
│    recipient_gets: 3490 MXN                                                 │
│    delivery_method_id: "bank_mx_001"                                        │
│    delivery_type: "BANK"                                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

```
REMITTANCES: "📋 RESUMEN DE TU ENVÍO
              ═══════════════════════════════════════

              👤 Destinatario: María García (Mamá)
              🌎 País: México

              💵 Monto a enviar: $200.00 USD
              📦 Comisión: $3.99 USD
              ═══════════════════════════════════════
              💳 Total a pagar: $203.99 USD

              💱 Tipo de cambio: 17.45 MXN/USD
              📬 María recibe: $3,490.00 MXN

              🏦 Método: Depósito bancario
              ⏱️ Llegada estimada: 2-4 horas

              ¿Confirmas este envío?"
```

---

### Turn 9: User Confirms Transfer

```
USER: "Sí, confirmo"
```

#### What Happens Inside the System

**Step 1: LLM Decision**
```
LLM sees: User confirmed
→ State instructions: "Call create_transfer with the collected data"
→ Tool has requires_confirmation: true
```

**Step 2: Tool Call with Confirmation Flag**
```json
{
  "tool_calls": [
    {
      "name": "create_transfer",
      "parameters": {
        "recipient_id": "rec_001",
        "amount_usd": 200,
        "delivery_method_id": "bank_mx_001"
      }
    }
  ]
}
```

**Step 3: ToolExecutor Checks Confirmation Requirement**
```
ToolExecutor.execute("create_transfer", params)

1. Check tool.requires_confirmation → true
2. Check session.pending_confirmation → null (no pending)
3. Tool requires confirmation but user hasn't confirmed THIS specific action
4. Generate confirmation message using template:
   "¿Confirmas enviar $200 USD a María García?
    Recibirá el equivalente en MXN
    Se cargará a tu método de pago predeterminado
    Llegada estimada: 2-4 horas"
5. Set pending_confirmation:
   {
     "tool_name": "create_transfer",
     "tool_params": {...},
     "display_message": "...",
     "expires_at": "2026-01-12T10:15:00Z"  // 5 min timeout
   }
6. Return ToolResult with requires_confirmation: true
```

**Session State After Turn 9:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  AGENT STACK              │  CURRENT FLOW              │  CONFIRMATION      │
│  ─────────────────────    │  ────────────────────────  │  ─────────────     │
│  [Felix, Remittances]     │  flow_id: "send_money_flow"│  PENDING           │
│          ▲                │  current_state:            │                    │
│          └── active       │    "review_summary"        │  tool_name:        │
│                           │                            │  "create_transfer" │
│                           │                            │                    │
│                           │                            │  expires_at:       │
│                           │                            │  10:15:00          │
└─────────────────────────────────────────────────────────────────────────────┘
```

```
REMITTANCES: "⚠️ CONFIRMACIÓN REQUERIDA

              ¿Confirmas enviar $200 USD a María García?

              • María recibirá: $3,490.00 MXN
              • Se cargará a tu método de pago predeterminado
              • Llegada estimada: 2-4 horas

              Responde 'Sí' para confirmar o 'No' para cancelar."
```

---

### Turn 10: User Gives Final Confirmation

```
USER: "Sí"
```

#### What Happens Inside the System

**Step 1: Confirmation Detection**
```
Orchestrator._handle_confirmation_response()

1. Check session.pending_confirmation → EXISTS
2. Classify user response: "Sí"
   → Matches YES pattern (Spanish: "sí", "si", "confirmo", etc.)
   → Classification: CONFIRMED
```

**Step 2: Re-execute Tool with skip_confirmation**
```
ToolExecutor.execute("create_transfer", params, skip_confirmation=True)

1. Check skip_confirmation → true
2. Bypass confirmation check
3. Execute actual service call:
   MockRemittancesService.create_transfer(
     user_id="user_demo",
     recipient_id="rec_001",
     amount_usd=200,
     delivery_method_id="bank_mx_001"
   )
```

**Step 3: Service Execution**
```
MockRemittancesService.create_transfer() returns:
{
  "transfer_id": "TXN-20260112-001",
  "status": "PROCESSING",
  "recipient_name": "María García",
  "amount_usd": 200,
  "fee_usd": 3.99,
  "total_usd": 203.99,
  "recipient_gets": 3490,
  "recipient_currency": "MXN",
  "delivery_type": "BANK",
  "eta": "2-4 hours",
  "created_at": "2026-01-12T10:10:00Z"
}
```

**Step 4: Flow Transition to Completed**
```
Tool has flow_transition: { onSuccess: "completed" }
→ StateManager.transition_state(session, "completed")
→ State "completed" has is_final: true
→ Flow cleared after processing
```

**Step 5: Clear Confirmation**
```
StateManager.clear_pending_confirmation(session)
```

**Step 6: Response Generated**
```
on_enter.message for "completed" state:
"¡Tu envío está siendo procesado! ¿Hay algo más en lo que pueda ayudarte?"

LLM enhances with transaction details
```

**Final Session State:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  AGENT STACK              │  CURRENT FLOW              │  CONFIRMATION      │
│  ─────────────────────    │  ────────────────────────  │  ─────────────     │
│  [Felix, Remittances]     │  None                      │  None              │
│          ▲                │  (cleared - flow complete) │  (cleared)         │
│          └── active       │                            │                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

```
REMITTANCES: "✅ ¡ENVÍO EXITOSO!

              Tu transferencia está siendo procesada.

              📋 Detalles:
              • Referencia: TXN-20260112-001
              • Destinatario: María García
              • Monto enviado: $200.00 USD
              • María recibe: $3,490.00 MXN
              • Método: Depósito bancario
              • Llegada estimada: 2-4 horas

              Recibirás una notificación cuando María reciba el dinero.

              ¿Hay algo más en lo que pueda ayudarte?"
```

---

### Summary: What We Just Witnessed

This conversation demonstrated every major architectural component:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    COMPLETE CONVERSATION JOURNEY                            │
│                    (Routing Chain Architecture)                             │
└─────────────────────────────────────────────────────────────────────────────┘

Turn  │ User Said             │ Agent Stack          │ Flow State        │ Chain Iters
──────┼───────────────────────┼──────────────────────┼───────────────────┼───────────
  1   │ "Hola"                │ [Felix]              │ None              │ 1 (stable)
  2   │ "Quiero recarga"      │ [Felix, TopUps]      │ recarga@collect   │ 3 (routed)
  3   │ "+52 55 9999 8888"    │ [Felix, TopUps]      │ recarga@select_amt│ 1 (stable)
  4   │ "Mejor un crédito"    │ [Felix, SNPL]        │ apply_snpl@elig   │ 3 (routed)
  5   │ "Mejor enviar dinero" │ [Felix, Remittances] │ send_money@recip  │ 3 (routed)
  6   │ "A mi mamá"           │ [Felix, Remittances] │ send_money@amt    │ 1 (stable)
  7   │ "200 dólares"         │ [Felix, Remittances] │ send_money@dlvr   │ 1 (stable)
  8   │ "Por banco"           │ [Felix, Remittances] │ send_money@review │ 1 (stable)
  9   │ "Sí, confirmo"        │ [Felix, Remittances] │ review + PENDING  │ 1 (confirm)
 10   │ "Sí"                  │ [Felix, Remittances] │ None (completed)  │ 1 (stable)
```

**Key Architectural Features Demonstrated:**

1. **Routing Chain (Eliminates Extra Turns)** (Turns 2, 4, 5)
   - Chain loops until stable state (no routing tools called)
   - Felix → TopUps → start_flow all happen in ONE user turn
   - User gets final agent response immediately
   - Max 3 iterations with loop detection for safety

2. **Proactive Context Enrichment** (Turns 2, 4, 5, 6)
   - on_enter.callTool executes at each chain iteration
   - Data available in "Available Context Data" section
   - LLM can immediately use fetched data
   - HTTP calls to Services Gateway (port 8001)

3. **Agent Routing via Chain** (Turns 2, 4, 5)
   - Felix delegates immediately without collecting info
   - Agents hand off via go_home and enter_* tools
   - Stack maintains navigation history
   - Chain continues until stable state reached

4. **Services Gateway (HTTP)** (Turns 2, 4, 5, 6, 7, 10)
   - All service calls via REST API
   - Services return raw data only (no formatting)
   - Response format: `{"success": true, "data": {...}}`
   - Independently deployable

5. **Confirmation Flow** (Turns 9-10)
   - Sensitive actions require explicit confirmation
   - Pending confirmation stored in session
   - User response classified (Yes/No/Unclear)
   - Tool re-executed with skip_confirmation

6. **Shadow Service (Final State Only)** (Every turn)
   - Runs AFTER chain completes (evaluates final state)
   - Evaluated but didn't inject (below thresholds)
   - No wasted evaluation on intermediate routing states

This walkthrough shows how Felix maintains coherent conversations across agent switches, flow abandonment, and multi-step transactions - using a routing chain that delivers immediate responses without extra turns.

---

## Conclusion

Felix's architecture is designed around these principles:

1. **Explicit over implicit** - Configuration declares intent clearly
2. **Separation of concerns** - Each layer has one job
3. **Immediate responses** - Routing chain eliminates extra turns
4. **State is king** - Everything is tracked and recoverable
5. **Fail fast** - Catch configuration errors at startup
6. **Iterative routing** - Chain loops until stable state, no recursion
7. **Proactive enrichment** - Load data before asking the LLM
8. **Service independence** - HTTP-based Services Gateway for scalability

The result is a conversational AI system that's:
- **Responsive** - Users get answers immediately, no extra turns needed
- **Maintainable** - Changes are configuration, not code
- **Scalable** - Services deployed independently, HTTP communication
- **Predictable** - Routing chain execution with loop detection
- **Resilient** - Errors are contained and recoverable
- **Testable** - Clear boundaries enable focused testing

---

*This document describes the Felix Conversational Orchestrator architecture as of January 2026.*

*Last updated: January 12, 2026 - Updated agent hierarchy (removed Wallet/Credit agents, added Financial Advisor), clarified shadow service status (Campaigns disabled), added services gateway details.*
