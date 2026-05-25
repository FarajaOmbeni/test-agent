"""
Integration tests for the wished 'get_current_weather' tool on TestBot.

Wish:  add a tool that can get current weather information for a given location
Agent: TestBot
Blast: tool

6 conversations:
  happy_path_1  — direct "what is the weather in London?"
  happy_path_2  — temperature query for a specific city
  edge_case     — weather embedded in a planning request
  edge_case_2   — weather request arrives after an unrelated turn
  bad_input     — historical weather (today-tool must NOT fire)
  no_action     — completely unrelated request (greeting)

These tests MUST FAIL against the current agent (tool does not yet exist)
and PASS after the wish is implemented.

Run with:
    cd test-agent && python -m pytest tests/test_integration__get_current_weather.py -v
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# ---------------------------------------------------------------------------
# Conversation specs
# ---------------------------------------------------------------------------

CONVERSATIONS = [
    # ── happy_path_1 ────────────────────────────────────────────────────
    {
        "id": "happy_path_1",
        "description": "Direct, unambiguous request for current weather in a city.",
        "messages": [
            {"role": "user", "content": "What is the weather like in London right now?"}
        ],
        "expected_behavior": (
            "The agent must call get_current_weather with location='London' and "
            "return current conditions (temperature, condition description, etc.). "
            "Must not refuse or fabricate data."
        ),
        "must_use_tool": "get_current_weather",
    },

    # ── happy_path_2 ────────────────────────────────────────────────────
    {
        "id": "happy_path_2",
        "description": "User asks for the current temperature in a specific city.",
        "messages": [
            {"role": "user", "content": "What's the temperature in Tokyo right now?"}
        ],
        "expected_behavior": (
            "The agent must call get_current_weather with location='Tokyo' and "
            "include temperature information in the reply."
        ),
        "must_use_tool": "get_current_weather",
    },

    # ── edge_case ────────────────────────────────────────────────────────
    {
        "id": "edge_case",
        "description": "Weather need embedded in a planning request.",
        "messages": [
            {
                "role": "user",
                "content": (
                    "I'm planning a picnic in Paris today. "
                    "Can you check if the weather is suitable?"
                ),
            }
        ],
        "expected_behavior": (
            "The agent must recognise the implicit weather check, call "
            "get_current_weather with location='Paris', and give a relevant "
            "answer about suitability for a picnic."
        ),
        "must_use_tool": "get_current_weather",
    },

    # ── edge_case_2 ──────────────────────────────────────────────────────
    {
        "id": "edge_case_2",
        "description": "Weather request arrives after an unrelated greeting exchange.",
        "messages": [
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hello, world! I'm TestBot."},
            {"role": "user", "content": "Can you check the current weather in New York?"},
        ],
        "expected_behavior": (
            "Even after an unrelated prior turn the agent must call "
            "get_current_weather with location='New York' and report conditions."
        ),
        "must_use_tool": "get_current_weather",
    },

    # ── bad_input ────────────────────────────────────────────────────────
    {
        "id": "bad_input",
        "description": "User asks for historical weather — current-weather tool must NOT fire.",
        "messages": [
            {
                "role": "user",
                "content": "What was the weather like in Berlin on January 1st, 1990?",
            }
        ],
        "expected_behavior": (
            "The agent must NOT call get_current_weather for a historical query. "
            "It may answer from knowledge or say it cannot retrieve historical data, "
            "but must never return current weather as the answer to a past-date question."
        ),
        "must_not_use_tool": "get_current_weather",
    },

    # ── no_action ────────────────────────────────────────────────────────
    {
        "id": "no_action",
        "description": "Unrelated greeting request — no weather tool should fire.",
        "messages": [
            {"role": "user", "content": "Say hello to Alice."}
        ],
        "expected_behavior": (
            "The agent must greet Alice via the 'greet' tool. "
            "It must NOT invoke get_current_weather."
        ),
        "must_not_use_tool": "get_current_weather",
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

    happy_path_* and edge_case* tests FAIL until get_current_weather is
    implemented because the tool call will not happen.
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
