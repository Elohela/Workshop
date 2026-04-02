"""Session management for multi-agent conversations."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .store import ContextStore


@dataclass
class TaskRecord:
    """Record of a completed subtask."""

    agent: str
    action: str
    status: str
    result_summary: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class Session:
    """Manages state for a single user session.

    Wraps a ContextStore and adds session-level bookkeeping:
    task history, artifacts, and decision log.
    """

    def __init__(self, session_id: str | None = None) -> None:
        self.id = session_id or f"session_{uuid.uuid4().hex[:8]}"
        self.context = ContextStore()
        self.task_history: list[TaskRecord] = []
        self.artifacts: dict[str, Any] = {}
        self.decisions: list[dict[str, str]] = []
        self.created_at = datetime.now(timezone.utc)

        self.context.set_shared("session_id", self.id)

    def record_task(self, agent: str, action: str, status: str, summary: str) -> None:
        """Log a completed subtask."""
        record = TaskRecord(
            agent=agent, action=action, status=status, result_summary=summary
        )
        self.task_history.append(record)
        self.context.set_shared(
            "task_history",
            [
                {"agent": t.agent, "action": t.action, "status": t.status}
                for t in self.task_history
            ],
        )

    def record_decision(self, question: str, answer: str, rationale: str = "") -> None:
        """Log a decision made during the session."""
        self.decisions.append(
            {"question": question, "answer": answer, "rationale": rationale}
        )
        self.context.set_shared("decisions", self.decisions)

    def store_artifact(self, name: str, content: Any) -> None:
        """Save a named artifact (file, CSS, report, etc.)."""
        self.artifacts[name] = content
        self.context.set_shared("artifacts", list(self.artifacts.keys()))

    def summary(self) -> dict[str, Any]:
        """Return a session summary for debugging or display."""
        return {
            "session_id": self.id,
            "created_at": self.created_at.isoformat(),
            "tasks_completed": len(self.task_history),
            "artifacts": list(self.artifacts.keys()),
            "decisions": len(self.decisions),
        }
