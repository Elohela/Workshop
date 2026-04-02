"""Research Agent — information gathering and codebase exploration."""

from __future__ import annotations

import anthropic

from agents.agents.base import Agent, AgentRole, Result, ToolDef
from agents.bus.message import Message
from agents.context.store import ContextStore
from agents.tools.search import SearchTool, GrepTool, GlobTool, TOOL_EXECUTORS as SEARCH_EXEC
from agents.tools.files import FileReadTool, TOOL_EXECUTORS as FILE_EXEC


class ResearchAgent(Agent):
    role = AgentRole.RESEARCH
    description = "Gathers information by searching codebases, reading files, and querying the web."
    system_prompt = (
        "You are a Research Agent. Your job is to find information quickly and accurately.\n\n"
        "Guidelines:\n"
        "- Search broadly first, then narrow down.\n"
        "- Always cite which files/lines your findings come from.\n"
        "- Provide a confidence score (0.0-1.0) for your findings.\n"
        "- If you can't find what you need, say so clearly — don't guess.\n"
        "- Summarize findings in structured format, not prose.\n"
    )
    tools = [SearchTool, GrepTool, GlobTool, FileReadTool]

    def __init__(self, client: anthropic.AsyncAnthropic | None = None) -> None:
        super().__init__()
        self.client = client or anthropic.AsyncAnthropic()
        self._executors = {**SEARCH_EXEC, **FILE_EXEC}

    async def handle(self, message: Message, context: ContextStore) -> Result:
        payload = message.payload
        action = payload.get("action", "search")
        query = payload.get("query", "")

        # Build the conversation for the LLM.
        user_message = (
            f"Action: {action}\n"
            f"Query: {query}\n"
            f"Constraints: {payload.get('constraints', {})}\n"
        )

        # Add session context if available.
        task_history = context.get("task_history", [])
        if task_history:
            user_message += f"\nPrevious tasks in this session: {task_history}\n"

        messages = [{"role": "user", "content": user_message}]

        # Agentic tool-use loop.
        findings: list[dict] = []
        for _ in range(10):  # Max iterations to prevent runaway loops.
            response = await self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=self.system_prompt,
                tools=self.get_anthropic_tools(),
                messages=messages,
            )

            # Collect text blocks and tool calls.
            text_parts = []
            tool_calls = []
            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_calls.append(block)

            if not tool_calls:
                # No more tool calls — agent is done.
                break

            # Execute each tool call and feed results back.
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for tc in tool_calls:
                executor = self._executors.get(tc.name)
                if executor:
                    result = await executor(**tc.input)
                    findings.append({"tool": tc.name, "input": tc.input, "result": result})
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

        # Store findings in agent namespace.
        context.agent_set(self.role.value, "last_findings", findings)
        summary = "\n".join(text_parts) if text_parts else "No summary produced."

        return Result(
            status="success",
            data={"summary": summary, "findings": findings, "query": query},
            confidence=0.85 if findings else 0.3,
        )
