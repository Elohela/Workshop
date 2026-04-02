# Multi-Agent System Architecture

## Overview

A coordinated suite of specialized agents orchestrated by a central router.
Each agent owns a distinct capability domain and communicates through a
shared message bus with structured handoffs.

```
                           +------------------+
                           |   Orchestrator   |
                           |   (Router Agent) |
                           +--------+---------+
                                    |
          +----------+--------------+--------------+----------+
          |          |              |              |           |
   +------+---+ +---+----+  +-----+------+ +-----+-----+ +--+--------+
   | Research  | | Builder|  |  Reviewer  | |  Advisor   | |  Visual   |
   |  Agent    | |  Agent |  |   Agent    | |   Agent    | | Designer  |
   +------+---+ +---+----+  +-----+------+ +-----+-----+ +--+--------+
          |          |              |              |           |
   +------+---+ +---+----+  +-----+------+ +-----+-----+ +--+--------+
   | Search   | | Code   |  | Analysis   | | Scope     | | Color     |
   | Read     | | Write  |  | Lint/Test  | | Tradeoffs | | Layout    |
   | Summarize| | Shell  |  | Security   | | Priorities| | Typography|
   +----------+ +--------+  +------------+ +-----------+ +-----------+
```

---

## Core Principles

1. **Single Responsibility** — Each agent does one thing well
2. **Structured Handoffs** — Agents pass typed messages, not free text
3. **Orchestrator Decides** — One agent routes; specialists execute
4. **Shared Context, Isolated Execution** — Agents share a context store but run independently
5. **Fail Gracefully** — Any agent can fail without crashing the system

---

## Architecture Components

### 1. Orchestrator (Router Agent)

The brain of the system. Receives user requests, decomposes them into
subtasks, and delegates to the right specialist.

**Responsibilities:**
- Parse user intent
- Break complex tasks into subtasks
- Route subtasks to specialist agents
- Aggregate results and respond to the user
- Handle retries and fallbacks

**Decision Logic:**
```
User Request
    |
    v
[Intent Classification]
    |
    +---> research?  ---> Research Agent
    +---> build?     ---> Builder Agent
    +---> review?    ---> Reviewer Agent
    +---> scoping?   ---> Advisor Agent (challenge assumptions first)
    +---> visual?    ---> Visual Designer Agent
    +---> composite? ---> Decompose into subtasks, fan out
```

### 2. Specialist Agents

#### Research Agent
- **Purpose:** Gather information, search codebases, read docs, summarize
- **Tools:** web search, file read, glob, grep, summarization
- **Output:** Structured findings with sources and confidence scores

#### Builder Agent
- **Purpose:** Generate code, create files, run builds
- **Tools:** code generation, file write, shell execution, package management
- **Output:** File diffs, build results, error logs

#### Reviewer Agent
- **Purpose:** Analyze code quality, find bugs, check security, run tests
- **Tools:** static analysis, test runners, security scanners, linters
- **Output:** Review report with severity-ranked findings

#### Planner Agent
- **Purpose:** Break down ambiguous or large tasks into actionable steps
- **Tools:** context read, task decomposition, dependency analysis
- **Output:** Ordered task list with dependencies and acceptance criteria

#### Advisor Agent (Scope Challenger)
- **Purpose:** Push back on scope creep, question assumptions, force tradeoff decisions. This agent is deliberately contrarian — its job is to make sure you're building the right thing before you build the thing right.
- **Personality:** Direct, Socratic, allergic to hand-waving. Asks "why" more than "how." Won't let vague requirements slide.
- **Tools:** context read, task history analysis, complexity estimation, requirement comparison
- **Output:** Structured challenge report with verdicts

**Advisor triggers automatically when:**
- A new feature request arrives (pre-build gate)
- Task scope expands mid-session
- Builder Agent estimates > N files changed
- User says "also", "while we're at it", or "one more thing"

**Challenge Report format:**
```json
{
  "verdict": "challenge",          // "approve" | "challenge" | "reject"
  "scope_rating": "large",        // "trivial" | "small" | "medium" | "large" | "epic"
  "questions": [
    "Do you need this for launch or is it a nice-to-have?",
    "This touches auth and payments — are you sure you want both in one PR?",
    "You asked for 'simple' but described 4 edge cases. Which 2 matter most?"
  ],
  "suggested_cuts": [
    "Drop the admin dashboard for v1 — add it when someone asks for it",
    "Use a static config instead of building a settings UI"
  ],
  "complexity_estimate": {
    "files_touched": 12,
    "risk_areas": ["auth", "database migration"],
    "simpler_alternative": "Skip the custom OAuth flow; use a third-party provider"
  }
}
```

**Advisor operating principles:**
1. **YAGNI enforcer** — If nobody asked for it, don't build it
2. **Scope slicer** — Always look for the 20% effort that delivers 80% value
3. **Assumption hunter** — Surface hidden assumptions before they become bugs
4. **Tradeoff articulator** — Don't just say "it's complex"; say what you'd cut and why
5. **Time-boxed** — Challenges must be actionable, not philosophical

