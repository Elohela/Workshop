"""File read/write tools for Builder and Research agents."""

from __future__ import annotations

import os
from typing import Any

from agents.agents.base import ToolDef

FileReadTool = ToolDef(
    name="file_read",
    description="Read the contents of a file. Returns the file content as a string with line numbers.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Absolute or relative path to the file"},
            "offset": {"type": "integer", "description": "Line number to start reading from (0-based)", "default": 0},
            "limit": {"type": "integer", "description": "Max number of lines to read", "default": 500},
        },
        "required": ["path"],
    },
)

FileWriteTool = ToolDef(
    name="file_write",
    description="Write content to a file. Creates the file if it doesn't exist. Overwrites if it does.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the file to write"},
            "content": {"type": "string", "description": "The content to write"},
        },
        "required": ["path", "content"],
    },
)


async def execute_file_read(
    path: str, offset: int = 0, limit: int = 500
) -> dict[str, Any]:
    """Read a file and return its contents with line numbers."""
    abs_path = os.path.abspath(path)
    if not os.path.isfile(abs_path):
        return {"error": f"File not found: {abs_path}"}

    with open(abs_path, "r", errors="replace") as f:
        lines = f.readlines()

    selected = lines[offset : offset + limit]
    numbered = [
        {"line": offset + i + 1, "content": line.rstrip()}
        for i, line in enumerate(selected)
    ]
    return {
        "path": abs_path,
        "total_lines": len(lines),
        "showing": f"{offset + 1}-{offset + len(selected)}",
        "lines": numbered,
    }


async def execute_file_write(path: str, content: str) -> dict[str, Any]:
    """Write content to a file."""
    abs_path = os.path.abspath(path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "w") as f:
        f.write(content)
    return {"path": abs_path, "bytes_written": len(content.encode())}


TOOL_EXECUTORS = {
    "file_read": execute_file_read,
    "file_write": execute_file_write,
}
