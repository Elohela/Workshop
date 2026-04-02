"""Builder Agent — code generation, file creation, and builds."""

from __future__ import annotations

import anthropic

from agents.agents.base import Agent, AgentRole, Result
from agents.bus.message import Message
from agents.context.store import ContextStore
from agents.tools.files import FileReadTool, FileWriteTool, TOOL_EXECUTORS as FILE_EXEC
from agents.tools.shell import ShellTool, TOOL_EXECUTORS as SHELL_EXEC


class BuilderAgent(Agent):
    role = AgentRole.BUILDER
    description = "Generates code, creates files, and runs builds."
    system_prompt = (
        "You are a Builder Agent. You write code and ship working software.\n\n"
        "Guidelines:\n"
        "- Read existing code before modifying it. Understand context first.\n"
        "- Write minimal, correct code. No speculative abstractions.\n"
        "- Don't add features beyond what was requested.\n"
        "- Run builds/tests after making changes to verify they work.\n"
        "- Output file diffs and build results in structured format.\n"
        "- If a task is ambiguous, state your assumptions explicitly.\n"
    )
    tools = [FileReadTool, FileWriteTool, ShellTool]

    def __init__(self, client: anthropic.AsyncAnthropic | None = None) -> None:
        super().__init__()
        self.client = client or anthropic.AsyncAnthropic()
        self._executors = {**FILE_EXEC, **SHELL_EXEC}

    async def handle(self, message: Message, context: ContextStore) -> Result:
        payload = message.payload
        action = payload.get("action", "build")
        spec = payload.get("spec", "")

        user_message = f"Action: {action}\nSpecification:\n{spec}\n"

        # Include any research findings from context.
        research = context.agent_data("research")
        if research.get("last_findings"):
            user_message += f"\nResearch findings available: {len(research['last_findings'])} items\n"

        # Include design decisions if Visual Designer has run.
        design = context.agent_data("visual_designer")
        if design.get("last_decisions"):
            user_message += f"\nDesign decisions to follow:\n{design['last_decisions']}\n"

        messages = [{"role": "user", "content": user_message}]
        files_changed: list[str] = []

        for _ in range(15):  # Builder may need more iterations for complex tasks.
            response = await self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=8192,
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
                    if tc.name == "file_write":
                        files_changed.append(tc.input.get("path", "unknown"))
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

        context.agent_set(self.role.value, "files_changed", files_changed)
        summary = "\n".join(text_parts) if text_parts else "Build completed."

        return Result(
            status="success",
            data={"summary": summary, "files_changed": files_changed},
        )
