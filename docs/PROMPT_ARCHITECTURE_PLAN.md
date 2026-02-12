# COS Prompt Architecture Enhancement Plan

This document outlines the implementation plan for four architectural patterns to make the Conversational Orchestrator Service (COS) more reliable, faster, and more extensible.

---

## Executive Summary

| Pattern | Impact | Effort | Priority |
|---------|--------|--------|----------|
| **Prompt Modes** | High (faster routing, cost reduction) | Medium | P0 |
| **Lazy Tool Loading** | High (token savings, better caching) | Medium | P0 |
| **Hook System** | Medium (extensibility, A/B testing) | Medium | P1 |
| **Shadow Agent** | High (quality gates, enrichment) | High | P1 |

**Estimated Total Effort:** 4-6 weeks for full implementation

---

## Pattern 1: Prompt Modes

### Problem
Currently, `context_assembler.py` builds the same full context for every LLM call, even during routing chain iterations where we just need to determine the next agent. This wastes tokens and slows down multi-hop routing.

### Solution
Introduce three prompt modes that control what sections are included:

```
┌─────────────────────────────────────────────────────────────────┐
│  FULL MODE (main conversation)                                  │
│  ├── Base system prompt                                         │
│  ├── Agent description + system_prompt_addition                 │
│  ├── User profile + behavioral summary                          │
│  ├── Product context (remittances history, credit status, etc.) │
│  ├── Compacted history                                          │
│  ├── Current flow state                                         │
│  ├── Navigation instructions                                    │
│  ├── Language directive                                         │
│  └── All tools                                                  │
│  ~3,000-5,000 tokens                                            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  ROUTING MODE (agent/flow routing decisions)                    │
│  ├── Minimal identity ("You are routing for Felix")             │
│  ├── Agent description (shortened)                              │
│  ├── User name only                                             │
│  ├── Navigation + routing tools only                            │
│  └── Language directive                                         │
│  ~500-800 tokens                                                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  MINIMAL MODE (sub-agent tasks, shadow agent)                   │
│  ├── Task-specific instructions                                 │
│  ├── Relevant context only                                      │
│  └── Task-specific tools only                                   │
│  ~300-500 tokens                                                │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation

#### Phase 1.1: Add PromptMode enum and update ContextAssembler

```python
# app/core/prompt_modes.py
from enum import Enum

class PromptMode(Enum):
    FULL = "full"           # Main conversation - all sections
    ROUTING = "routing"     # Routing decisions - minimal context
    MINIMAL = "minimal"     # Sub-tasks - task-specific only
```

```python
# app/core/context_assembler.py - modified assemble()
def assemble(
    self,
    session: ConversationSession,
    user_message: str,
    agent: AgentConfig,
    user_context: Optional[UserContext] = None,
    recent_messages: Optional[List[ConversationMessage]] = None,
    compacted_history: Optional[str] = None,
    current_flow_state: Optional[SubflowStateConfig] = None,
    mode: PromptMode = PromptMode.FULL,  # NEW PARAMETER
) -> AssembledContext:
    """Assemble context based on prompt mode."""

    if mode == PromptMode.ROUTING:
        return self._assemble_routing_mode(session, user_message, agent, user_context)
    elif mode == PromptMode.MINIMAL:
        return self._assemble_minimal_mode(session, user_message, agent)
    else:
        return self._assemble_full_mode(...)  # Current implementation
```

#### Phase 1.2: Use ROUTING mode during chain iterations

```python
# app/core/orchestrator.py - in routing chain loop
while True:
    chain_state.iteration += 1

    # First iteration: FULL mode (need complete context for initial understanding)
    # Subsequent iterations: ROUTING mode (just need to route)
    mode = PromptMode.FULL if chain_state.iteration == 1 else PromptMode.ROUTING

    context = self.context_assembler.assemble(
        session=session,
        user_message=user_message,
        agent=agent,
        mode=mode,  # Pass mode
        ...
    )
