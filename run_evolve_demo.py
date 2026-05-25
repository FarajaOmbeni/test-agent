#!/usr/bin/env python3
"""Interactive TestBot chat with mind.evolve() capability.

Usage:
    cd dr/test-agent
    python run_evolve_demo.py

Commands:
    /tools      — list available tools
    /evolve     — show pending evolutions status
    /revert     — revert last evolution
    /quit       — exit
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# ── Path setup ──────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
_NODEAI_ROOT = _HERE.parent / "nodeai"
_SRC = _HERE / "src"

sys.path.insert(0, str(_NODEAI_ROOT))
sys.path.insert(0, str(_SRC))

os.environ.setdefault(
    "DEFAULT_PLUGIN_PATHS",
    json.dumps(["nodeai_plugins"]),
)

# Set working directory to test-agent root so data/ is created here
os.chdir(str(_HERE))

# Load .env (only from this directory, not parent)
from dotenv import load_dotenv
load_dotenv(_HERE / ".env", override=True)

# ── Import and register ────────────────────────────────────────────────
from nodeai.api import Node, Mind, TextThought

# Side-effect import: registers @brain, @tool, @storage for TestBot
import agents.TestBot  # noqa: F401

# Register the self_evolve pipeline agents (needed by mind.evolve())
import nodeai_agents.self_evolve.wish_to_tests  # noqa: F401
import nodeai_agents.self_evolve.plan_writer  # noqa: F401
import nodeai_agents.self_evolve.plan_auditor  # noqa: F401
import nodeai_agents.self_evolve.code_writer  # noqa: F401
import nodeai_agents.self_evolve.integration_tester  # noqa: F401
import nodeai_agents.self_evolve.orchestrator  # noqa: F401


# ── Interactive loop ───────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  TestBot — Interactive Chat")
    print("  (with mind.evolve() self-evolution)")
    print("=" * 60)
    print()
    print("  Commands: /tools /evolve /revert /quit")
    print()

    # Start node
    node = Node(auto_start=True)
    mind = node.get_mind("TestBot", "test_1")

    tools = [t.name for t in mind.tools.list_public_tools()]
    print(f"  Tools: {tools}")
    print()
    print("-" * 60)

    while True:
        try:
            user_input = input("\nyou> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye!")
            break

        if not user_input:
            continue

        # Handle slash commands
        if user_input == "/quit":
            print("Goodbye!")
            break

        elif user_input == "/tools":
            tools = [t.name for t in mind.tools.list_public_tools()]
            print(f"  Tools: {tools}")
            continue

        elif user_input == "/evolve":
            pending = mind.unbox("pending_evolutions", [])
            if not pending:
                print("  No pending evolutions.")
            else:
                for e in pending:
                    print(f"  [{e.get('status', '?')}] {e.get('evo_id', '?')}: {e.get('query', '?')}")
            continue

        elif user_input == "/revert":
            result = mind.revert_last_evolution()
            print(f"  Revert: {result.status} (evo_id={result.evo_id})")
            tools = [t.name for t in mind.tools.list_public_tools()]
            print(f"  Tools now: {tools}")
            continue

        elif user_input.startswith("/"):
            print(f"  Unknown command: {user_input}")
            continue

        # Send message to TestBot
        thought = TextThought(user_input, role="user")
        response = mind.think(thought)

        content = getattr(response, "content", str(response))
        print(f"\nTestBot> {content}")

    # Cleanup
    node.shutdown(block=True)


if __name__ == "__main__":
    main()
