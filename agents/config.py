"""Agent registry and configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agents.agents.base import AgentRole


@dataclass
class AgentConfig:
    """Configuration for a single agent."""

    role: AgentRole
    enabled: bool = True
    model: str = "claude-sonnet-4-6"
    max_iterations: int = 10
    timeout_ms: int = 60_000
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestratorConfig:
    """Top-level configuration for the multi-agent system."""

    # Model used by the orchestrator for routing decisions.
    router_model: str = "claude-sonnet-4-6"

    # Whether the advisor acts as a mandatory pre-build gate.
    advisor_gate_enabled: bool = True

    # Whether to run visual_designer in parallel with builder for UI tasks.
    parallel_design: bool = True

    # Max number of build -> review iterations before giving up.
    max_review_loops: int = 3

    # Per-agent overrides.
    agents: dict[str, AgentConfig] = field(default_factory=lambda: {
        "research": AgentConfig(role=AgentRole.RESEARCH),
        "builder": AgentConfig(role=AgentRole.BUILDER, max_iterations=15),
        "reviewer": AgentConfig(role=AgentRole.REVIEWER),
        "planner": AgentConfig(role=AgentRole.PLANNER),
        "advisor": AgentConfig(role=AgentRole.ADVISOR, max_iterations=8),
        "visual_designer": AgentConfig(
            role=AgentRole.VISUAL_DESIGNER,
            max_iterations=12,
        ),
    })