```

#### Phase 1.3: Configuration-driven section inclusion

```json
// config/prompts/prompt_modes.json
{
  "full": {
    "sections": ["base_prompt", "agent_description", "user_profile", "product_context",
                 "compacted_history", "flow_state", "navigation", "language_directive"],
    "tools": "all"
  },
  "routing": {
    "sections": ["routing_identity", "agent_summary", "user_name", "navigation", "language_directive"],
    "tools": "navigation_only"
  },
  "minimal": {
    "sections": ["task_instructions", "language_directive"],
    "tools": "task_specific"
  }
}
```

### Expected Impact
- **Token reduction:** 70-80% savings during routing iterations
- **Latency improvement:** Faster LLM responses with smaller prompts
- **Cost savings:** Significant reduction in API costs for multi-hop routing

---

## Pattern 2: Lazy Tool Loading

### Problem
Every LLM call includes full tool schemas for all agent tools (10-20+ tools). Most messages use 0-2 tools, but we pay for full schemas every time. This also hurts prompt caching effectiveness.

### Solution
Include only a lightweight tool index in the prompt. Agent reads full documentation on-demand when it needs to use a tool.

### Implementation

#### Phase 2.1: Create tool documentation files

```
backend/app/config/tools/
├── get_exchange_rate/
│   └── TOOL.md          # Full documentation, examples, edge cases
├── create_transfer/
│   └── TOOL.md
├── list_recipients/
│   └── TOOL.md
└── ...
```

**Example TOOL.md:**
```markdown
# get_exchange_rate

## Purpose
Retrieve current exchange rate for a currency pair.

## Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| from_currency | string | Yes | Source currency code (e.g., "USD") |
| to_currency | string | Yes | Target currency code (e.g., "MXN") |
| amount | number | No | Amount to convert (for display purposes) |

## Response
```json
{
  "rate": 17.45,
  "from": "USD",
  "to": "MXN",
  "timestamp": "2024-01-15T10:30:00Z",
  "converted_amount": 174.50  // If amount was provided
}
```

## Usage Notes
- Rates are cached for 60 seconds
- Always show rate AND timestamp to user
- If rate seems unusual (>20% change), mention market volatility

## Examples
- User: "What's the exchange rate?" → Call with from="USD", to="MXN"
- User: "How much is $500 in pesos?" → Call with amount=500
```

#### Phase 2.2: Build tool index instead of full schemas

```python
# app/core/context_assembler.py
def _build_tool_index(self, agent: AgentConfig) -> str:
    """Build lightweight tool index for prompt."""
    tools = []
    for tool in agent.tools:
        tools.append(f'  <tool name="{tool.name}" description="{tool.description[:100]}" />')

    return f"""<available_tools>
{chr(10).join(tools)}
</available_tools>

When you need to use a tool, first read its documentation at /config/tools/{{tool_name}}/TOOL.md
to understand parameters, response format, and usage guidelines."""
```

#### Phase 2.3: Hybrid approach - index + minimal schema

For frequently used tools, include minimal schema inline:

```python
def _build_tools(self, agent: AgentConfig, current_flow_state: Optional[SubflowStateConfig] = None) -> List[dict]:
    """Build tools with lazy loading support."""

    # Always include navigation tools with full schema (small, always needed)
    tools = self._build_navigation_tools(agent)

    if current_flow_state and current_flow_state.state_tools:
        # In flow state: include FULL schemas for whitelisted tools only
        for tool_name in current_flow_state.state_tools:
            tool = agent.get_tool(tool_name)
            if tool:
                tools.append(tool.to_openai_tool())
    else:
        # Not in flow: use tool index + minimal schemas for common tools
        # Only include full schema for "hot" tools
        HOT_TOOLS = {"get_exchange_rate", "create_quote", "list_recipients"}

        for tool in agent.tools:
            if tool.name in HOT_TOOLS:
                tools.append(tool.to_openai_tool())
            # Other tools available via lazy loading

    return tools
