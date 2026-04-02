"""Shell execution tool for Builder and Reviewer agents."""

from __future__ import annotations

import asyncio
from typing import Any

from agents.agents.base import ToolDef

ShellTool = ToolDef(
    name="shell_exec",
    description="Execute a shell command and return stdout, stderr, and exit code. Use for builds, tests, and system commands.",
    parameters={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "The shell command to execute"},
            "timeout_seconds": {"type": "integer", "default": 60, "description": "Max execution time in seconds"},
            "working_dir": {"type": "string", "description": "Working directory for the command"},
        },
        "required": ["command"],
    },
)


async def execute_shell(
    command: str, timeout_seconds: int = 60, working_dir: str | None = None
) -> dict[str, Any]:
    """Run a shell command asynchronously."""
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_dir,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout_seconds
        )
        return {
            "command": command,
            "exit_code": proc.returncode,
            "stdout": stdout.decode(errors="replace")[-5000:],  # Cap output size
            "stderr": stderr.decode(errors="replace")[-2000:],
        }
    except asyncio.TimeoutError:
        proc.kill()
        return {"command": command, "error": f"Timed out after {timeout_seconds}s"}
    except OSError as exc:
        return {"command": command, "error": str(exc)}


TOOL_EXECUTORS = {
    "shell_exec": execute_shell,
}
