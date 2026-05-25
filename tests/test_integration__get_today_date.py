"""
Integration tests for the wished 'get_today_date' tool on TestBot.

Wish:  add a tool that returns today's date as ISO 8601
Agent: TestBot
Blast: tool
Capability gaps: none registered for TestBot (no manifest on file).

6 conversations:
  happy_path_1  — direct "what is today's date?"
  happy_path_2  — explicit ISO 8601 mention
  edge_case     — implicit date need embedded in a task request
  edge_case_2   — date request arrives after an unrelated turn
  bad_input     — user asks for a historical date (today-tool must NOT fire)
  no_action     — completely unrelated request (greeting)

These tests MUST FAIL against the current agent (tool does not yet exist)
and PASS after the wish is implemented.

Run with:
    cd test-agent && python -m pytest tests/test_integration__get_today_date.py -v
"""
from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

TODAY_ISO = date.today().isoformat()   # e.g. "2026-05-25"
ISO_RE = re.compile(r"\d{4}-\d{2}-\d{2}")

# ---------------------------------------------------------------------------
# Conversation specs
# ---------------------------------------------------------------------------

CONVERSATIONS = [
    # ── happy_path_1 ────────────────────────────────────────────────────
    {
        "id": "happy_path_1",
        "description": "Direct, unambiguous request for today's date.",
        "messages": [
            {"role": "user", "content": "What is today's date?"}
        ],
        "expected_behavior": (
            f"The agent must call get_today_date and include '{TODAY_ISO}' "
            "in its reply. Must not refuse or hallucinate a date."
        ),
        "must_use_tool": "get_today_date",
        "must_contain": TODAY_ISO,
    },

    # ── happy_path_2 ────────────────────────────────────────────────────
    {
        "id": "happy_path_2",
        "description": "User explicitly requests ISO 8601 format.",
        "messages": [
            {"role": "user", "content": "Give me today's date in ISO 8601 format."}
        ],
        "expected_behavior": (
            "The agent must call get_today_date and return the date as ISO 8601. "
            f"The reply must contain '{TODAY_ISO}'."
        ),
        "must_use_tool": "get_today_date",
        "must_contain": TODAY_ISO,
    },

    # ── edge_case ────────────────────────────────────────────────────────
    {
        "id": "edge_case",
        "description": "Implicit date need embedded in a task (form filling).",
        "messages": [
            {
                "role": "user",
                "content": (
                    "I'm filling out a form that needs today's date. "
                    "Can you give it to me as a machine-readable date string?"
                ),
            }
        ],
        "expected_behavior": (
            "The agent must recognise the implicit date request, call "
            f"get_today_date, and provide '{TODAY_ISO}'. "
            "'machine-readable' signals ISO 8601 is expected."
        ),
        "must_use_tool": "get_today_date",
        "must_contain": TODAY_ISO,
    },

    # ── edge_case_2 ──────────────────────────────────────────────────────
    {
        "id": "edge_case_2",
        "description": "Date request arrives after an unrelated greeting exchange.",
        "messages": [
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hello, world! I'm TestBot."},
            {"role": "user", "content": "By the way, what's today's date in ISO format?"},
        ],
        "expected_behavior": (
            "Even after an unrelated prior turn the agent must call "
            f"get_today_date and reply with '{TODAY_ISO}'."
        ),
        "must_use_tool": "get_today_date",
        "must_contain": TODAY_ISO,
    },

    # ── bad_input ────────────────────────────────────────────────────────
    {
        "id": "bad_input",
        "description": "User asks for a historical date — today-tool must NOT fire.",
        "messages": [
            {"role": "user", "content": "What was the date on July 4th, 1776?"}
        ],
        "expected_behavior": (
            "The agent must NOT call get_today_date for a historical query. "
            "It may answer '1776-07-04' from knowledge but must never return "
            "today's date as the answer to a historical question."
        ),
        "must_not_use_tool": "get_today_date",
    },

    # ── no_action ────────────────────────────────────────────────────────
    {
        "id": "no_action",
        "description": "Unrelated greeting request — no date tool should fire.",
        "messages": [
            {"role": "user", "content": "Say hello to Alice."}
        ],
        "expected_behavior": (
            "The agent must greet Alice via the 'greet' tool. "
            "It must NOT invoke get_today_date."
        ),
        "must_not_use_tool": "get_today_date",
        "must_use_tool": "greet",
    },
]


# ---------------------------------------------------------------------------
# pytest harness
# ---------------------------------------------------------------------------

def _extract_tool_names(response) -> list[str]:
    """Pull tool names from whatever shape response.tool_calls takes."""
    calls = getattr(response, "tool_calls", None) or []
    names: list[str] = []
    for tc in calls:
        name = getattr(tc, "tool", None) or getattr(tc, "name", None)
        if name:
            names.append(name)
    return names


@pytest.mark.parametrize("conv", CONVERSATIONS, ids=[c["id"] for c in CONVERSATIONS])
def test_conversation(conv, mind):
    """
    Run each conversation against the live TestBot mind and assert the
    expected_behavior described in the conversation spec.

    The 'mind' fixture must be provided by conftest.py as a live Mind
    instance wired to TestBot.

    happy_path_* and edge_case* tests FAIL until get_today_date is
    implemented because the tool call will not happen and TODAY_ISO will
    not appear in the reply.
    """
    messages = conv["messages"]
    user_message = messages[-1]["content"]
    history = messages[:-1]

    # Dispatch — adapt to the fixture interface available
    if history and hasattr(mind, "think_with_history"):
        response = mind.think_with_history(user_message, history=history)
    else:
        response = mind.think(user_message)

    reply_text: str = getattr(response, "text", str(response))
    tool_names = _extract_tool_names(response)

    must_contain = conv.get("must_contain")
    must_use = conv.get("must_use_tool")
    must_not_use = conv.get("must_not_use_tool")

    if must_contain:
        assert must_contain in reply_text, (
            f"[{conv['id']}] Expected '{must_contain}' in reply.\n"
            f"Got: {reply_text!r}\n"
            f"Expected behavior: {conv['expected_behavior']}"
        )

    if must_use:
        assert must_use in tool_names, (
            f"[{conv['id']}] Expected tool '{must_use}' to be called.\n"
            f"Tools actually called: {tool_names}\n"
            f"Expected behavior: {conv['expected_behavior']}"
        )

    if must_not_use:
        assert must_not_use not in tool_names, (
            f"[{conv['id']}] Tool '{must_not_use}' must NOT be called.\n"
            f"Tools actually called: {tool_names}\n"
            f"Expected behavior: {conv['expected_behavior']}"
        )
