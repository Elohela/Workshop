"""Search tools for the Research agent."""

from __future__ import annotations

import asyncio
import glob as glob_mod
import os
import re
from dataclasses import dataclass
from typing import Any

from agents.agents.base import ToolDef


# --- Tool definitions (for LLM tool-use registration) ---

SearchTool = ToolDef(
    name="web_search",
    description="Search the web for information. Returns a list of results with titles, URLs, and snippets.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query"},
            "max_results": {"type": "integer", "default": 5},
        },
        "required": ["query"],
    },
)

GrepTool = ToolDef(
    name="grep",
    description="Search file contents for a regex pattern. Returns matching lines with file paths and line numbers.",
    parameters={
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Regex pattern to search for"},
            "path": {"type": "string", "description": "Directory to search in", "default": "."},
            "file_types": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Glob patterns for file types, e.g. ['*.py', '*.js']",
            },
        },
        "required": ["pattern"],
    },
)

GlobTool = ToolDef(
    name="glob",
    description="Find files matching a glob pattern. Returns a list of matching file paths.",
    parameters={
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Glob pattern, e.g. '**/*.py'"},
            "path": {"type": "string", "description": "Base directory", "default": "."},
        },
        "required": ["pattern"],
    },
)


# --- Tool implementations ---


async def execute_search(query: str, max_results: int = 5) -> dict[str, Any]:
    """Execute a web search. Placeholder — wire up a real search API."""
    # In production, call a search API here (e.g., Brave, Tavily, SerpAPI).
    return {
        "query": query,
        "results": [],
        "note": "Web search not configured. Wire up a search provider in tools/search.py.",
    }


async def execute_grep(
    pattern: str, path: str = ".", file_types: list[str] | None = None
) -> dict[str, Any]:
    """Search file contents for a regex pattern."""
    matches: list[dict[str, Any]] = []
    compiled = re.compile(pattern)
    search_root = os.path.abspath(path)

    for root, _dirs, files in os.walk(search_root):
        for filename in files:
            if file_types:
                if not any(filename.endswith(ft.lstrip("*")) for ft in file_types):
                    continue
            filepath = os.path.join(root, filename)
            try:
                with open(filepath, "r", errors="ignore") as f:
                    for lineno, line in enumerate(f, 1):
                        if compiled.search(line):
                            matches.append(
                                {"file": filepath, "line": lineno, "content": line.rstrip()}
                            )
            except (OSError, UnicodeDecodeError):
                continue

    return {"pattern": pattern, "matches": matches[:100]}


async def execute_glob(pattern: str, path: str = ".") -> dict[str, Any]:
    """Find files matching a glob pattern."""
    full_pattern = os.path.join(os.path.abspath(path), pattern)
    results = sorted(glob_mod.glob(full_pattern, recursive=True))
    return {"pattern": pattern, "files": results[:200]}


TOOL_EXECUTORS = {
    "web_search": execute_search,
    "grep": execute_grep,
    "glob": execute_glob,
}
