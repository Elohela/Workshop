"""In-process async message bus for agent communication."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any, Callable, Coroutine

from .message import Message

logger = logging.getLogger(__name__)

Listener = Callable[[Message], Coroutine[Any, Any, None]]


class MessageBus:
    """Async message bus that routes messages between agents.

    Agents subscribe to receive messages addressed to them.
    The bus handles delivery, timeouts, and dead-letter logging.
    """

    def __init__(self) -> None:
        self._listeners: dict[str, list[Listener]] = defaultdict(list)
        self._history: list[Message] = []
        self._pending: dict[str, asyncio.Future[Message]] = {}

    def subscribe(self, agent_name: str, listener: Listener) -> None:
        """Register a listener for messages addressed to an agent."""
        self._listeners[agent_name].append(listener)

    async def publish(self, message: Message) -> None:
        """Send a message to its target agent."""
        self._history.append(message)
        listeners = self._listeners.get(message.to_agent, [])
        if not listeners:
            logger.warning(f"No listeners for agent '{message.to_agent}', message {message.id} dropped")
            return
        for listener in listeners:
            await listener(message)

        # Resolve any pending request-reply futures.
        if message.parent_id and message.parent_id in self._pending:
            self._pending[message.parent_id].set_result(message)

    async def request(self, message: Message, timeout_ms: int | None = None) -> Message:
        """Send a message and wait for the reply.

        Returns the reply message. Raises asyncio.TimeoutError if no reply
        arrives within the timeout.
        """
        timeout = (timeout_ms or message.timeout_ms) / 1000.0
        future: asyncio.Future[Message] = asyncio.get_event_loop().create_future()
        self._pending[message.id] = future
        await self.publish(message)
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        finally:
            self._pending.pop(message.id, None)

    def get_history(self, limit: int = 50) -> list[Message]:
        """Return recent message history."""
        return self._history[-limit:]