#### Visual Designer Agent
- **Purpose:** Make opinionated aesthetic decisions about UI, layout, color, typography, and visual hierarchy. This agent has taste — it doesn't ask what you want, it tells you what looks good and why.
- **Personality:** Confident, specific, design-literate. References real design systems and principles. Prefers showing over telling.
- **Tools:** CSS generation, color palette tools, layout analysis, screenshot comparison, design token management
- **Output:** Design decisions with rationale, CSS/style code, visual specifications

**Design system awareness:**
```json
{
  "palette": {
    "philosophy": "Contrast-driven, not pastel. Every color earns its place.",
    "primary": "#1a1a2e",
    "accent": "#e94560",
    "surface": "#f8f9fa",
    "text": "#16213e",
    "rules": [
      "Never use pure black (#000) for text — it vibrates on white",
      "Accent color is for ONE thing per viewport. If everything is emphasized, nothing is.",
      "Background gradients are a crutch. Use whitespace instead."
    ]
  },
  "typography": {
    "philosophy": "Two fonts max. If you need three, your hierarchy is broken.",
    "heading": "Inter or system-ui, 600-700 weight",
    "body": "Same family, 400 weight, 1.6 line-height minimum",
    "rules": [
      "Body text under 16px is a readability bug, not a style choice",
      "Letter-spacing on uppercase headings: always. On body text: never.",
      "If you're using more than 4 font sizes, simplify your component hierarchy"
    ]
  },
  "spacing": {
    "philosophy": "Generous whitespace signals confidence. Cramped layouts signal panic.",
    "base_unit": "8px",
    "rules": [
      "Padding inside components: 16-24px minimum",
      "Margin between sections: 64-96px. Let the content breathe.",
      "Consistent spacing > pixel-perfect alignment"
    ]
  },
  "opinions": [
    "Rounded corners on cards: 8-12px. More than 16px looks like a toy.",
    "Drop shadows should be barely visible. If you can see the shadow, it's too strong.",
    "Hover states are not optional. Every clickable element needs one.",
    "Animations under 200ms or don't bother. 300ms+ feels laggy.",
    "Dark mode is not 'invert the colors'. It's a separate design exercise.",
    "Icons without labels are a guessing game. Label your icons.",
    "Hero sections taller than 80vh are self-indulgent. Get to the content."
  ]
}
```

**Visual Designer output format:**
```json
{
  "decision": "Redesign the card grid layout",
  "rationale": "Current 3-column grid creates orphan cards at common breakpoints. A 2/4 responsive grid with 24px gaps gives consistent rhythm across devices.",
  "changes": [
    {
      "target": ".gallery-grid",
      "property": "grid-template-columns",
      "from": "repeat(3, 1fr)",
      "to": "repeat(auto-fit, minmax(280px, 1fr))",
      "why": "Fluid grid prevents orphans and eliminates the need for breakpoint-specific overrides"
    }
  ],
  "css": "/* generated CSS here */",
  "visual_hierarchy_notes": "The section title competes with the card content. Reduce title size from 2.5rem to 2rem and add 48px margin-bottom to create clear separation."
}
```

**Visual Designer operating principles:**
1. **Opinionated by default** — Proposes a specific solution, not a menu of options
2. **Justifies with principles** — Every choice traces back to readability, hierarchy, or rhythm
3. **Mobile-first** — Designs for the smallest screen, then enhances
4. **Consistency over novelty** — A boring design system beats creative chaos
5. **Ships CSS, not mockups** — Output is working code, not descriptions of what it could look like

### 3. Message Bus

Agents communicate via a typed message protocol — not raw strings.

```json
{
  "id": "msg_abc123",
  "from": "orchestrator",
  "to": "research_agent",
  "type": "task",
  "payload": {
    "action": "search_codebase",
    "query": "authentication middleware",
    "constraints": {
      "max_results": 10,
      "file_types": ["*.ts", "*.js"]
    }
  },
  "context_ref": "ctx_session_001",
  "priority": "normal",
  "timeout_ms": 30000
}
```

```json
{
  "id": "msg_def456",
  "from": "research_agent",
  "to": "orchestrator",
  "type": "result",
  "payload": {
    "status": "success",
    "findings": [...],
    "confidence": 0.85,
    "sources": [...]
  },
  "parent_id": "msg_abc123"
}
```

### 4. Context Store

A shared key-value store that agents read from and write to. Prevents
redundant work and maintains session continuity.

```
+-------------------------------------------+
|            Context Store                   |
|-------------------------------------------|
| session_id    | current user session       |
| task_history  | completed subtasks         |
| file_cache    | recently read files        |
| decisions     | choices made this session  |
| artifacts     | generated outputs          |
+-------------------------------------------+
```

