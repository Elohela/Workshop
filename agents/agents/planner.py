"""Planner Agent — task decomposition and dependency analysis."""

from __future__ import annotations

import anthropic

from agents.agents.base import Agent, AgentRole, Result
from agents.bus.message import Message
from agents.context.store import ContextStore
from agents.tools.files import FileReadTool, TOOL_EXECUTORS as FILE_EXEC
from agents.tools.search import GrepTool, GlobTool, TOOL_EXECUTORS as SEARCH_EXEC


class PlannerAgent(Agent):
    role = AgentRole.PLANNER
    description = "Breaks down ambiguous or large tasks into ordered, actionable subtasks."
    system_prompt = (
        "You are a Planner Agent. You decompose complex requests into concrete steps.\n\n"
        "Guidelines:\n"
        "- Read the codebase first to understand what exists.\n"
        "- Break tasks into small, independently testable steps.\n"
        "- Identify dependencies between steps (what must happen first).\n"
        "- Flag steps that can run in parallel.\n"
        "- Each step must have clear acceptance criteria.\n"
        "- Output your plan as a structured JSON list, not prose.\n\n"
        "Output format:\n"
        '{"steps": [{"id": 1, "action": "...", "agent": "builder|research|reviewer", '
        '"depends_on": [], "parallel_with": [], "acceptance": "..."}]}\n'
    )
    tools = [FileReadTool, GrepTool, GlobTool]

    def __init__(self, client: anthropic.AsyncAnthropic | None = None) -> None:
        super().__init__()
        self.client = client or anthropic.AsyncAnthropic()
        self._executors = {**FILE_EXEC, **SEARCH_EXEC}

    async def handle(self, message: Message, context: ContextStore) -> Result:
        payload = message.payload
        task = payload.get("task", payload.get("spec", ""))

        user_message = (
            f"Task to plan:\n{task}\n\n"
            "Explore the codebase as needed, then produce a structured plan.\n"
        )

        # Pass along any advisor feedback if scope was challenged.
        advisor_data = context.agent_data("advisor")
        if advisor_data.get("last_challenge"):
            user_message += (
                f"\nThe Advisor challenged scope with these notes:\n"
                f"{advisor_data['last_challenge']}\n"
                "Incorporate the advisor's feedback into your plan.\n"
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

        plan_text = "\n".join(text_parts) if text_parts else "No plan produced."
        context.agent_set(self.role.value, "last_plan", plan_text)

        return Result(
            status="success",
            data={"plan": plan_text, "task": task},
        )