```

#### Phase 2.4: Add read_tool_docs tool

```python
# New system tool available to all agents
{
    "name": "read_tool_documentation",
    "description": "Read detailed documentation for a tool before using it",
    "input_schema": {
        "type": "object",
        "properties": {
            "tool_name": {
                "type": "string",
                "description": "Name of the tool to read docs for"
            }
        },
        "required": ["tool_name"]
    }
}
```

### Expected Impact
- **Token reduction:** 50-70% reduction in tool-related tokens
- **Better caching:** Stable tool index improves Claude prompt caching
- **Richer documentation:** Tools can have extensive docs without bloating prompts

---

## Pattern 3: Hook System

### Problem
Modifying prompt behavior requires code changes. No easy way to A/B test prompts, enable debug mode, or customize per-user without touching `context_assembler.py`.

### Solution
Introduce a hook system that intercepts and transforms prompts at key points in the assembly pipeline.

### Architecture

```
User Message
     │
     ▼
┌─────────────────────────────────────────┐
│  Hook: pre_assembly                     │
│  (can modify: user_message, context)    │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│  ContextAssembler.assemble()            │
│  ├── Hook: section_build (per section)  │
│  └── Hook: tools_build                  │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│  Hook: post_assembly                    │
│  (can modify: system_prompt, tools)     │
└────────────────┬────────────────────────┘
                 │
                 ▼
     LLM Call
```

### Implementation

#### Phase 3.1: Define hook interface

```python
# app/core/hooks/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

@dataclass
class HookContext:
    """Context passed to hooks."""
    user_id: str
    session_id: str
    agent_id: str
    user_message: str
    timestamp: datetime
    metadata: Dict[str, Any]

class PromptHook(ABC):
    """Base class for prompt hooks."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique hook identifier."""
        pass

    @property
    def priority(self) -> int:
        """Execution order (lower = earlier). Default 100."""
        return 100

    @abstractmethod
    def should_activate(self, context: HookContext) -> bool:
        """Determine if hook should run."""
        pass

    def pre_assembly(self, context: HookContext, sections: Dict[str, str]) -> Dict[str, str]:
        """Modify sections before assembly. Return modified sections."""
        return sections

    def post_assembly(self, context: HookContext, system_prompt: str, tools: List[dict]) -> tuple[str, List[dict]]:
        """Modify assembled prompt. Return (system_prompt, tools)."""
        return system_prompt, tools
```

#### Phase 3.2: Implement hook registry

```python
# app/core/hooks/registry.py
class HookRegistry:
    """Registry for prompt hooks."""

    def __init__(self):
        self._hooks: List[PromptHook] = []

    def register(self, hook: PromptHook) -> None:
        self._hooks.append(hook)
        self._hooks.sort(key=lambda h: h.priority)

    def get_active_hooks(self, context: HookContext) -> List[PromptHook]:
        return [h for h in self._hooks if h.should_activate(context)]

    async def apply_pre_assembly(self, context: HookContext, sections: Dict[str, str]) -> Dict[str, str]:
        for hook in self.get_active_hooks(context):
            sections = hook.pre_assembly(context, sections)
        return sections

    async def apply_post_assembly(self, context: HookContext, system_prompt: str, tools: List[dict]) -> tuple[str, List[dict]]:
        for hook in self.get_active_hooks(context):
            system_prompt, tools = hook.post_assembly(context, system_prompt, tools)
        return system_prompt, tools
```

#### Phase 3.3: Example hooks

```python
# app/core/hooks/builtin/debug_hook.py
class DebugHook(PromptHook):
    """Inject verbose logging instructions for debug users."""

    name = "debug"
    priority = 50

    def __init__(self, debug_user_ids: Set[str]):
        self.debug_user_ids = debug_user_ids

    def should_activate(self, context: HookContext) -> bool:
        return context.user_id in self.debug_user_ids

    def post_assembly(self, context: HookContext, system_prompt: str, tools: List[dict]) -> tuple[str, List[dict]]:
        debug_section = """
## DEBUG MODE ACTIVE
- Log your reasoning before each tool call
- Explain why you chose this tool over alternatives
- Note any ambiguity in the user's request
"""
        return system_prompt + debug_section, tools
