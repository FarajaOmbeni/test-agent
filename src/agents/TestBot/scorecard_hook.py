"""Live Scorecard monitor — reports every TestBot interaction in real-time.

Registers an on_think_ended hook that sends each response to the Scorecard
dashboard as it happens. Activated only when SCORECARD_API_KEY is set.

Import this module from TestBot.__init__ to auto-register the hook.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

from nodeai.api import tool, Mind

AGENT_NAME = "TestBot"

_log = logging.getLogger(__name__)

# ── Singleton state ────────────────────────────────────────────────────
_scorecard_client = None
_active_runs: dict[str, str] = {}  # mind_id -> run_id


def _get_client():
    """Lazy-init a Scorecard client, cached for the process lifetime."""
    global _scorecard_client
    if _scorecard_client is None:
        from scorecard_ai import Scorecard

        _scorecard_client = Scorecard(api_key=os.environ["SCORECARD_API_KEY"])
    return _scorecard_client


def _get_or_create_run(mind: Mind) -> str:
    """Return an active Scorecard Run ID for this mind, creating one if needed."""
    mind_id = getattr(mind, "mind_id", None) or "default"
    if mind_id in _active_runs:
        return _active_runs[mind_id]

    client = _get_client()
    project_id = os.environ.get("SCORECARD_PROJECT_ID", "")
    if not project_id:
        raise ValueError("SCORECARD_PROJECT_ID not set")

    run = client.runs.create(project_id=project_id)
    _active_runs[mind_id] = run.id
    _log.info("[SCORECARD] Created run %s for mind %s", run.id, mind_id)
    return run.id


def _last_user_message(mind: Mind) -> str:
    """Extract the most recent user message from the mind's memory."""
    try:
        memory = mind.memory
        if not memory:
            return ""
        for thought in reversed(memory):
            role = getattr(thought, "role", None)
            if role == "user":
                return getattr(thought, "content", str(thought))
    except Exception:
        pass
    return ""


# ── Hook ───────────────────────────────────────────────────────────────

@tool([AGENT_NAME], internal=True)
def on_think_ended(self: Mind, final_thought: Any = None) -> None:
    """Report each interaction to Scorecard dashboard in real-time."""
    if not os.environ.get("SCORECARD_API_KEY"):
        return

    try:
        client = _get_client()
        run_id = _get_or_create_run(self)

        user_msg = _last_user_message(self)
        response_text = ""
        if final_thought is not None:
            response_text = getattr(final_thought, "content", str(final_thought))

        tool_names = []
        tool_calls = getattr(final_thought, "tool_calls", None) or []
        for tc in tool_calls:
            name = getattr(tc, "tool", None) or getattr(tc, "name", None)
            if name:
                tool_names.append(name)

        client.records.create(
            run_id=run_id,
            inputs={
                "user_message": user_msg,
                "timestamp": str(int(time.time())),
            },
            outputs={
                "response": response_text,
                "tools_called": ", ".join(tool_names) if tool_names else "none",
            },
        )

        _log.debug("[SCORECARD] Recorded interaction: %s -> %s",
                   user_msg[:60], response_text[:60])

    except Exception as exc:
        _log.warning("[SCORECARD] Failed to record interaction: %s", exc)
