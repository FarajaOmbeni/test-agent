"""
Unit tests for the get_today_date tool on TestBot.

Wish:  add a tool that returns today's date as ISO 8601
Agent: TestBot  (src/agents/TestBot)
Blast: tool

These tests MUST FAIL initially — they describe behavior that does not yet exist.
Capability gaps: none registered for TestBot (no manifest on file).

Run with:
    cd test-agent && python -m pytest tests/test_unit__get_today_date.py -v
"""
from __future__ import annotations

import inspect
import re
import sys
from datetime import date, datetime
from pathlib import Path

import pytest

# Make sure the src package is importable when running from the project root.
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")           # YYYY-MM-DD
ISO_DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


# ---------------------------------------------------------------------------
# Gate 1 — the symbol must exist in the module
# ---------------------------------------------------------------------------

class TestGetTodayDateToolExists:
    """Verify that the wished tool is present in TestBot's contract surface.

    The wish says 'add a tool' — the very first requirement is that the
    symbol get_today_date exists and is importable.  Every test in this
    class will fail with ImportError until main.py is updated.
    """

    def test_tool_is_importable(self):
        """get_today_date must be importable from agents.TestBot.main.
        Fails until the @tool-decorated function is added."""
        from agents.TestBot.main import get_today_date  # noqa: F401

    def test_tool_is_callable(self):
        """The imported symbol must be callable."""
        from agents.TestBot.main import get_today_date
        assert callable(get_today_date), "get_today_date must be callable"

    def test_tool_is_distinct_from_greet(self):
        """get_today_date must be a separate tool, not an alias for greet."""
        from agents.TestBot.main import get_today_date, greet
        assert get_today_date is not greet


# ---------------------------------------------------------------------------
# Gate 2 — the underlying function returns an ISO 8601 string
# ---------------------------------------------------------------------------

def _call_raw(fn, *args, **kwargs):
    """Call fn, tolerating a leading 'self: Mind' param by passing None."""
    sig = inspect.signature(fn)
    params = list(sig.parameters.keys())
    if params and params[0] == "self":
        return fn(None, *args, **kwargs)
    return fn(*args, **kwargs)


class TestGetTodayDateReturnShape:
    """Verify output conforms to ISO 8601 format.

    Wish intent: 'returns today's date as ISO 8601' — the exact format
    matters.  Tests fail if the tool returns 'May 25, 2026' or similar.
    """

    def test_returns_string(self):
        """The tool must return a str, not None, int, or dict."""
        from agents.TestBot.main import get_today_date
        result = _call_raw(get_today_date)
        assert isinstance(result, str), f"Expected str, got {type(result).__name__}"

    def test_returns_iso_8601(self):
        """Output must match YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS… (ISO 8601).
        Fails for locale-formatted strings like 'May 25, 2026'."""
        from agents.TestBot.main import get_today_date
        result = _call_raw(get_today_date)
        assert ISO_DATE_RE.match(result) or ISO_DATETIME_RE.match(result), (
            f"'{result}' does not match ISO 8601 "
            "(expected YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS…)"
        )

    def test_date_portion_is_today(self):
        """The YYYY-MM-DD portion must equal today's local date."""
        from agents.TestBot.main import get_today_date
        result = _call_raw(get_today_date)
        date_part = result[:10]
        today = date.today().isoformat()
        assert date_part == today, (
            f"Expected today ({today}) but got date portion '{date_part}'"
        )

    def test_parseable_by_stdlib(self):
        """The returned string must be accepted by datetime.fromisoformat()."""
        from agents.TestBot.main import get_today_date
        result = _call_raw(get_today_date)
        try:
            datetime.fromisoformat(result)
        except ValueError as exc:
            pytest.fail(f"datetime.fromisoformat() rejected '{result}': {exc}")


# ---------------------------------------------------------------------------
# Gate 3 — tool signature contract
# ---------------------------------------------------------------------------

class TestGetTodayDateToolSignature:
    """Verify the tool's public contract — no required user-supplied arguments.

    'Returns today's date' implies zero user input.  A tool that required
    arguments would break agent auto-invocation.
    """

    def test_callable_with_no_user_args(self):
        """Must be invocable without any user-supplied arguments."""
        from agents.TestBot.main import get_today_date
        result = _call_raw(get_today_date)
        assert result is not None, "get_today_date() returned None"

    def test_no_required_params_beyond_self(self):
        """Parameters other than 'self' must all have defaults."""
        from agents.TestBot.main import get_today_date
        sig = inspect.signature(get_today_date)
        for name, param in sig.parameters.items():
            if name == "self":
                continue
            assert param.default is not inspect.Parameter.empty, (
                f"Parameter '{name}' has no default — "
                "a date tool should require no user input."
            )


# ---------------------------------------------------------------------------
# Gate 4 — idempotency within the same day
# ---------------------------------------------------------------------------

class TestGetTodayDateIdempotency:
    """The tool must be deterministic within a single day."""

    def test_two_rapid_calls_agree(self):
        """Two back-to-back calls must return the same YYYY-MM-DD."""
        from agents.TestBot.main import get_today_date
        first = _call_raw(get_today_date)
        second = _call_raw(get_today_date)
        assert first[:10] == second[:10], (
            f"Inconsistent results on same day: '{first}' vs '{second}'"
        )


# ---------------------------------------------------------------------------
# Guard — existing tools do NOT accidentally satisfy the wish
# (Capability gaps: none registered, so no extra gap-driven classes needed)
# ---------------------------------------------------------------------------

class TestExistingToolsDoNotSatisfyWish:
    """Confirm that greet() does not return an ISO 8601 date.

    This is a baseline guard — if greet already returned a date the wish
    would be pointless.  Also documents that the new tool is genuinely
    additive.
    """

    def test_greet_does_not_return_iso_date(self):
        """greet() must not accidentally satisfy the ISO-date requirement."""
        from agents.TestBot.main import greet
        result = _call_raw(greet)
        assert not (ISO_DATE_RE.match(str(result)) or ISO_DATETIME_RE.match(str(result))), (
            "greet() returned an ISO 8601 string — is it masquerading as get_today_date?"
        )
