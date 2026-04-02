"""Shared context store for cross-agent state."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Namespace:
    """Isolated write-space for a single agent."""

    owner: str
    data: dict[str, Any] = field(default_factory=dict)


class ContextStore:
    """Key-value store shared across all agents.

    Rules:
    - Any agent can READ from any namespace.
    - Agents can only WRITE to their own namespace.
    - The orchestrator merges results into shared state.
    """

    def __init__(self) -> None:
        self._shared: dict[str, Any] = {}
        self._namespaces: dict[str, Namespace] = {}

    # --- Shared state (read/write by orchestrator only) ---

    def get(self, key: str, default: Any = None) -> Any:
        """Read from shared state."""
        return self._shared.get(key, default)

    def set_shared(self, key: str, value: Any) -> None:
        """Write to shared state (orchestrator use only)."""
        self._shared[key] = value

    # --- Namespaced state (per-agent isolation) ---

    def _ensure_namespace(self, agent: str) -> Namespace:
        if agent not in self._namespaces:
            self._namespaces[agent] = Namespace(owner=agent)
        return self._namespaces[agent]

    def agent_get(self, agent: str, key: str, default: Any = None) -> Any:
        """Read a value from any agent's namespace."""
        ns = self._namespaces.get(agent)
        if ns is None:
            return default
        return ns.data.get(key, default)

    def agent_set(self, agent: str, key: str, value: Any) -> None:
        """Write a value to an agent's own namespace."""
        ns = self._ensure_namespace(agent)
        ns.data[key] = value

    def agent_data(self, agent: str) -> dict[str, Any]:
        """Return a read-only copy of an agent's namespace."""
        ns = self._namespaces.get(agent)
        if ns is None:
            return {}
        return copy.deepcopy(ns.data)

    # --- Bulk operations ---

    def snapshot(self) -> dict[str, Any]:
        """Return a full snapshot of the store for debugging."""
        return {
            "shared": copy.deepcopy(self._shared),
            "namespaces": {
                name: copy.deepcopy(ns.data)
                for name, ns in self._namespaces.items()
            },
        }