**Rules:**
- Agents READ freely from shared context
- Agents WRITE only to their own namespace
- Orchestrator merges agent outputs into shared state

---

## Execution Patterns

### Sequential Pipeline
For tasks with dependencies:
```
Research --> Plan --> Advisor (challenge scope) --> Build --> Review --> Done
```

### Parallel Fan-Out
For independent subtasks:
```
Orchestrator --+--> Research Agent (part A)
               +--> Research Agent (part B)
               +--> Builder Agent (scaffolding)
               |
               +--> [await all] --> Merge --> Next step
```

### Iterative Loop
For tasks requiring refinement:
```
Build --> Review --> [issues found?]
                        yes --> Build (fix) --> Review --> ...
                        no  --> Done
```

### Gated Build Pipeline (with Advisor + Designer)
For feature work where scope discipline and aesthetics matter:
```
User Request
    |
    v
Advisor (challenge scope, force tradeoffs)
    |
    +--> [scope approved?]
    |        no  --> Advisor returns cuts/questions to user
    |        yes --> continue
    v
Planner (break into tasks)
    |
    +----> Visual Designer (in parallel: design system, CSS, layout)
    +----> Builder (in parallel: logic, data, API)
    |
    +--> [merge design + build]
    v
Reviewer (quality + visual consistency check)
    |
    v
Done
```

This is the recommended default for any user-facing feature. The Advisor
acts as a **pre-build gate** — nothing gets built until scope is justified.
The Visual Designer and Builder run in parallel so design decisions don't
bottleneck implementation.

---

## Agent Lifecycle

```
IDLE --> ASSIGNED --> RUNNING --> COMPLETED
                        |              |
                        v              v
                     FAILED       [result to orchestrator]
                        |
                        v
                  [retry or escalate]
```

Each agent reports:
- `started` — acknowledged the task
- `progress` — intermediate updates (optional)
- `completed` — final result
- `failed` — error with diagnostic info

---

## Error Handling Strategy

| Failure Type        | Response                                      |
|---------------------|-----------------------------------------------|
| Agent timeout       | Retry once, then escalate to orchestrator     |
| Agent error         | Log, retry with modified params if possible   |
| Conflicting results | Orchestrator resolves or asks user             |
| All agents fail     | Surface error to user with diagnostic context |

---

## Extension Points

Adding a new agent requires:

1. **Define the agent's role** — what it does, what tools it needs
2. **Register with orchestrator** — add routing rules for when to invoke it
3. **Implement the interface:**

```python
class Agent:
    name: str
    description: str
    tools: list[Tool]

    async def handle(self, message: Message, context: Context) -> Result:
        """Process a task message and return a result."""
        ...
```

4. **Add to the message bus** — agent can now send/receive messages

---

## Recommended Tech Stack

| Component       | Recommendation                  | Why                                        |
|-----------------|---------------------------------|--------------------------------------------|
| Agent runtime   | Python + Claude Agent SDK       | First-class tool use, async, typed          |
| Message bus     | In-process async queue          | Start simple; swap for Redis/NATS later     |
| Context store   | In-memory dict → SQLite         | No infra overhead; upgrade path exists      |
| LLM backbone    | Claude Opus/Sonnet via API      | Strong reasoning + tool use capabilities    |
| Orchestration   | Custom router or LangGraph      | Full control over routing logic             |

---

## Project Structure

```
agents/
├── orchestrator.py          # Central router + task decomposition
├── agents/
│   ├── base.py              # Agent interface + shared types
│   ├── research.py          # Research agent implementation
│   ├── builder.py           # Code generation agent
│   ├── reviewer.py          # Code review + analysis agent
│   ├── planner.py           # Task planning agent
│   ├── advisor.py           # Scope challenger + tradeoff enforcer
│   └── visual_designer.py   # Aesthetic decisions + CSS generation
├── bus/
│   ├── message.py           # Message types + serialization
│   └── queue.py             # Message queue implementation
├── context/
│   ├── store.py             # Shared context store
│   └── session.py           # Session management
├── tools/
│   ├── search.py            # Web/code search tools
│   ├── files.py             # File read/write tools
│   ├── shell.py             # Command execution tools
│   ├── analysis.py          # Lint, test, security tools
│   └── design.py            # Color, typography, layout tools
├── config.py                # Agent registry + routing config
└── main.py                  # Entry point
```

---

## Next Steps

1. **Scaffold the project** — set up the directory structure and base classes
2. **Build the orchestrator** — intent classification + routing logic
3. **Implement one agent** — start with Research Agent as proof of concept
4. **Add the message bus** — typed messages between orchestrator and agents
5. **Wire up tools** — connect real capabilities (file I/O, search, shell)
6. **Add agents incrementally** — Builder, Reviewer, Planner
7. **Add the Advisor** — wire it as a pre-build gate in the orchestrator
8. **Add the Visual Designer** — parallel track alongside Builder for UI work
9. **Test end-to-end** — complex multi-step task through the full gated pipeline
