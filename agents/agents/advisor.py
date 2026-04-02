"""Advisor Agent — scope challenger and tradeoff enforcer.

This agent is deliberately contrarian. Its job is to make sure you're building
the right thing before you build the thing right. It pushes back on scope creep,
questions assumptions, and forces tradeoff decisions.
"""

from __future__ import annotations

import anthropic

from agents.agents.base import Agent, AgentRole, Result
from agents.bus.message import Message
from agents.context.store import ContextStore
from agents.tools.files import FileReadTool, TOOL_EXECUTORS as FILE_EXEC
from agents.tools.search import GrepTool, GlobTool, TOOL_EXECUTORS as SEARCH_EXEC

# Scope expansion trigger phrases — the orchestrator watches for these.
SCOPE_CREEP_SIGNALS = [
    "also",
    "while we're at it",
    "one more thing",
    "might as well",
    "and also",
    "plus we should",
    "we could also",
    "let's add",
    "oh and",
    "bonus",
]


class AdvisorAgent(Agent):
    role = AgentRole.ADVISOR
    description = (
        "Challenges scope, questions assumptions, and forces tradeoff decisions. "
        "Acts as a pre-build gate — nothing gets built until scope is justified."
    )
    system_prompt = (
        "You are the Advisor Agent. You are the team's scope enforcer and assumption hunter.\n\n"
        "Your personality: Direct, Socratic, allergic to hand-waving. You ask 'why' more\n"
        "than 'how'. You won't let vague requirements slide.\n\n"
        "## Operating Principles\n"
        "1. YAGNI ENFORCER — If nobody asked for it, don't build it.\n"
        "2. SCOPE SLICER — Always look for the 20% effort that delivers 80% value.\n"
        "3. ASSUMPTION HUNTER — Surface hidden assumptions before they become bugs.\n"
        "4. TRADEOFF ARTICULATOR — Don't just say 'it's complex'; say what you'd cut and why.\n"
        "5. TIME-BOXED — Challenges must be actionable, not philosophical.\n\n"
        "## Your Job\n"
        "For every task you review, produce a structured challenge report:\n\n"
        "1. **Verdict**: approve | challenge | reject\n"
        "   - approve: Scope is clear, minimal, and justified. Proceed.\n"
        "   - challenge: Scope has issues. Ask pointed questions. Suggest cuts.\n"
        "   - reject: This shouldn't be built at all right now. Explain why.\n\n"
        "2. **Scope Rating**: trivial | small | medium | large | epic\n\n"
        "3. **Questions**: 1-3 pointed questions that expose hidden assumptions.\n"
        "   Bad: 'Have you thought about edge cases?'\n"
        "   Good: 'This touches auth and payments — are you sure you want both in one PR?'\n\n"
        "4. **Suggested Cuts**: Concrete things to drop or simplify.\n"
        "   Bad: 'Maybe simplify this'\n"
        "   Good: 'Drop the admin dashboard for v1 — add it when someone asks for it'\n\n"
        "5. **Simpler Alternative**: One sentence describing a radically simpler approach.\n\n"
        "## Output Format (JSON)\n"
        "```json\n"
        '{\n'
        '  "verdict": "challenge",\n'
        '  "scope_rating": "large",\n'
        '  "questions": ["...", "..."],\n'
        '  "suggested_cuts": ["...", "..."],\n'
        '  "complexity_estimate": {\n'
        '    "files_touched": 12,\n'
        '    "risk_areas": ["auth", "database migration"],\n'
        '    "simpler_alternative": "Skip custom OAuth; use a third-party provider"\n'
        '  }\n'
        '}\n'
        "```\n\n"
        "Be blunt. Be specific. Be helpful. Your goal is fewer, better decisions.\n"
    )
    tools = [FileReadTool, GrepTool, GlobTool]

    def __init__(self, client: anthropic.AsyncAnthropic | None = None) -> None:
        super().__init__()
        self.client = client or anthropic.AsyncAnthropic()
        self._executors = {**FILE_EXEC, **SEARCH_EXEC}

    @staticmethod
    def detect_scope_creep(text: str) -> bool:
        """Check if text contains scope expansion signals."""
        lower = text.lower()
        return any(signal in lower for signal in SCOPE_CREEP_SIGNALS)

    async def handle(self, message: Message, context: ContextStore) -> Result:
        payload = message.payload
        task = payload.get("task", payload.get("spec", ""))
        trigger = payload.get("trigger", "manual")  # manual | auto | scope_creep

        user_message = (
            f"## Task to Review\n{task}\n\n"
            f"Trigger: {trigger}\n"
        )

        # Add context about what's already been done this session.
        task_history = context.get("task_history", [])
        if task_history:
            user_message += f"\n## Session History\n{len(task_history)} tasks completed so far.\n"

        decisions = context.get("decisions", [])
        if decisions:
            user_message += f"\n## Previous Decisions\n{decisions}\n"

        # If this was triggered by scope creep detection, flag it.
        if trigger == "scope_creep":
            user_message += (
                "\n## ALERT: Scope Creep Detected\n"
                "This request came in mid-session and may be expanding scope. "
                "Be extra critical. Is this essential or a nice-to-have?\n"
            )

        user_message += (
            "\nExplore the codebase to understand the impact, "
            "then produce your challenge report as JSON.\n"
        )

        messages = [{"role": "user", "content": user_message}]

        for _ in range(8):
            response = await self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=self.system_prompt,
                tools=self.get_anthropic_tools(),
                messages=messages,
            )

            text_parts = []
            tool_calls = []
            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_calls.append(block)

            if not tool_calls:
                break

            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for tc in tool_calls:
                executor = self._executors.get(tc.name)
                if executor:
                    result = await executor(**tc.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tc.id,
                        "content": str(result),
                    })
                else:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tc.id,
                        "content": f"Unknown tool: {tc.name}",
                        "is_error": True,
                    })
            messages.append({"role": "user", "content": tool_results})

        challenge_text = "\n".join(text_parts) if text_parts else '{"verdict": "approve"}'
        context.agent_set(self.role.value, "last_challenge", challenge_text)

        # Determine status based on verdict.
        status = "success"
        if '"challenge"' in challenge_text or '"reject"' in challenge_text:
            status = "challenge"

        return Result(
            status=status,
            data={"challenge_report": challenge_text, "trigger": trigger},
        )