```

```python
# app/core/hooks/builtin/ab_test_hook.py
class ABTestHook(PromptHook):
    """A/B test different prompt variations."""

    name = "ab_test"
    priority = 90

    def __init__(self, experiment_id: str, variant_prompts: Dict[str, str]):
        self.experiment_id = experiment_id
        self.variant_prompts = variant_prompts

    def should_activate(self, context: HookContext) -> bool:
        return context.metadata.get("ab_experiments", {}).get(self.experiment_id) is not None

    def pre_assembly(self, context: HookContext, sections: Dict[str, str]) -> Dict[str, str]:
        variant = context.metadata["ab_experiments"][self.experiment_id]
        if variant in self.variant_prompts:
            sections["base_prompt"] = self.variant_prompts[variant]
        return sections
```

```python
# app/core/hooks/builtin/time_based_hook.py
class TimeBasedPersonaHook(PromptHook):
    """Adjust tone based on time of day."""

    name = "time_persona"
    priority = 80

    def should_activate(self, context: HookContext) -> bool:
        return True  # Always active

    def pre_assembly(self, context: HookContext, sections: Dict[str, str]) -> Dict[str, str]:
        hour = context.timestamp.hour

        if 6 <= hour < 12:
            tone_addition = "\nNote: It's morning. Be energetic and positive."
        elif 12 <= hour < 18:
            tone_addition = "\nNote: It's afternoon. Be efficient and focused."
        else:
            tone_addition = "\nNote: It's evening. Be relaxed and patient."

        sections["agent_description"] = sections.get("agent_description", "") + tone_addition
        return sections
```

#### Phase 3.4: Configuration-driven hooks

```json
// config/hooks.json
{
  "hooks": {
    "debug": {
      "enabled": true,
      "user_ids": ["test_user_123", "diego@felixpago.com"]
    },
    "ab_test_tone": {
      "enabled": true,
      "experiment_id": "tone_2024_01",
      "variants": {
        "control": "You are a helpful assistant...",
        "friendly": "You are a warm, friendly assistant...",
        "professional": "You are a professional financial assistant..."
      },
      "allocation": {"control": 0.33, "friendly": 0.33, "professional": 0.34}
    },
    "premium_features": {
      "enabled": true,
      "condition": "user.tier == 'premium'"
    }
  }
}
```

### Expected Impact
- **Extensibility:** Add new behaviors without code changes
- **A/B testing:** Test prompt variations with real users
- **Debugging:** Enable verbose mode for specific users
- **Personalization:** Time-based, user-tier-based customization

---

## Pattern 4: Shadow Agent

### Problem
The main agent can make mistakes, miss context, or produce suboptimal responses. There's no quality gate or opportunity for enrichment before responses reach users.

### Solution
A Shadow Agent runs in parallel with the main agent. It can:
1. **Validate:** Check if the main agent's response is correct/appropriate
2. **Enrich:** Add missing context or proactive suggestions
3. **Interrupt:** Stop bad paths before they reach the user
4. **Monitor:** Collect quality metrics for improvement

### Architecture

```
                    User Message
                         │
                         ▼
              ┌──────────────────────┐
              │    Orchestrator      │
              └──────────┬───────────┘
                         │
           ┌─────────────┴─────────────┐
           │                           │
           ▼                           ▼
    ┌──────────────┐           ┌──────────────┐
    │  Main Agent  │           │ Shadow Agent │
    │  (Primary)   │           │ (Validator)  │
    └──────┬───────┘           └──────┬───────┘
           │                          │
           │ Response                 │ Analysis
           │                          │
           └──────────┬───────────────┘
                      ▼
              ┌──────────────────────┐
              │   Shadow Resolver    │
              │  ┌─────────────────┐ │
              │  │ Decide:         │ │
              │  │ - Pass through  │ │
              │  │ - Enrich        │ │
              │  │ - Replace       │ │
              │  │ - Flag for      │ │
              │  │   review        │ │
              │  └─────────────────┘ │
              └──────────┬───────────┘
                         │
                         ▼
                  Final Response
