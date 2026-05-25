"""TestBot — contract surface.

Minimal agent with one starter tool. Used to test mind.evolve()
adding new tools at runtime.
"""
from __future__ import annotations

import json
import logging

from nodeai.api import brain, tool, storage, Mind

AGENT_NAME = "TestBot"

_log = logging.getLogger(__name__)


# ── Storage ─────────────────────────────────────────────────────────────

@storage([AGENT_NAME])
def testbot_storage(*, node=None, **_kw):
    return {
        "storage_type": "LocalMemory",
        "storage_config": {"base_directory": "./data"},
    }


# ── Brain ───────────────────────────────────────────────────────────────

@brain([AGENT_NAME])
def testbot_brain(mind=None, node=None, **_kw):
    return {
        "instructions": (
            "You are TestBot, a helpful assistant with evolving capabilities. "
            "Use your tools to help users. When asked to do something you "
            "cannot do with your current tools, use the evolve_capability tool "
            "to permanently add that capability, then use the new tool to "
            "fulfill the request."
        ),
        "send_final_message": True,
        "filter_noise": False,
        "clients": [
            {
                "provider": "anthropic",
                "model_configs": {
                    "model": "claude-sonnet-4-20250514",
                },
            },
        ],
    }


# ── Tools ───────────────────────────────────────────────────────────────

@tool([AGENT_NAME])
def greet(self: Mind, name: str = "world") -> str:
    """Greet someone by name.

    Use when: the user asks for a greeting.

    name: The person's name to greet.
    """
    return f"Hello, {name}! I'm TestBot."


@tool([AGENT_NAME])
def evolve_capability(self: Mind, wish: str = "") -> str:
    """Add a new capability to this agent via self-evolution.

    Use when: you cannot fulfill a user request with existing tools
    and want to permanently add that capability. The evolution runs
    in the background — the new tool will be available on the next
    interaction.

    wish: Natural-language description of the tool/capability to add.
        Example: "add a tool that returns today's date as ISO 8601"
    """
    if not wish:
        return "Error: 'wish' parameter is required. Describe what capability to add."

    _log.info("[EVOLVE] Starting background evolution: %s", wish)
    evo_id = self.evolve_background(query=wish, blast_radius="tool", revert_on_regression=True)

    return json.dumps({
        "status": "evolving",
        "evo_id": evo_id,
        "message": "Evolution started in background. The new tool will be available shortly — ask me again in a moment.",
    })




# ── Internal hooks ──────────────────────────────────────────────────────


@tool([AGENT_NAME], internal=True)
def on_think_start(self: Mind) -> str | None:
    """Check for completed background evolutions and announce them."""
    pending = self.unbox("pending_evolutions", [])
    if not pending or not isinstance(pending, list):
        return None

    completed = [e for e in pending if isinstance(e, dict) and e.get("status") != "in_progress"]
    if not completed:
        return None

    # Keep only still-in-progress entries
    still_pending = [e for e in pending if isinstance(e, dict) and e.get("status") == "in_progress"]
    self.box("pending_evolutions", still_pending)

    # Build announcement for the LLM
    announcements = []
    for e in completed:
        if e.get("status") == "success":
            announcements.append(
                f"[SYSTEM] Evolution '{e.get('query', '')}' completed successfully. "
                f"New tools are now available. Use them to help the user."
            )
        else:
            announcements.append(
                f"[SYSTEM] Evolution '{e.get('query', '')}' {e.get('status')}: "
                f"{e.get('error', 'see logs for details')}"
            )

    return "\n".join(announcements) if announcements else None
