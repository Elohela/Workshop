"""Typed message protocol for inter-agent communication."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class MessageType(str, Enum):
    TASK = "task"
    RESULT = "result"
    PROGRESS = "progress"
    ERROR = "error"


class Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Message:
    """Structured message passed between agents."""

    from_agent: str
    to_agent: str
    type: MessageType
    payload: dict[str, Any]
    id: str = field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:12]}")
    parent_id: str | None = None
    context_ref: str | None = None
    priority: Priority = Priority.NORMAL
    timeout_ms: int = 30_000
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def reply(
        self,
        type: MessageType,
        payload: dict[str, Any],
        **kwargs: Any,
    ) -> Message:
        """Create a reply message back to the sender."""
        return Message(
            from_agent=self.to_agent,
            to_agent=self.from_agent,
            type=type,
            payload=payload,
            parent_id=self.id,
            context_ref=self.context_ref,
            **kwargs,
        )