```

### Shadow Agent Subagents (Configurable)

Based on your existing shadow service frontend, we'll support multiple specialized subagents:

| Subagent | Purpose | When Active |
|----------|---------|-------------|
| **QualityGate** | Verify response accuracy | Always |
| **ComplianceChecker** | Ensure regulatory compliance | Financial operations |
| **ToneAnalyzer** | Check tone appropriateness | Customer-facing responses |
| **ContextEnricher** | Add missing relevant info | When context gaps detected |
| **IntentValidator** | Verify correct intent routing | After routing decisions |

### Implementation

#### Phase 4.1: Shadow Agent Core

```python
# app/core/shadow/agent.py
from dataclasses import dataclass
from typing import Optional, List
from enum import Enum

class ShadowVerdict(Enum):
    PASS = "pass"              # Response is good, send as-is
    ENRICH = "enrich"          # Add shadow's additions to response
    REPLACE = "replace"        # Use shadow's response instead
    FLAG = "flag"              # Send but flag for human review
    BLOCK = "block"            # Don't send, escalate

@dataclass
class ShadowAnalysis:
    verdict: ShadowVerdict
    confidence: float          # 0-1, how confident is shadow
    enrichment: Optional[str]  # Additional content to add
    replacement: Optional[str] # Full replacement response
    issues: List[str]          # Identified issues
    metrics: dict              # For logging/analytics

@dataclass
class ShadowConfig:
    enabled: bool
    subagents: List[str]       # Which subagents to run
    confidence_threshold: float # Min confidence to intervene
    timeout_ms: int            # Max time to wait for shadow
    mode: str                  # "async" (don't block) or "gate" (block until ready)
```

```python
# app/core/shadow/shadow_agent.py
class ShadowAgent:
    """Parallel agent for validation and enrichment."""

    def __init__(self, config: ShadowConfig, llm_client: LLMClient):
        self.config = config
        self.llm_client = llm_client
        self.subagents = self._load_subagents(config.subagents)

    async def analyze(
        self,
        user_message: str,
        main_response: str,
        context: AssembledContext,
        session: ConversationSession,
    ) -> ShadowAnalysis:
        """
        Analyze the main agent's response.

        Runs configured subagents and aggregates their verdicts.
        """
        # Run subagents in parallel
        analyses = await asyncio.gather(*[
            subagent.analyze(user_message, main_response, context, session)
            for subagent in self.subagents
        ], return_exceptions=True)

        # Aggregate verdicts (most severe wins)
        return self._aggregate_analyses(analyses)

    async def generate_enrichment(
        self,
        user_message: str,
        main_response: str,
        issues: List[str],
        context: AssembledContext,
    ) -> str:
        """Generate enriched response based on identified issues."""

        enrichment_prompt = f"""The main agent responded to: "{user_message}"

Main agent response:
{main_response}

Issues identified:
{chr(10).join(f"- {issue}" for issue in issues)}

Generate a brief addition (1-2 sentences) that addresses these issues without repeating the main response."""

        response = await self.llm_client.complete(
            system_prompt="You are an assistant that enriches responses. Be concise.",
            messages=[{"role": "user", "content": enrichment_prompt}],
            model="claude-3-haiku-20240307",  # Fast model for enrichment
            max_tokens=150,
        )
        return response.text
