"""Orchestrator — central router that decomposes tasks and delegates to agents.

The orchestrator is the only component that talks to the user. Specialist agents
communicate through the orchestrator via the message bus.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import anthropic

from agents.agents.base import Agent, AgentRole, Result
from agents.agents.research import ResearchAgent
from agents.agents.builder import BuilderAgent
from agents.agents.reviewer import ReviewerAgent
from agents.agents.planner import PlannerAgent
from agents.agents.advisor import AdvisorAgent
from agents.agents.visual_designer import VisualDesignerAgent
from agents.bus.message import Message, MessageType, Priority
from agents.bus.queue import MessageBus
from agents.context.session import Session

logger = logging.getLogger(__name__)


class Orchestrator:
    """Central router that receives user requests and delegates to specialist agents.

    Execution patterns:
    - Sequential pipeline: Research -> Plan -> Build -> Review
    - Parallel fan-out: Multiple agents run concurrently
    - Gated pipeline: Advisor challenges scope before Build + Design run in parallel
    - Iterative loop: Build -> Review -> fix -> Review until clean
    """

    SYSTEM_PROMPT = (
        "You are the Orchestrator of a multi-agent system. Your job is to:\n"
        "1. Understand the user's intent.\n"
        "2. Decide which agents to invoke and in what order.\n"
        "3. Aggregate results and respond to the user.\n\n"
        "Available agents:\n"
        "- research: Search codebases, read files, gather information\n"
        "- builder: Generate code, create files, run builds\n"
        "- reviewer: Code quality, linting, testing, security\n"
        "- planner: Break complex tasks into ordered steps\n"
        "- advisor: Challenge scope, question assumptions, force tradeoffs\n"
        "- visual_designer: UI aesthetics, CSS, layout, color, typography\n\n"
        "Routing rules:\n"
        "- For ANY feature request: run advisor FIRST as a scope gate.\n"
        "- For UI/visual work: run visual_designer in PARALLEL with builder.\n"
        "- For questions/research: route to research agent.\n"
        "- For code review: route to reviewer.\n"
        "- For complex/ambiguous tasks: route to planner first.\n"
        "- After building: always run reviewer.\n\n"
        "Respond with a JSON routing plan:\n"
        '{"steps": [{"agent": "agent_name", "action": "...", "parallel_with": [], "payload": {...}}]}\n'
    )

    def __init__(self, client: anthropic.AsyncAnthropic | None = None) -> None:
        self.client = client or anthropic.AsyncAnthropic()
        self.bus = MessageBus()
        self.session = Session()

        # Initialize all agents.
        self.agents: dict[str, Agent] = {
            "research": ResearchAgent(client=self.client),
            "builder": BuilderAgent(client=self.client),
            "reviewer": ReviewerAgent(client=self.client),
            "planner": PlannerAgent(client=self.client),
            "advisor": AdvisorAgent(client=self.client),
            "visual_designer": VisualDesignerAgent(client=self.client),
        }

        # Register agents on the message bus.
        for name, agent in self.agents.items():
            self.bus.subscribe(name, self._make_handler(agent))

    def _make_handler(self, agent: Agent):
        """Create a message handler that runs an agent and publishes the result."""
        async def handler(message: Message) -> None:
            result = await agent.run(message, self.session.context)
            reply = message.reply(
                type=MessageType.RESULT,
                payload={"result": result.data, "status": result.status},
            )
            await self.bus.publish(reply)
        return handler

    async def route(self, user_input: str) -> dict[str, Any]:
        """Process a user request end-to-end.

        1. Classify intent via LLM.
        2. Execute the routing plan (sequential/parallel/gated).
        3. Return aggregated results.
        """
        # Check for scope creep signals.
        from agents.agents.advisor import AdvisorAgent
        scope_creep = AdvisorAgent.detect_scope_creep(user_input)

        # Ask the LLM to produce a routing plan.
        routing_prompt = f"User request: {user_input}\n"
        if scope_creep:
            routing_prompt += "\n⚠️ Scope creep detected. Route to advisor first.\n"

        response = await self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=self.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": routing_prompt}],
        )

        routing_text = ""
        for block in response.content:
            if block.type == "text":
                routing_text += block.text

        # Execute the plan.
        plan = self._parse_routing_plan(routing_text)
        results = await self._execute_plan(plan, user_input)

        # Record in session history.
        for agent_name, result in results.items():
            self.session.record_task(
                agent=agent_name,
                action="routed",
                status=result.status,
                summary=str(result.data.get("summary", ""))[:200],
            )

        return {
            "routing_plan": routing_text,
            "results": {k: v.data for k, v in results.items()},
            "session": self.session.summary(),
        }

    def _parse_routing_plan(self, text: str) -> list[dict[str, Any]]:
        """Extract structured steps from the LLM's routing response.

        Falls back to a simple single-agent dispatch if parsing fails.
        """
        import json

        # Try to extract JSON from the response.
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            parsed = json.loads(text[start:end])
            return parsed.get("steps", [])
        except (ValueError, json.JSONDecodeError):
            # Fallback: try to identify the agent from keywords.
            for agent_name in self.agents:
                if agent_name in text.lower():
                    return [{"agent": agent_name, "action": "handle", "payload": {}}]
            # Default to planner for ambiguous requests.
            return [{"agent": "planner", "action": "plan", "payload": {}}]

    async def _execute_plan(
        self, steps: list[dict[str, Any]], user_input: str
    ) -> dict[str, Result]:
        """Execute routing steps, handling sequential and parallel execution."""
        results: dict[str, Result] = {}
        i = 0

        while i < len(steps):
            step = steps[i]
            agent_name = step.get("agent", "planner")
            parallel_with = step.get("parallel_with", [])

            if parallel_with:
                # Run this step and its parallel companions concurrently.
                parallel_agents = [agent_name] + parallel_with
                tasks = []
                for name in parallel_agents:
                    agent = self.agents.get(name)
                    if agent:
                        msg = Message(
                            from_agent="orchestrator",
                            to_agent=name,
                            type=MessageType.TASK,
                            payload={
                                "action": step.get("action", "handle"),
                                "task": user_input,
                                "spec": user_input,
                                **step.get("payload", {}),
                            },
                            context_ref=self.session.id,
                        )
                        tasks.append(self._run_agent(name, agent, msg))
                parallel_results = await asyncio.gather(*tasks, return_exceptions=True)
                for name, result in zip(parallel_agents, parallel_results):
                    if isinstance(result, Exception):
                        results[name] = Result(status="error", errors=[str(result)])
                    else:
                        results[name] = result
                i += 1
            else:
                # Sequential execution.
                agent = self.agents.get(agent_name)
                if agent:
                    msg = Message(
                        from_agent="orchestrator",
                        to_agent=agent_name,
                        type=MessageType.TASK,
                        payload={
                            "action": step.get("action", "handle"),
                            "task": user_input,
                            "spec": user_input,
                            **step.get("payload", {}),
                        },
                        context_ref=self.session.id,
                    )
                    result = await self._run_agent(agent_name, agent, msg)
                    results[agent_name] = result

                    # If the advisor challenged, surface it and stop the pipeline.
                    if agent_name == "advisor" and result.status == "challenge":
                        logger.info("Advisor challenged scope — halting pipeline.")
                        break
                i += 1

        return results

    async def _run_agent(self, name: str, agent: Agent, message: Message) -> Result:
        """Run a single agent with error handling."""
        try:
            return await agent.run(message, self.session.context)
        except Exception as exc:
            logger.exception(f"Agent '{name}' failed")
            return Result(status="error", errors=[str(exc)])

    # --- Convenience methods for common patterns ---

    async def research(self, query: str) -> Result:
        """Shortcut: send a query directly to the Research agent."""
        msg = Message(
            from_agent="orchestrator",
            to_agent="research",
            type=MessageType.TASK,
            payload={"action": "search", "query": query},
            context_ref=self.session.id,
        )
        return await self._run_agent("research", self.agents["research"], msg)

    async def build(self, spec: str) -> Result:
        """Shortcut: send a spec directly to the Builder agent."""
        msg = Message(
            from_agent="orchestrator",
            to_agent="builder",
            type=MessageType.TASK,
            payload={"action": "build", "spec": spec},
            context_ref=self.session.id,
        )
        return await self._run_agent("builder", self.agents["builder"], msg)

    async def review(self, target: str = ".") -> Result:
        """Shortcut: run the Reviewer on a target path."""
        msg = Message(
            from_agent="orchestrator",
            to_agent="reviewer",
            type=MessageType.TASK,
            payload={"action": "review", "target": target},
            context_ref=self.session.id,
        )
        return await self._run_agent("reviewer", self.agents["reviewer"], msg)

    async def challenge(self, task: str) -> Result:
        """Shortcut: run the Advisor on a task."""
        msg = Message(
            from_agent="orchestrator",
            to_agent="advisor",
            type=MessageType.TASK,
            payload={"action": "challenge", "task": task, "trigger": "manual"},
            context_ref=self.session.id,
        )
        return await self._run_agent("advisor", self.agents["advisor"], msg)

    async def design(self, spec: str) -> Result:
        """Shortcut: run the Visual Designer."""
        msg = Message(
            from_agent="orchestrator",
            to_agent="visual_designer",
            type=MessageType.TASK,
            payload={"action": "design", "spec": spec},
            context_ref=self.session.id,
        )
        return await self._run_agent("visual_designer", self.agents["visual_designer"], msg)

    async def gated_build(self, spec: str) -> dict[str, Result]:
        """Run the full gated pipeline: Advisor -> Plan -> (Design + Build) -> Review."""
        results: dict[str, Result] = {}

        # 1. Advisor gate.
        advisor_result = await self.challenge(spec)
        results["advisor"] = advisor_result
        if advisor_result.status == "challenge":
            return results  # Stop — scope needs resolution.

        # 2. Plan.
        plan_msg = Message(
            from_agent="orchestrator",
            to_agent="planner",
            type=MessageType.TASK,
            payload={"action": "plan", "task": spec},
            context_ref=self.session.id,
        )
        results["planner"] = await self._run_agent("planner", self.agents["planner"], plan_msg)

        # 3. Design + Build in parallel.
        design_task = self._run_agent(
            "visual_designer",
            self.agents["visual_designer"],
            Message(
                from_agent="orchestrator",
                to_agent="visual_designer",
                type=MessageType.TASK,
                payload={"action": "design", "spec": spec},
                context_ref=self.session.id,
            ),
        )
        build_task = self._run_agent(
            "builder",
            self.agents["builder"],
            Message(
                from_agent="orchestrator",
                to_agent="builder",
                type=MessageType.TASK,
                payload={"action": "build", "spec": spec},
                context_ref=self.session.id,
            ),
        )
        design_result, build_result = await asyncio.gather(design_task, build_task)
        results["visual_designer"] = design_result
        results["builder"] = build_result

        # 4. Review.
        results["reviewer"] = await self.review()

        return results
