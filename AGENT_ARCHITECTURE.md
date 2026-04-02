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
                +----------------+----------------+
                |                |                 |
         +------+------+  +-----+------+  +------+------+
         |  Research   |  |  Builder   |  |  Reviewer   |
         |   Agent     |  |   Agent    |  |   Agent     |
         +------+------+  +-----+------+  +------+------+
                |                |                 |
         +------+------+  +-----+------+  +------+------+
         | Web Search  |  | Code Gen   |  | Analysis    |
         | File Read   |  | File Write |  | Lint/Test   |
         | Summarize   |  | Shell Exec |  | Security    |
         +-------------+  +------------+  +-------------+
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
Research --> Plan --> Build --> Review --> Done
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
│   └── planner.py           # Task planning agent
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
│   └── analysis.py          # Lint, test, security tools
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
7. **Test end-to-end** — complex multi-step task through the full pipeline