```

#### Phase 4.2: Subagent Implementations

```python
# app/core/shadow/subagents/quality_gate.py
class QualityGateSubagent:
    """Validates response quality and accuracy."""

    name = "quality_gate"

    async def analyze(
        self,
        user_message: str,
        main_response: str,
        context: AssembledContext,
        session: ConversationSession,
    ) -> SubagentAnalysis:

        validation_prompt = f"""Evaluate this customer service response:

User asked: "{user_message}"

Agent responded: "{main_response}"

Check for:
1. Does it answer the user's actual question?
2. Is the information accurate (based on context)?
3. Is the tone appropriate?
4. Are there any red flags (promises that can't be kept, incorrect data)?

Respond in JSON:
{{"verdict": "pass|flag|block", "confidence": 0.0-1.0, "issues": ["issue1", ...]}}"""

        response = await self.llm_client.complete(
            system_prompt="You are a QA validator. Be strict but fair.",
            messages=[{"role": "user", "content": validation_prompt}],
            model="claude-3-haiku-20240307",
            max_tokens=200,
        )

        return self._parse_response(response.text)
```

```python
# app/core/shadow/subagents/context_enricher.py
class ContextEnricherSubagent:
    """Identifies missing context opportunities."""

    name = "context_enricher"

    async def analyze(
        self,
        user_message: str,
        main_response: str,
        context: AssembledContext,
        session: ConversationSession,
    ) -> SubagentAnalysis:

        # Check for proactive opportunities
        opportunities = []

        # Example: User asking about transfer, but has a promotion available
        if "transfer" in user_message.lower():
            promotions = await self._check_promotions(session.user_id)
            if promotions:
                opportunities.append(f"User has promotion: {promotions[0]['name']}")

        # Example: User asking about rate, but rate is unusually good today
        if "rate" in user_message.lower() or "exchange" in user_message.lower():
            if await self._is_rate_favorable():
                opportunities.append("Current rate is better than 30-day average")

        if opportunities:
            return SubagentAnalysis(
                verdict=ShadowVerdict.ENRICH,
                confidence=0.8,
                enrichment=self._format_opportunities(opportunities),
                issues=[],
            )

        return SubagentAnalysis(verdict=ShadowVerdict.PASS, confidence=1.0)
```

#### Phase 4.3: Integration with Orchestrator

```python
# app/core/orchestrator.py - modified handle_message
async def handle_message(self, user_message: str, user_id: str, session_id: Optional[UUID] = None) -> OrchestratorResponse:
    # ... existing setup code ...

    # Start shadow agent in parallel (if enabled)
    shadow_task = None
    if self.shadow_agent and self.shadow_agent.config.enabled:
        shadow_task = asyncio.create_task(
            self._run_shadow_analysis(user_message, context, session)
        )

    # === Run main agent (existing routing chain) ===
    # ... existing routing chain code ...
    main_response = response_text

    # === Shadow Agent Resolution ===
    if shadow_task:
        try:
            shadow_analysis = await asyncio.wait_for(
                shadow_task,
                timeout=self.shadow_agent.config.timeout_ms / 1000
            )

            # Resolve based on shadow verdict
            final_response = await self._resolve_shadow_verdict(
                main_response, shadow_analysis
            )
            response_text = final_response

        except asyncio.TimeoutError:
            # Shadow timed out, use main response
            logger.warning("Shadow agent timed out, using main response")

    # ... existing response handling ...

async def _resolve_shadow_verdict(
    self,
    main_response: str,
    analysis: ShadowAnalysis
) -> str:
    """Resolve shadow agent verdict into final response."""

    if analysis.verdict == ShadowVerdict.PASS:
        return main_response

    elif analysis.verdict == ShadowVerdict.ENRICH:
        # Append enrichment to main response
        return f"{main_response}\n\n{analysis.enrichment}"

    elif analysis.verdict == ShadowVerdict.REPLACE:
        logger.warning(f"Shadow replacing response. Issues: {analysis.issues}")
        return analysis.replacement

    elif analysis.verdict == ShadowVerdict.FLAG:
        # Send but log for review
        await self._flag_for_review(main_response, analysis)
        return main_response

    elif analysis.verdict == ShadowVerdict.BLOCK:
        # Don't send, escalate
        logger.error(f"Shadow blocked response. Issues: {analysis.issues}")
        return "Lo siento, necesito transferirte con un agente humano para ayudarte mejor."

    return main_response
