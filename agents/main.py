"""Entry point for the multi-agent system.

Usage:
    python -m agents.main "Your request here"
    python -m agents.main --interactive
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys

from agents.orchestrator import Orchestrator


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("agents")


async def run_once(orchestrator: Orchestrator, request: str) -> None:
    """Process a single request and print the result."""
    print(f"\n{'='*60}")
    print(f"Request: {request}")
    print(f"{'='*60}\n")

    result = await orchestrator.route(request)

    print(f"\n{'='*60}")
    print("Results:")
    print(f"{'='*60}")
    for agent_name, agent_result in result.get("results", {}).items():
        print(f"\n--- {agent_name} ---")
        summary = agent_result.get("summary", agent_result)
        if isinstance(summary, str) and len(summary) > 500:
            summary = summary[:500] + "..."
        print(summary)

    print(f"\nSession: {json.dumps(result.get('session', {}), indent=2)}")


async def run_interactive(orchestrator: Orchestrator) -> None:
    """Run an interactive REPL."""
    print("Multi-Agent System — Interactive Mode")
    print("Type 'quit' to exit, 'session' for session info.\n")

    while True:
        try:
            request = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not request:
            continue
        if request.lower() == "quit":
            print("Goodbye.")
            break
        if request.lower() == "session":
            print(json.dumps(orchestrator.session.summary(), indent=2))
            continue

        await run_once(orchestrator, request)


def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-Agent System")
    parser.add_argument("request", nargs="?", help="Single request to process")
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Run in interactive REPL mode"
    )
    parser.add_argument(
        "--gated", "-g", action="store_true",
        help="Use gated build pipeline (Advisor -> Plan -> Design+Build -> Review)",
    )
    args = parser.parse_args()

    orchestrator = Orchestrator()

    if args.interactive:
        asyncio.run(run_interactive(orchestrator))
    elif args.request:
        if args.gated:

            async def gated() -> None:
                results = await orchestrator.gated_build(args.request)
                for name, result in results.items():
                    print(f"\n--- {name} ---")
                    print(f"Status: {result.status}")
                    if result.data:
                        summary = result.data.get("summary", str(result.data))
                        print(summary[:500] if isinstance(summary, str) else summary)

            asyncio.run(gated())
        else:
            asyncio.run(run_once(orchestrator, args.request))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
