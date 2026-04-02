"""Base agent interface and shared types."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from agents.bus.message import Message
from agents.context.store import ContextStore


class AgentRole(str, Enum):
    ORCHESTRATOR = "orchestrator"
    RESEARCH = "research"
    BUILDER = "builder"
    REVIEWER = "reviewer"
    PLANNER = "planner"
    ADVISOR = "advisor"
    VISUAL_DESIGNER = "visual_designer"


class AgentStatus(str, Enum):
    IDLE = "idle"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Result:
    """Structured result returned by every agent."""

    status: str  # "success" | "error" | "challenge" | "needs_input"
    data: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == "success"


@dataclass
class ToolDef:
    """Definition of a tool an agent can use."""

    name: str
    description: str
    parameters: dict[str, Any]

    def to_anthropic_tool(self) -> dict[str, Any]:
        """Convert to Anthropic API tool format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters,
        }


class Agent(abc.ABC):
    """Base class for all agents in the system."""

    role: AgentRole
    description: str
    system_prompt: str
    tools: list[ToolDef]

    def __init__(self) -> None:
        self.status = AgentStatus.IDLE

    @abc.abstractmethod
    async def handle(self, message: Message, context: ContextStore) -> Result:
        """Process a task message and return a result.

        Args:
            message: The incoming task message from the orchestrator.
            context: Shared context store for reading session state.

        Returns:
            A structured Result with the agent's output.
        """
        ...

    async def run(self, message: Message, context: ContextStore) -> Result:
        """Execute the agent lifecycle: assign -> run -> complete/fail."""
        self.status = AgentStatus.ASSIGNED
        try:
            self.status = AgentStatus.RUNNING
            result = await self.handle(message, context)
            self.status = AgentStatus.COMPLETED
            return result
        except Exception as exc:
            self.status = AgentStatus.FAILED
            return Result(
                status="error",
                errors=[str(exc)],
                metadata={"agent": self.role.value},
            )

    def get_anthropic_tools(self) -> list[dict[str, Any]]:
        """Return tools in Anthropic API format."""
        return [t.to_anthropic_tool() for t in self.tools]
