"""
Unit tests for the wished `get_current_datetime` tool on TestBot.

Wish: "add a tool that gets the current date and time"

These tests are written BEFORE the tool exists and MUST fail against the
current agent code. They describe the contract the new tool must fulfill.

Agent: TestBot  (src/agents/TestBot)
Import prefix: agents.TestBot
"""

import inspect
import re
import pytest
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_main():
    """Import agents.TestBot.main; return the module object."""
    import importlib
    return importlib.import_module("agents.TestBot.main")


def _get_mind_class():
    mod = _load_main()
    # Convention: the Mind class is the one that owns the tool methods
    for name, obj in inspect.getmembers(mod, inspect.isclass):
        if hasattr(obj, "get_current_datetime"):
            return obj
    # If class not found the test will fail at assertion time
    return getattr(mod, "Mind", None)


# ---------------------------------------------------------------------------
# Class 1: Tool presence
# ---------------------------------------------------------------------------

class TestGetCurrentDatetimeToolExists:
    """The tool must be present on the Mind class before any behavior can work."""

    def test_tool_is_defined_on_module(self):
        """
        Wish: the agent should expose a callable named `get_current_datetime`.
        Fails now because no such tool exists on TestBot.
        """
        mod = _load_main()
        assert hasattr(mod, "get_current_datetime") or _get_mind_class() is not None, (
            "Neither a standalone function nor a Mind class with "
            "`get_current_datetime` was found in agents.TestBot.main"
        )

    def test_tool_is_callable_on_mind_class(self):
        """
        The get_current_datetime method must exist directly on the Mind class
        so the framework can register it as a tool.
        """
        mind_cls = _get_mind_class()
        assert mind_cls is not None, "Mind class not found in agents.TestBot.main"
        assert hasattr(mind_cls, "get_current_datetime"), (
            "Mind class has no `get_current_datetime` attribute — "
            "tool has not been added yet"
        )
        assert callable(getattr(mind_cls, "get_current_datetime")), (
            "`get_current_datetime` exists but is not callable"
        )


# ---------------------------------------------------------------------------
# Class 2: Tool signature
# ---------------------------------------------------------------------------

class TestGetCurrentDatetimeSignature:
    """The tool signature must be compatible with the framework's tool-calling pattern."""

    def test_signature_has_self_parameter(self):
        """
        All agent tools take `self: Mind` as first parameter.
        Confirms the tool is an instance method, not a standalone function.
        """
        mind_cls = _get_mind_class()
        assert mind_cls is not None, "Mind class not found"
        fn = getattr(mind_cls, "get_current_datetime", None)
        assert fn is not None, "`get_current_datetime` not found on Mind"
        sig = inspect.signature(fn)
        params = list(sig.parameters.keys())
        assert params[0] == "self", (
            f"First parameter should be 'self', got '{params[0]}'"
        )

    def test_no_required_non_self_parameters(self):
        """
        Getting the current datetime requires no user-supplied arguments.
        All parameters beyond `self` must have defaults.
        """
        mind_cls = _get_mind_class()
        assert mind_cls is not None, "Mind class not found"
        fn = getattr(mind_cls, "get_current_datetime", None)
        assert fn is not None, "`get_current_datetime` not found on Mind"
        sig = inspect.signature(fn)
        for pname, param in sig.parameters.items():
            if pname == "self":
                continue
            assert param.default is not inspect.Parameter.empty, (
                f"Parameter `{pname}` has no default — tool requires user input "
                "but should be callable with zero arguments"
            )

    def test_has_docstring_with_use_when(self):
        """
        Framework convention: docstrings must include a 'Use when:' section
        so the LLM knows when to invoke the tool (see greet / evolve_capability).
        """
        mind_cls = _get_mind_class()
        assert mind_cls is not None, "Mind class not found"
        fn = getattr(mind_cls, "get_current_datetime", None)
        assert fn is not None, "`get_current_datetime` not found on Mind"
        doc = inspect.getdoc(fn) or ""
        assert "Use when:" in doc, (
            "Tool docstring must include 'Use when:' per project convention. "
            f"Got docstring: {doc!r}"
        )


# ---------------------------------------------------------------------------
# Class 3: Return value contract
# ---------------------------------------------------------------------------

class TestGetCurrentDatetimeReturnValue:
    """The tool must return a string that contains parseable date/time information."""

    def _call_tool(self):
        """Instantiate Mind and call get_current_datetime()."""
        mind_cls = _get_mind_class()
        assert mind_cls is not None, "Mind class not found"
        instance = mind_cls.__new__(mind_cls)  # bypass __init__ if heavy
        fn = getattr(instance, "get_current_datetime", None)
        assert fn is not None, "`get_current_datetime` not found on Mind instance"
        return fn()

    def test_returns_a_string(self):
        """
        Wish: tool should return current date and time — the natural type is str.
        """
        result = self._call_tool()
        assert isinstance(result, str), (
            f"Expected str return, got {type(result).__name__}: {result!r}"
        )

    def test_return_contains_current_year(self):
        """
        The returned string must contain the current 4-digit year, proving
        it reflects real wall-clock time rather than a hardcoded stub.
        """
        result = self._call_tool()
        current_year = str(datetime.now().year)
        assert current_year in result, (
            f"Current year {current_year} not found in result: {result!r}"
        )

    def test_return_contains_time_components(self):
        """
        The return value must contain at least hour/minute information
        (e.g., '14:30' or 'T14:30') so it satisfies the 'time' part of the wish.
        """
        result = self._call_tool()
        # Matches HH:MM with optional seconds
        time_pattern = re.compile(r"\d{1,2}:\d{2}")
        assert time_pattern.search(result), (
            f"No time pattern (HH:MM) found in result: {result!r}"
        )

    def test_return_is_not_empty(self):
        """
        Basic guard: the tool must not return an empty string.
        """
        result = self._call_tool()
        assert result.strip(), "Tool returned an empty or whitespace-only string"


# ---------------------------------------------------------------------------
# Class 4: LLM routing
# ---------------------------------------------------------------------------

class TestGetCurrentDatetimeRouting:
    """
    Verify the tool is registered so the LLM can discover and invoke it.
    This checks framework-level metadata, not just Python attribute presence.
    """

    def test_tool_appears_in_agent_tool_list(self):
        """
        Many frameworks expose a list of registered tools (e.g., Mind.__tools__,
        Mind.tools, or a module-level TOOLS list).  The new tool must appear
        there so the LLM can call it.

        If the project has no such registry, this test should be updated once
        the convention is known; for now it asserts the attribute exists.
        """
        mod = _load_main()
        mind_cls = _get_mind_class()

        # Try common registry patterns
        registry = (
            getattr(mind_cls, "__tools__", None)
            or getattr(mind_cls, "tools", None)
            or getattr(mod, "TOOLS", None)
            or getattr(mod, "__tools__", None)
        )

        assert registry is not None, (
            "Could not find a tool registry on Mind class or module. "
            "Once `get_current_datetime` is added, ensure it's registered."
        )

        tool_names = [
            (t.__name__ if callable(t) else str(t)) for t in registry
        ]
        assert "get_current_datetime" in tool_names, (
            f"`get_current_datetime` not in tool registry. Found: {tool_names}"
        )
