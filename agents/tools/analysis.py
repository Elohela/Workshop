"""Analysis tools for the Reviewer agent."""

from __future__ import annotations

from typing import Any

from agents.agents.base import ToolDef
from .shell import execute_shell

LintTool = ToolDef(
    name="lint",
    description="Run a linter on the specified files or directory. Returns lint warnings and errors.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File or directory to lint"},
            "linter": {
                "type": "string",
                "enum": ["ruff", "eslint", "pylint", "flake8"],
                "description": "Which linter to use",
                "default": "ruff",
            },
        },
        "required": ["path"],
    },
)

TestRunnerTool = ToolDef(
    name="run_tests",
    description="Run the test suite. Returns test results with pass/fail counts and failure details.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Test file or directory"},
            "runner": {
                "type": "string",
                "enum": ["pytest", "jest", "mocha"],
                "default": "pytest",
            },
            "filter": {"type": "string", "description": "Test name filter pattern"},
        },
        "required": ["path"],
    },
)

SecurityScanTool = ToolDef(
    name="security_scan",
    description="Run a security scan on the codebase. Checks for common vulnerabilities (OWASP Top 10).",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory to scan"},
            "checks": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific checks to run, e.g. ['sql_injection', 'xss', 'secrets']",
            },
        },
        "required": ["path"],
    },
)


LINTER_COMMANDS = {
    "ruff": "ruff check {path}",
    "eslint": "npx eslint {path}",
    "pylint": "pylint {path}",
    "flake8": "flake8 {path}",
}

TEST_COMMANDS = {
    "pytest": "python -m pytest {path} -v {filter_flag}",
    "jest": "npx jest {path} {filter_flag}",
    "mocha": "npx mocha {path} {filter_flag}",
}


async def execute_lint(path: str, linter: str = "ruff") -> dict[str, Any]:
    """Run a linter and return results."""
    cmd = LINTER_COMMANDS.get(linter, LINTER_COMMANDS["ruff"]).format(path=path)
    return await execute_shell(cmd)


async def execute_tests(
    path: str, runner: str = "pytest", filter: str | None = None
) -> dict[str, Any]:
    """Run tests and return results."""
    filter_flag = f"-k '{filter}'" if filter and runner == "pytest" else ""
    if filter and runner == "jest":
        filter_flag = f"--testNamePattern='{filter}'"
    cmd = TEST_COMMANDS.get(runner, TEST_COMMANDS["pytest"]).format(
        path=path, filter_flag=filter_flag
    )
    return await execute_shell(cmd)


async def execute_security_scan(
    path: str, checks: list[str] | None = None
) -> dict[str, Any]:
    """Run a security scan. Uses bandit for Python by default."""
    cmd = f"bandit -r {path} -f json"
    if checks and "secrets" in checks:
        cmd += " && git secrets --scan"
    return await execute_shell(cmd)


TOOL_EXECUTORS = {
    "lint": execute_lint,
    "run_tests": execute_tests,
    "security_scan": execute_security_scan,
}
