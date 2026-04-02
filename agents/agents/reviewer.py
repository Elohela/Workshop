"""Reviewer Agent — code quality, testing, and security analysis."""

from __future__ import annotations

import anthropic

from agents.agents.base import Agent, AgentRole, Result
from agents.bus.message import Message
from agents.context.store import ContextStore
from agents.tools.files import FileReadTool, TOOL_EXECUTORS as FILE_EXEC
from agents.tools.shell import ShellTool, TOOL_EXECUTORS as SHELL_EXEC
from agents.tools.analysis import (
    LintTool, TestRunnerTool, SecurityScanTool,
    TOOL_EXECUTORS as ANALYSIS_EXEC,
)


class ReviewerAgent(Agent):
    role = AgentRole.REVIEWER
    description = "Analyzes code quality, runs tests, and checks for security issues."
    system_prompt = (
        "You are a Reviewer Agent. You ensure code quality and correctness.\n\n"
        "Guidelines:\n"
        "- Run linters and tests before giving opinions.\n"
        "- Rank findings by severity: critical > high > medium > low.\n"
        "- Focus on bugs and security issues, not style preferences.\n"
        "- If tests pass and no critical issues, say so clearly.\n"
        "- Always check for OWASP Top 10 vulnerabilities in web code.\n"
        "- Be specific: cite file paths, line numbers, and the exact issue.\n"
    )
    tools = [FileReadTool, ShellTool, LintTool, TestRunnerTool, SecurityScanTool]

    def __init__(self, client: anthropic.AsyncAnthropic | None = None) -> None:
        super().__init__()
        self.client = client or anthropic.AsyncAnthropic()
        self._executors = {**FILE_EXEC, **SHELL_EXEC, **ANALYSIS_EXEC}

    async def handle(self, message: Message, context: ContextStore) -> Result:
        payload = message.payload
        action = payload.get("action", "review")
        target = payload.get("target", ".")

        # Check what the builder changed so we know what to review.
        files_changed = context.agent_get("builder", "files_changed", [])

        user_message = f"Action: {action}\nTarget: {target}\n"
        if files_changed:
            user_message += f"Files recently changed by Builder: {files_changed}\n"
        user_message += "Run linters and tests, then provide a severity-ranked review.\n"

        messages = [{"role": "user", "content": user_message}]
        findings: list[dict] = []

        for _ in range(10):
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
                    findings.append({"tool": tc.name, "result": result})
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

        context.agent_set(self.role.value, "last_review", findings)
        summary = "\n".join(text_parts) if text_parts else "Review completed."

        return Result(
            status="success",
            data={"summary": summary, "findings": findings, "target": target},
        )
