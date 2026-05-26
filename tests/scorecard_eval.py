#!/usr/bin/env python3
"""Batch eval — run TestBot conversation specs and push results to Scorecard.

Wraps the existing CONVERSATIONS from test_integration__get_today_date.py,
runs each against a live TestBot Mind, and records results on the Scorecard
dashboard via run_and_evaluate().

Usage:
    cd test-agent
    python tests/scorecard_eval.py

Requires SCORECARD_API_KEY and SCORECARD_PROJECT_ID in .env (or environment).
"""
from __future__ import annotations

import json
import os
import sys
import textwrap
from pathlib import Path

# ── Path setup ─────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
_SRC = _ROOT / "src"

if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

os.chdir(str(_ROOT))
os.environ.setdefault("DEFAULT_PLUGIN_PATHS", json.dumps(["nodeai_plugins"]))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env", override=True)

# ── Imports (after path setup) ─────────────────────────────────────────
from scorecard_ai import Scorecard
from scorecard_ai.lib import run_and_evaluate

from nodeai.api import Node, TextThought

import agents.TestBot  # noqa: F401
from test_integration__get_today_date import CONVERSATIONS

# ── Boot TestBot ───────────────────────────────────────────────────────
_node = Node(auto_start=True)
_mind = _node.get_mind("TestBot", "scorecard_eval")


# ── Transform conversations into Scorecard testcases ───────────────────
def _build_testcases() -> list[dict]:
    testcases = []
    for conv in CONVERSATIONS:
        testcases.append(
            {
                "inputs": {
                    "id": conv["id"],
                    "description": conv["description"],
                    "messages": json.dumps(conv["messages"]),
                },
                "expected": {
                    "expected_behavior": conv["expected_behavior"],
                    "must_contain": conv.get("must_contain", ""),
                    "must_use_tool": conv.get("must_use_tool", ""),
                    "must_not_use_tool": conv.get("must_not_use_tool", ""),
                },
            }
        )
    return testcases


# ── System under test ──────────────────────────────────────────────────
def _extract_tool_names(response) -> list[str]:
    calls = getattr(response, "tool_calls", None) or []
    names: list[str] = []
    for tc in calls:
        name = getattr(tc, "tool", None) or getattr(tc, "name", None)
        if name:
            names.append(name)
    return names


def run_testbot(inputs: dict, _system_version=None) -> dict:
    """Send the conversation to TestBot and return outputs for Scorecard."""
    messages = json.loads(inputs["messages"])
    user_message = messages[-1]["content"]
    history = messages[:-1]

    if history and hasattr(_mind, "think_with_history"):
        response = _mind.think_with_history(user_message, history=history)
    else:
        thought = TextThought(user_message, role="user")
        response = _mind.think(thought)

    reply_text = getattr(response, "content", str(response))
    tool_names = _extract_tool_names(response)

    return {
        "response": reply_text,
        "tools_called": json.dumps(tool_names),
    }


# ── Main ───────────────────────────────────────────────────────────────
def main():
    project_id = os.environ.get("SCORECARD_PROJECT_ID")
    if not project_id:
        print("Error: SCORECARD_PROJECT_ID not set in .env or environment.")
        sys.exit(1)

    api_key = os.environ.get("SCORECARD_API_KEY")
    if not api_key:
        print("Error: SCORECARD_API_KEY not set in .env or environment.")
        sys.exit(1)

    scorecard = Scorecard(api_key=api_key)

    # Create metrics for this project
    tool_correctness = scorecard.metrics.create(
        project_id=project_id,
        name="Tool Correctness",
        description="Did the agent call the correct tool (or avoid the wrong one)?",
        eval_type="ai",
        output_type="boolean",
        prompt_template=textwrap.dedent("""\
            You are evaluating whether an AI agent called the correct tool.

            Expected behavior: {{expected.expected_behavior}}
            Must use tool: {{expected.must_use_tool}}
            Must NOT use tool: {{expected.must_not_use_tool}}

            Tools actually called: {{outputs.tools_called}}
            Agent response: {{outputs.response}}

            Did the agent use the correct tool(s) as specified? Answer true or false.

            {{ gradingInstructionsAndExamples }}"""),
    )

    response_quality = scorecard.metrics.create(
        project_id=project_id,
        name="Response Quality",
        description="How relevant and complete is the agent's response?",
        eval_type="ai",
        output_type="int",
        prompt_template=textwrap.dedent("""\
            You are evaluating the quality of an AI agent's response.

            User request: {{inputs.description}}
            Expected behavior: {{expected.expected_behavior}}
            Must contain: {{expected.must_contain}}

            Agent response: {{outputs.response}}

            Rate the response quality on a scale of 1-5:
            1 = Completely wrong or refused when it should have answered
            2 = Partially relevant but missing key information
            3 = Acceptable but could be better
            4 = Good response meeting expectations
            5 = Excellent, complete, and well-formatted response

            {{ gradingInstructionsAndExamples }}"""),
    )

    testcases = _build_testcases()

    print(f"Running {len(testcases)} conversations against TestBot...")
    print(f"Metrics: {tool_correctness.name} (id={tool_correctness.id}), "
          f"{response_quality.name} (id={response_quality.id})")
    print()

    run = run_and_evaluate(
        client=scorecard,
        project_id=project_id,
        testcases=testcases,
        metric_ids=[tool_correctness.id, response_quality.id],
        system=run_testbot,
    )

    print()
    print(f'Results: {run["url"]}')

    # Cleanup
    _node.shutdown(block=True)


if __name__ == "__main__":
    main()