```

#### Phase 4.4: Configuration (leveraging existing frontend)

```json
// config/shadow_service.json
{
  "enabled": true,
  "mode": "async",
  "timeout_ms": 2000,
  "confidence_threshold": 0.7,
  "subagents": [
    {
      "id": "quality_gate",
      "name": "Quality Gate",
      "enabled": true,
      "priority": 1,
      "config": {
        "strict_mode": false
      }
    },
    {
      "id": "context_enricher",
      "name": "Context Enricher",
      "enabled": true,
      "priority": 2,
      "config": {
        "check_promotions": true,
        "check_rate_alerts": true
      }
    },
    {
      "id": "compliance_checker",
      "name": "Compliance Checker",
      "enabled": true,
      "priority": 3,
      "config": {
        "regulations": ["cfpb", "remittance_disclosure"]
      }
    }
  ],
  "metrics": {
    "log_all_analyses": true,
    "sample_rate": 1.0
  }
}
```

### Expected Impact
- **Quality improvement:** Catch errors before they reach users
- **Proactive service:** Surface relevant information users didn't ask for
- **Compliance:** Automated regulatory checks
- **Learning:** Metrics for continuous improvement

---

## Implementation Timeline

### Week 1-2: Prompt Modes
- [ ] Create `PromptMode` enum and mode configuration
- [ ] Refactor `context_assembler.py` to support modes
- [ ] Implement `ROUTING` mode with minimal context
- [ ] Update orchestrator to use `ROUTING` mode during chain iterations
- [ ] Test and measure token/latency improvements

### Week 2-3: Lazy Tool Loading
- [ ] Create tool documentation structure (`config/tools/*/TOOL.md`)
- [ ] Implement tool index builder
- [ ] Add `read_tool_documentation` system tool
- [ ] Implement hybrid approach (hot tools + index)
- [ ] Test with complex multi-tool scenarios

### Week 3-4: Hook System
- [ ] Define hook interface and registry
- [ ] Implement built-in hooks (debug, A/B test, time-based)
- [ ] Add hook configuration loading
- [ ] Integrate hooks into context assembler
- [ ] Create documentation for custom hooks

### Week 4-6: Shadow Agent
- [ ] Implement shadow agent core
- [ ] Build quality gate subagent
- [ ] Build context enricher subagent
- [ ] Integrate with orchestrator
- [ ] Connect to existing frontend (`shadowServiceStore.js`)
- [ ] Build metrics/logging infrastructure
- [ ] Test with production-like scenarios

---

## Success Metrics

| Pattern | Metric | Target |
|---------|--------|--------|
| Prompt Modes | Token reduction in routing | -70% |
| Prompt Modes | Routing chain latency | -40% |
| Lazy Tool Loading | Base prompt tokens | -50% |
| Lazy Tool Loading | Prompt cache hit rate | +30% |
| Hook System | Time to deploy A/B test | <1 hour |
| Shadow Agent | Response quality score | +15% |
| Shadow Agent | Proactive suggestions rate | >10% of conversations |

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Lazy loading increases latency | Medium | Pre-warm common tools, cache TOOL.md reads |
| Shadow agent adds latency | High | Async mode with timeout, use fast models |
| Hooks create debugging complexity | Medium | Comprehensive logging, hook tracing in event trace |
| Mode selection errors | Medium | Fallback to FULL mode, monitoring |

---

## Open Questions

1. **Hook persistence:** Should hook state (e.g., A/B variant assignment) persist across sessions?
2. **Shadow agent escalation:** How should blocked responses be handled in the UI?
3. **Tool documentation ownership:** Should product teams own their tool docs?
4. **Shadow agent cost:** What's the acceptable cost increase for shadow validation?

---

*Document created: January 2026*
*Authors: Platform Team + Claude*
