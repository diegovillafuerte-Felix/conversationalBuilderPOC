# Moltbot Prompt Architecture: A Deep Dive

This document explains how Moltbot dynamically assembles coherent, context-aware system prompts for AI agents. These principles can be applied to any agentic AI system that needs configurable identity, modular capabilities, and secure context management.

---

## Table of Contents

1. [Core Philosophy](#core-philosophy)
2. [Architecture Overview](#architecture-overview)
3. [Bootstrap Files - The Personality Layer](#bootstrap-files---the-personality-layer)
4. [SOUL.md - The Identity Core](#soulmd---the-identity-core)
5. [Hook System - Dynamic Prompt Modification](#hook-system---dynamic-prompt-modification)
6. [Skills System - Lazy Loading for Token Efficiency](#skills-system---lazy-loading-for-token-efficiency)
7. [Context Isolation - Security Boundaries](#context-isolation---security-boundaries)
8. [Prompt Modes - Contextual Prompt Sizing](#prompt-modes---contextual-prompt-sizing)
9. [System Prompt Assembly](#system-prompt-assembly)
10. [Configuration & Customization](#configuration--customization)
11. [Design Principles & Benefits](#design-principles--benefits)
12. [Implementation Patterns for Your Own Project](#implementation-patterns-for-your-own-project)

---

## Core Philosophy

Moltbot's prompt system is built on several key principles:

1. **User-editable identity**: Non-developers should be able to customize agent personality without touching code
2. **Separation of concerns**: Identity, behavior rules, environment config, and capabilities are separate files
3. **Token efficiency**: Only include what's needed for each specific context
4. **Security by default**: Sensitive information doesn't leak to sub-agents or shared contexts
5. **Extensibility**: Hooks allow customization without forking core code
6. **Progressive disclosure**: Capabilities are listed but loaded on-demand

---

## Architecture Overview

### Assembly Flow

```
Session Start
    │
    ▼
┌─────────────────────────────────┐
│  Load Bootstrap Files           │
│  (SOUL.md, AGENTS.md, etc.)     │
└─────────────┬───────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│  Apply Hook Overrides           │
│  (persona swapping, injection)  │
└─────────────┬───────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│  Build Bootstrap Context        │
│  (truncate, format, filter)     │
└─────────────┬───────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│  Load & Format Skills           │
│  (XML skill list with paths)    │
└─────────────┬───────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│  Assemble System Prompt         │
│  (buildAgentSystemPrompt)       │
└─────────────┬───────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│  Inject into Agent Runtime      │
└─────────────────────────────────┘
```

### Key Components

| Component | Responsibility |
|-----------|---------------|
| `workspace.ts` | Load/save bootstrap files from disk |
| `bootstrap-files.ts` | Orchestrate bootstrap loading and filtering |
| `bootstrap-hooks.ts` | Apply hook transformations |
| `bootstrap.ts` | Truncate and format content for injection |
| `skills/workspace.ts` | Load skills and build XML prompt |
| `system-prompt.ts` | Assemble final prompt from all components |

---

## Bootstrap Files - The Personality Layer

Bootstrap files are user-editable markdown files that define the agent's identity, behavior, and context. They live in a workspace directory and are loaded fresh each session.

### File Inventory

| File | Purpose | Injected To |
|------|---------|-------------|
| **SOUL.md** | Core identity, personality, tone, boundaries | Main sessions only |
| **AGENTS.md** | Workspace rules, memory management, safety guidelines, group chat behavior | All contexts |
| **TOOLS.md** | Environment-specific notes (device names, SSH hosts, API endpoints, preferences) | All contexts |
| **IDENTITY.md** | Agent metadata (name, creature type, emoji, avatar URL) | Main sessions only |
| **USER.md** | User context, preferences, background info | Main sessions only |
| **HEARTBEAT.md** | Instructions for periodic heartbeat polling | Main sessions only |
| **BOOTSTRAP.md** | First-run setup instructions (deleted after use) | New workspaces only |
| **MEMORY.md** | Long-term curated memories | Main sessions only (never shared) |

### Why Separate Files?

1. **Single Responsibility**: Each file has one clear purpose
2. **Selective Loading**: Different contexts can load different files
3. **User-Friendly Editing**: Users edit small, focused files instead of one massive config
4. **Version Control**: Changes to identity vs. behavior vs. tools are tracked separately
5. **Security Filtering**: Easy to exclude sensitive files from certain contexts

### Loading Priority and Filtering

```typescript
// Files are loaded in this order
const BOOTSTRAP_FILES = [
  "AGENTS.md",     // Always first - establishes ground rules
  "SOUL.md",       // Identity/persona
  "TOOLS.md",      // Environment config
  "IDENTITY.md",   // Metadata
  "USER.md",       // User context
  "HEARTBEAT.md",  // Heartbeat instructions
  "BOOTSTRAP.md",  // First-run only
];

// Sub-agents only receive these files
const SUBAGENT_BOOTSTRAP_ALLOWLIST = new Set([
  "AGENTS.md",
  "TOOLS.md"
]);
```

---

## SOUL.md - The Identity Core

SOUL.md is the most important bootstrap file. It defines *who* the agent is - not just what it can do, but how it thinks, communicates, and relates to the user.

### Example Structure

```markdown
# SOUL.md - Who You Are

## Core Truths
- Be genuinely helpful, not performatively helpful
- Have opinions - disagree, prefer things, find stuff amusing
- Be resourceful before asking for help
- Earn trust through competence
- Remember you're a guest in someone's digital life

## Communication Style
- Direct and concise, not corporate or stiff
- Use humor when appropriate, but don't force it
- Match the user's energy and formality level
- Explain your reasoning when making decisions

## Boundaries
- Private things stay private
- Ask before taking external actions (sending emails, posting, etc.)
- Never send half-baked or placeholder responses
- When uncertain, say so

## Vibe
"Be the assistant you'd actually want to talk to -
competent, genuine, occasionally funny, never annoying."
```

### Why SOUL.md Matters

1. **Consistent Personality**: Every session starts with the same core identity
2. **User Customization**: Users can craft exactly the persona they want
3. **Separation from Rules**: Identity (SOUL) is separate from behavior (AGENTS)
4. **Swappable**: Hooks can swap SOUL.md for alternate personas

### Use Cases

- **Professional vs. Casual**: Different SOUL.md for work vs. personal use
- **Domain-Specific Personas**: A coding assistant vs. a writing assistant
- **Branded Agents**: Company-specific tone and personality
- **Experimental**: A/B test different personas

---

## Hook System - Dynamic Prompt Modification

Hooks are an extensibility mechanism that allow intercepting and modifying the prompt assembly pipeline without changing core code.

### How Hooks Work

```typescript
// The pipeline emits events at key points
let bootstrapFiles = loadWorkspaceBootstrapFiles();

// Hooks can intercept and transform
bootstrapFiles = await applyBootstrapHookOverrides(bootstrapFiles, {
  hookEvent: "agent:bootstrap",
  context: { workspaceDir, userTimezone, ... }
});

const contextFiles = buildBootstrapContextFiles(bootstrapFiles);
```

### Built-in Example: soul-evil

The "soul-evil" hook demonstrates persona swapping. Despite the name, it's a general-purpose persona variation system.

```json
{
  "hooks": {
    "internal": {
      "entries": {
        "soul-evil": {
          "enabled": true,
          "file": "SOUL_EVIL.md",
          "chance": 0.1,
          "purge": {
            "at": "21:00",
            "duration": "15m"
          }
        }
      }
    }
  }
}
```

**Activation conditions:**
- **Random chance**: 10% probability on any message
- **Purge window**: Always active during 21:00-21:15 in user's timezone

**How it works:**
1. Hook checks if conditions are met (chance OR time window)
2. If triggered, reads `SOUL_EVIL.md` from workspace
3. Replaces `SOUL.md` content in memory (original file unchanged)
4. Modified bootstrap files continue through pipeline

### Use Cases for Hooks

1. **Persona Variation**
   - Alternate personality during certain hours
   - Different personas for different platforms (Discord vs. SMS)
   - "Unhinged mode" that activates randomly

2. **Dynamic Content Injection**
   ```typescript
   // Inject current context into TOOLS.md
   if (file.name === "TOOLS.md") {
     const weather = await getWeather();
     const calendar = await getNextEvent();
     file.content += `\n\n## Current Context\n- Weather: ${weather}\n- Next event: ${calendar}`;
   }
   ```

3. **A/B Testing**
   - Randomly assign users to persona variants
   - Track which performs better on user satisfaction

4. **Feature Flags**
   - Inject or remove capabilities based on config
   - Enable experimental features for beta users

5. **User-Specific Customization**
   - Load different SOUL.md based on who's messaging
   - Premium users get enhanced persona

6. **Time-Aware Behavior**
   - Formal during work hours, casual evenings
   - Holiday-themed personas that auto-activate

7. **Debug Mode**
   ```typescript
   if (config.debug) {
     files.push({
       name: "DEBUG.md",
       content: "Log all tool calls. Explain reasoning verbosely."
     });
   }
   ```

### Benefits of Hook Architecture

- **No core code changes**: Extend functionality without forking
- **Composable**: Multiple hooks can chain together
- **Testable**: Hooks are isolated, pure functions
- **Rollback-friendly**: Disable a hook instantly if it causes issues

---

## Skills System - Lazy Loading for Token Efficiency

Skills define capabilities the agent can use (web browsing, file editing, API integrations). Instead of including full skill instructions in every prompt, Moltbot uses lazy loading.

### The Problem with Inline Skills

```
Traditional approach:
┌─────────────────────────────────────┐
│ System Prompt                       │
│ ├─ Identity (500 tokens)            │
│ ├─ Rules (1,000 tokens)             │
│ ├─ Skill: Web Browser (5,000 tokens)│
│ ├─ Skill: File Editor (3,000 tokens)│
│ ├─ Skill: Calendar (4,000 tokens)   │
│ ├─ Skill: Email (6,000 tokens)      │
│ ├─ ... 10 more skills ...           │
│ └─ Total: 50,000+ tokens            │
└─────────────────────────────────────┘

Problem: Most messages use 0-2 skills, but you pay
for all 50,000 tokens on every request.
```

### Moltbot's Solution: Lazy Loading

```
Moltbot approach:
┌─────────────────────────────────────┐
│ System Prompt                       │
│ ├─ Identity (500 tokens)            │
│ ├─ Rules (1,000 tokens)             │
│ └─ Skill Index (500 tokens total)   │
│     ├─ web-browser: "Browse web..." │
│     ├─ file-editor: "Edit files..." │
│     └─ ... (just names + 1-liners)  │
│ Total: ~3,000 tokens                │
└─────────────────────────────────────┘

When model needs a skill → reads SKILL.md on demand
```

### Implementation

**Skill index format (injected into prompt):**
```xml
<available_skills>
  <skill>
    <name>web-browser</name>
    <description>Control web browser for research and automation</description>
    <location>/workspace/skills/web-browser/SKILL.md</location>
  </skill>
  <skill>
    <name>file-editor</name>
    <description>Read, write, and edit files with syntax awareness</description>
    <location>/workspace/skills/file-editor/SKILL.md</location>
  </skill>
</available_skills>
```

**Prompt instruction:**
```
When you need to use a skill, first read its SKILL.md file at the
location listed above to get detailed instructions.
```

### Benefits

1. **Token Efficiency**: Base prompt stays small (~3-5k tokens vs 50k+)
2. **Better Caching**: Skill list rarely changes, so prompt can be cached
3. **Pay-per-use**: Only load skills actually needed
4. **Unlimited Detail**: Skills can have extensive documentation without bloating every request
5. **Dynamic Skills**: Add/remove skills without changing prompt assembly code

### Tradeoff

The model needs one extra read operation before using a skill for the first time in a session. This is almost always worth it given the token savings.

### Skill Loading Priority

Skills can come from multiple sources with clear precedence:

```
extra < bundled < managed < workspace
```

- **extra**: Programmatically injected skills
- **bundled**: Default skills shipped with the system
- **managed**: Auto-installed from a skill registry
- **workspace**: User-created skills (highest priority, can override others)

---

## Context Isolation - Security Boundaries

Context isolation prevents sensitive information from leaking between execution contexts. This is critical for security and privacy.

### The Problem

```
Without isolation:
┌─────────────────────────────────────────────────┐
│ Main Session                                    │
│ ├─ SOUL.md (your personality)                   │
│ ├─ USER.md (personal info about you)            │
│ ├─ MEMORY.md (private memories, secrets)        │
│ └─ Spawns sub-agent for web research            │
│     └─ Sub-agent has access to MEMORY.md! 😱    │
│         └─ Could be manipulated by malicious    │
│            web content to exfiltrate data       │
└─────────────────────────────────────────────────┘
```

### The Solution: Filtered Bootstrap Files

```typescript
// Sub-agents only receive safe, non-sensitive files
const SUBAGENT_BOOTSTRAP_ALLOWLIST = new Set([
  "AGENTS.md",   // General behavior rules - safe
  "TOOLS.md"     // Environment notes - safe
]);

// These are EXCLUDED from sub-agents:
// - SOUL.md      (may contain private personality context)
// - USER.md      (personal user information)
// - MEMORY.md    (private memories, secrets)
// - IDENTITY.md  (not needed for subtasks)
```

### Context Matrix

| File | Main Session | Sub-Agent | Group Chat |
|------|:------------:|:---------:|:----------:|
| AGENTS.md | ✅ | ✅ | ✅ |
| TOOLS.md | ✅ | ✅ | ✅ |
| SOUL.md | ✅ | ❌ | ✅ |
| IDENTITY.md | ✅ | ❌ | ❌ |
| USER.md | ✅ | ❌ | ❌ |
| MEMORY.md | ✅ | ❌ | ❌ |
| HEARTBEAT.md | ✅ | ❌ | ❌ |

### MEMORY.md - Special Handling

From the AGENTS.md template:

```markdown
### 🧠 MEMORY.md - Your Long-Term Memory
- **ONLY load in main session** (direct chats with your human)
- **DO NOT load in shared contexts** (Discord, group chats, sessions with others)
- This is for **security** — contains personal context that shouldn't leak
```

MEMORY.md is like a private journal - it only comes out in 1:1 conversations with the owner.

### Benefits

1. **Privacy Protection**: Personal memories don't leak to sub-agents
2. **Security Boundary**: Compromised sub-agent has less to exfiltrate
3. **Token Efficiency**: Sub-agents don't load unnecessary context
4. **Clean Separation**: Different contexts have appropriate information

### Implementation Pattern

```typescript
function filterBootstrapFilesForSession(
  files: BootstrapFile[],
  sessionType: "main" | "subagent" | "group"
): BootstrapFile[] {
  if (sessionType === "main") {
    return files; // Main session gets everything
  }

  if (sessionType === "subagent") {
    return files.filter(f => SUBAGENT_ALLOWLIST.has(f.name));
  }

  if (sessionType === "group") {
    return files.filter(f => !PRIVATE_FILES.has(f.name));
  }
}
```

---

## Prompt Modes - Contextual Prompt Sizing

Different execution contexts need different prompt sizes. Moltbot uses "prompt modes" to control which sections are included.

### Three Modes

| Mode | Use Case | Size | Includes |
|------|----------|------|----------|
| **full** | Main agent session | Large | All sections |
| **minimal** | Sub-agents, parallel tasks | Small | Essential sections only |
| **none** | Internal/utility calls | Tiny | Just identity line |

### Full Mode Sections

```
1.  Identity line
2.  Tooling (available tools + descriptions)
3.  Tool call style guidance
4.  CLI quick reference
5.  Skills (XML skill index)
6.  Memory recall instructions
7.  Self-update instructions
8.  Model aliases
9.  Workspace path
10. Documentation links
11. Sandbox info (if enabled)
12. User identity
13. Current date & time
14. Workspace files header
15. Reply tags
16. Messaging instructions
17. Voice/TTS config
18. Group chat context
19. Reactions guidance
20. Reasoning format
21. Project context (bootstrap files injected here)
22. Silent replies
23. Heartbeats
24. Runtime info
```

### Minimal Mode Sections

```
1. Identity line
2. Tooling
3. Workspace path
4. Sandbox info (if enabled)
5. Current date & time
6. Runtime info
7. Filtered bootstrap files (AGENTS.md, TOOLS.md only)
```

**Excluded from minimal:**
- Skills (sub-agents don't need skill discovery)
- Memory recall
- Self-update
- User identity
- Reply tags
- Messaging instructions
- Heartbeats
- Most bootstrap files

### None Mode

```
"You are a personal assistant running inside Moltbot."
```

Used for internal operations where the model just needs to do a simple task.

### Benefits

1. **Token Efficiency**: Sub-agents use ~70% fewer tokens
2. **Faster Response**: Smaller prompts process faster
3. **Context Isolation**: Less information means less risk
4. **Cost Savings**: Significant reduction in API costs for parallel operations

---

## System Prompt Assembly

The `buildAgentSystemPrompt` function orchestrates final assembly.

### Function Signature

```typescript
function buildAgentSystemPrompt(params: {
  // Mode control
  promptMode: "full" | "minimal" | "none";

  // Core context
  workspaceDir: string;
  contextFiles: EmbeddedContextFile[];  // Bootstrap files

  // Capabilities
  toolNames: string[];
  toolSummaries: Map<string, string>;
  skillsPrompt?: string;  // XML skill index

  // User context
  ownerNumbers?: string[];
  userTimezone?: string;

  // Environment
  sandboxInfo?: SandboxInfo;
  heartbeatPrompt?: string;

  // Additional context
  extraSystemPrompt?: string;

  // ... many more options
}): string;
```

### Assembly Order

```typescript
function buildAgentSystemPrompt(params) {
  const sections: string[] = [];

  // 1. Identity
  sections.push("You are a personal assistant running inside Moltbot.");

  // 2. Tooling (always included)
  sections.push(buildToolingSection(params.toolNames, params.toolSummaries));

  // Mode-dependent sections
  if (params.promptMode === "full") {
    // 3. Skills
    if (params.skillsPrompt) {
      sections.push(buildSkillsSection(params.skillsPrompt));
    }

    // 4. Memory recall
    sections.push(buildMemorySection());

    // 5. Self-update instructions
    sections.push(buildSelfUpdateSection());

    // ... many more full-mode sections
  }

  // Common sections (all modes)
  sections.push(buildWorkspaceSection(params.workspaceDir));
  sections.push(buildTimeSection(params.userTimezone));
  sections.push(buildRuntimeSection());

  // Inject bootstrap files
  if (params.contextFiles.length > 0) {
    sections.push("## Project Context");
    for (const file of params.contextFiles) {
      sections.push(`### ${file.path}\n\n${file.content}`);
    }
  }

  return sections.join("\n\n");
}
```

### Content Truncation

Large bootstrap files are truncated to prevent context overflow:

```typescript
const DEFAULT_BOOTSTRAP_MAX_CHARS = 20_000;

function trimBootstrapContent(content: string, maxChars: number): string {
  if (content.length <= maxChars) return content;

  const headSize = Math.floor(maxChars * 0.7);  // 70% from beginning
  const tailSize = Math.floor(maxChars * 0.2);  // 20% from end

  const head = content.slice(0, headSize);
  const tail = content.slice(-tailSize);

  return `${head}\n\n[... content truncated ...]\n\n${tail}`;
}
```

---

## Configuration & Customization

### Key Configuration Options

```yaml
agents:
  defaults:
    # Bootstrap file handling
    bootstrapMaxChars: 20000    # Max chars per file before truncation

    # Time handling
    userTimezone: "America/New_York"
    timeFormat: "auto"          # "auto" | "12" | "24"

    # Workspace
    workspace: "~/clawd"        # Default workspace directory

    # Skills
    skillsDir: "skills"         # Relative to workspace
```

### Hook Configuration

```yaml
hooks:
  internal:
    entries:
      soul-evil:
        enabled: true
        file: "SOUL_ALTERNATE.md"
        chance: 0.05              # 5% random activation
        purge:
          at: "22:00"             # Daily activation window
          duration: "30m"
```

### Per-Channel Customization

Different communication channels can have different settings:

```yaml
channels:
  discord:
    capabilities:
      reactions: extensive       # Use emoji reactions freely
      formatting: limited        # No markdown tables

  sms:
    capabilities:
      reactions: none
      formatting: plain          # Plain text only
```

---

## Design Principles & Benefits

### 1. Separation of Concerns

**Principle**: Each file/component has one clear responsibility.

**Benefits**:
- Easier to understand and maintain
- Changes are isolated
- Users edit only what they need
- Testing is straightforward

### 2. User-Editable Configuration

**Principle**: Identity and behavior defined in markdown files, not code.

**Benefits**:
- Non-developers can customize agents
- No redeployment needed for persona changes
- Version control friendly
- Easy to share and replicate setups

### 3. Token Efficiency Through Lazy Loading

**Principle**: Only include what's needed for each request.

**Benefits**:
- 70-90% reduction in base prompt size
- Better prompt caching
- Lower API costs
- Faster responses

### 4. Security by Default

**Principle**: Sensitive information is excluded unless explicitly needed.

**Benefits**:
- Private data doesn't leak to sub-agents
- Compromised components have limited access
- Clear mental model for what's shared where

### 5. Extensibility Through Hooks

**Principle**: Modify behavior without changing core code.

**Benefits**:
- Plugin architecture for customization
- Safe experimentation
- Easy rollback
- Community contributions

### 6. Progressive Disclosure

**Principle**: List capabilities but load details on demand.

**Benefits**:
- Base prompt stays manageable
- Unlimited capability depth
- Model learns what it needs when it needs it

### 7. Prompt Mode Differentiation

**Principle**: Different contexts get appropriately-sized prompts.

**Benefits**:
- Main session gets full capability
- Sub-agents are fast and focused
- Cost optimization for parallel operations

---

## Implementation Patterns for Your Own Project

### Pattern 1: Bootstrap File System

```typescript
// Define your bootstrap files
const BOOTSTRAP_FILES = {
  IDENTITY: "IDENTITY.md",     // Who the agent is
  RULES: "RULES.md",           // Behavior guidelines
  CONTEXT: "CONTEXT.md",       // User/environment context
  MEMORY: "MEMORY.md",         // Long-term memory
};

// Load with filtering
async function loadBootstrapFiles(
  workspaceDir: string,
  sessionType: SessionType
): Promise<BootstrapFile[]> {
  const files = await Promise.all(
    Object.values(BOOTSTRAP_FILES).map(async (filename) => ({
      name: filename,
      content: await readFile(path.join(workspaceDir, filename)),
    }))
  );

  return filterForSessionType(files, sessionType);
}
```

### Pattern 2: Hook System

```typescript
type HookEvent = "bootstrap" | "pre-prompt" | "post-response";

interface Hook {
  event: HookEvent;
  handler: (data: any, context: any) => Promise<any>;
}

class HookRegistry {
  private hooks: Map<HookEvent, Hook[]> = new Map();

  register(hook: Hook) {
    const existing = this.hooks.get(hook.event) || [];
    this.hooks.set(hook.event, [...existing, hook]);
  }

  async emit(event: HookEvent, data: any, context: any) {
    const hooks = this.hooks.get(event) || [];
    let result = data;
    for (const hook of hooks) {
      result = await hook.handler(result, context);
    }
    return result;
  }
}
```

### Pattern 3: Lazy Skill Loading

```typescript
// Skill index for prompt
interface SkillEntry {
  name: string;
  description: string;  // One-liner
  path: string;         // Full path to SKILL.md
}

function buildSkillIndex(skills: SkillEntry[]): string {
  return `<available_skills>
${skills.map(s => `  <skill>
    <name>${s.name}</name>
    <description>${s.description}</description>
    <location>${s.path}</location>
  </skill>`).join("\n")}
</available_skills>`;
}

// Prompt instruction
const SKILL_INSTRUCTION = `
When you need to use a skill, read its SKILL.md file at the
listed location to get detailed instructions before proceeding.
`;
```

### Pattern 4: Context Isolation

```typescript
enum SessionType {
  MAIN = "main",
  SUBAGENT = "subagent",
  SHARED = "shared",
}

const VISIBILITY_MATRIX: Record<string, SessionType[]> = {
  "IDENTITY.md": [SessionType.MAIN],
  "RULES.md": [SessionType.MAIN, SessionType.SUBAGENT, SessionType.SHARED],
  "CONTEXT.md": [SessionType.MAIN, SessionType.SUBAGENT],
  "MEMORY.md": [SessionType.MAIN],  // Never shared
};

function filterForSessionType(
  files: BootstrapFile[],
  sessionType: SessionType
): BootstrapFile[] {
  return files.filter(f =>
    VISIBILITY_MATRIX[f.name]?.includes(sessionType)
  );
}
```

### Pattern 5: Prompt Mode Builder

```typescript
enum PromptMode {
  FULL = "full",
  MINIMAL = "minimal",
  NONE = "none",
}

function buildSystemPrompt(params: PromptParams): string {
  if (params.mode === PromptMode.NONE) {
    return "You are a helpful assistant.";
  }

  const sections = [
    buildIdentitySection(),
    buildToolingSection(params.tools),
  ];

  if (params.mode === PromptMode.FULL) {
    sections.push(
      buildSkillsSection(params.skills),
      buildMemorySection(),
      buildUserContextSection(params.user),
      // ... other full-mode sections
    );
  }

  sections.push(
    buildWorkspaceSection(params.workspace),
    buildTimeSection(params.timezone),
    buildBootstrapSection(params.bootstrapFiles),
  );

  return sections.filter(Boolean).join("\n\n");
}
```

---

## Summary

Moltbot's prompt architecture demonstrates several best practices for building configurable, secure, and efficient AI agent systems:

1. **Modular identity** through bootstrap files (SOUL.md, AGENTS.md, etc.)
2. **Dynamic customization** through hooks
3. **Token efficiency** through lazy skill loading
4. **Security** through context isolation
5. **Flexibility** through prompt modes

These patterns can be adapted to any agentic AI system that needs:
- User-customizable personality
- Modular capabilities
- Secure information handling
- Cost-effective operation
- Extensible architecture

The key insight is that a well-designed prompt system is not just a static string - it's a dynamic assembly pipeline that adapts to context, respects security boundaries, and optimizes for efficiency.
