"""
Unit tests for the get_current_weather tool on TestBot.

Wish:  add a tool that can get current weather information for a given location
Agent: TestBot  (src/agents/TestBot)
Blast: tool

These tests MUST FAIL initially — they describe behavior that does not yet exist.

Run with:
    cd test-agent && python -m pytest tests/test_unit__get_current_weather.py -v
"""
from __future__ import annotations

import inspect
import json
import sys
import unittest.mock as mock
from pathlib import Path

import pytest

# Make sure the src package is importable when running from the project root.
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


# ---------------------------------------------------------------------------
# Gate 1 — the symbol must exist in the module
# ---------------------------------------------------------------------------

class TestGetCurrentWeatherToolExists:
    """Verify that the wished tool is present in TestBot's contract surface."""

    def test_tool_is_importable(self):
        """get_current_weather must be importable from agents.TestBot.main."""
        from agents.TestBot.main import get_current_weather  # noqa: F401

    def test_tool_is_callable(self):
        """The imported symbol must be callable."""
        from agents.TestBot.main import get_current_weather
        assert callable(get_current_weather), "get_current_weather must be callable"

    def test_tool_is_distinct_from_greet(self):
        """get_current_weather must be a separate tool, not an alias for greet."""
        from agents.TestBot.main import get_current_weather, greet
        assert get_current_weather is not greet

    def test_tool_is_in_tools_list(self):
        """get_current_weather must appear in the module-level TOOLS list."""
        from agents.TestBot import main as m
        tools = getattr(m, "TOOLS", None)
        assert tools is not None, "TOOLS list not found in agents.TestBot.main"
        tool_names = [getattr(t, "__name__", None) or getattr(t, "name", None) for t in tools]
        assert "get_current_weather" in tool_names, (
            f"get_current_weather not in TOOLS list. Found: {tool_names}"
        )


# ---------------------------------------------------------------------------
# Gate 2 — signature contract
# ---------------------------------------------------------------------------

class TestGetCurrentWeatherSignature:
    """Verify the tool's public parameter contract."""

    def test_has_location_param(self):
        """Must accept a 'location' parameter."""
        from agents.TestBot.main import get_current_weather
        sig = inspect.signature(get_current_weather)
        assert "location" in sig.parameters, (
            "get_current_weather must have a 'location' parameter"
        )

    def test_location_has_default(self):
        """'location' must have a default so the LLM can omit it."""
        from agents.TestBot.main import get_current_weather
        sig = inspect.signature(get_current_weather)
        param = sig.parameters["location"]
        assert param.default is not inspect.Parameter.empty, (
            "'location' parameter should have a default value"
        )

    def test_no_required_params_beyond_self_and_location(self):
        """Parameters other than 'self' and 'location' must all have defaults."""
        from agents.TestBot.main import get_current_weather
        sig = inspect.signature(get_current_weather)
        for name, param in sig.parameters.items():
            if name in ("self", "location"):
                continue
            assert param.default is not inspect.Parameter.empty, (
                f"Parameter '{name}' has no default — unexpected required parameter."
            )


# ---------------------------------------------------------------------------
# Gate 3 — missing location guard
# ---------------------------------------------------------------------------

def _call_raw(fn, *args, **kwargs):
    """Call fn, tolerating a leading 'self: Mind' param by passing None."""
    sig = inspect.signature(fn)
    params = list(sig.parameters.keys())
    if params and params[0] == "self":
        return fn(None, *args, **kwargs)
    return fn(*args, **kwargs)


class TestGetCurrentWeatherMissingLocation:
    """Verify graceful handling when location is absent."""

    def test_empty_location_returns_error_string(self):
        """Calling with location='' must return an error string, not raise."""
        from agents.TestBot.main import get_current_weather
        result = _call_raw(get_current_weather, location="")
        assert isinstance(result, str), "Must return str even on bad input"
        assert "error" in result.lower() or "required" in result.lower(), (
            f"Expected error message for empty location, got: {result!r}"
        )

    def test_no_exception_on_empty_location(self):
        """Must not raise for empty location."""
        from agents.TestBot.main import get_current_weather
        try:
            _call_raw(get_current_weather, location="")
        except Exception as exc:
            pytest.fail(f"get_current_weather raised on empty location: {exc}")


# ---------------------------------------------------------------------------
# Gate 4 — happy-path return shape (mocked HTTP)
# ---------------------------------------------------------------------------

_MOCK_WTTR_RESPONSE = {
    "current_condition": [
        {
            "weatherDesc": [{"value": "Partly cloudy"}],
            "temp_C": "18",
            "temp_F": "64",
            "FeelsLikeC": "17",
            "FeelsLikeF": "63",
            "humidity": "72",
            "windspeedKmph": "15",
            "winddir16Point": "SW",
            "visibility": "10",
            "uvIndex": "3",
        }
    ],
    "nearest_area": [
        {
            "areaName": [{"value": "London"}],
            "country": [{"value": "United Kingdom"}],
        }
    ],
}


def _make_mock_urlopen(payload: dict):
    """Return a context-manager mock that yields fake HTTP response bytes."""
    raw = json.dumps(payload).encode()
    cm = mock.MagicMock()
    cm.__enter__ = mock.Mock(return_value=cm)
    cm.__exit__ = mock.Mock(return_value=False)
    cm.read = mock.Mock(return_value=raw)
    return cm


class TestGetCurrentWeatherReturnShape:
    """Verify the JSON structure returned for a known mocked response."""

    def _call_mocked(self, location: str) -> dict:
        from agents.TestBot.main import get_current_weather
        import urllib.request
        with mock.patch.object(urllib.request, "urlopen",
                               return_value=_make_mock_urlopen(_MOCK_WTTR_RESPONSE)):
            raw = _call_raw(get_current_weather, location=location)
        return json.loads(raw)

    def test_returns_string(self):
        """Must return a str (JSON-encoded)."""
        from agents.TestBot.main import get_current_weather
        import urllib.request
        with mock.patch.object(urllib.request, "urlopen",
                               return_value=_make_mock_urlopen(_MOCK_WTTR_RESPONSE)):
            result = _call_raw(get_current_weather, location="London")
        assert isinstance(result, str), f"Expected str, got {type(result).__name__}"

    def test_returns_valid_json(self):
        """Return value must be valid JSON."""
        data = self._call_mocked("London")
        assert isinstance(data, dict)

    def test_has_location_key(self):
        """Result must include 'location'."""
        data = self._call_mocked("London")
        assert "location" in data, f"Missing 'location' key. Keys: {list(data.keys())}"

    def test_has_condition_key(self):
        """Result must include 'condition'."""
        data = self._call_mocked("London")
        assert "condition" in data, f"Missing 'condition' key. Keys: {list(data.keys())}"

    def test_has_temperature_keys(self):
        """Result must include temperature_c and temperature_f."""
        data = self._call_mocked("London")
        assert "temperature_c" in data, "Missing 'temperature_c'"
        assert "temperature_f" in data, "Missing 'temperature_f'"

    def test_has_humidity_key(self):
        """Result must include humidity_pct."""
        data = self._call_mocked("London")
        assert "humidity_pct" in data, "Missing 'humidity_pct'"

    def test_has_wind_keys(self):
        """Result must include wind_kmph and wind_direction."""
        data = self._call_mocked("London")
        assert "wind_kmph" in data, "Missing 'wind_kmph'"
        assert "wind_direction" in data, "Missing 'wind_direction'"

    def test_condition_matches_mock(self):
        """The condition field must reflect the mocked weatherDesc."""
        data = self._call_mocked("London")
        assert data["condition"] == "Partly cloudy", (
            f"Expected 'Partly cloudy', got {data['condition']!r}"
        )

    def test_temperature_c_matches_mock(self):
        """temperature_c must match the mocked value."""
        data = self._call_mocked("London")
        assert str(data["temperature_c"]) == "18", (
            f"Expected '18', got {data['temperature_c']!r}"
        )


# ---------------------------------------------------------------------------
# Gate 5 — network error handling
# ---------------------------------------------------------------------------

class TestGetCurrentWeatherNetworkErrors:
    """Verify the tool degrades gracefully on network failures."""

    def test_url_error_returns_json_error(self):
        """URLError must yield a JSON string with an 'error' key, not an exception."""
        import urllib.error
        import urllib.request
        from agents.TestBot.main import get_current_weather

        with mock.patch.object(urllib.request, "urlopen",
                               side_effect=urllib.error.URLError("connection refused")):
            result = _call_raw(get_current_weather, location="Nowhere")

        assert isinstance(result, str), "Must return str on network error"
        data = json.loads(result)
        assert "error" in data, f"Expected 'error' key in result. Got: {data}"

    def test_generic_exception_returns_json_error(self):
        """Any unexpected exception must yield a JSON string with 'error', not propagate."""
        import urllib.request
        from agents.TestBot.main import get_current_weather

        with mock.patch.object(urllib.request, "urlopen",
                               side_effect=RuntimeError("unexpected")):
            result = _call_raw(get_current_weather, location="Somewhere")

        assert isinstance(result, str)
        data = json.loads(result)
        assert "error" in data


# ---------------------------------------------------------------------------
# Guard — existing tools do NOT accidentally satisfy the wish
# ---------------------------------------------------------------------------

class TestExistingToolsDoNotSatisfyWish:
    """Confirm that greet() does not return weather data."""

    def test_greet_does_not_return_weather_json(self):
        """greet() must not accidentally return a weather payload."""
        from agents.TestBot.main import greet
        result = _call_raw(greet, name="world")
        # Should not be a JSON dict with weather keys
        try:
            data = json.loads(str(result))
            weather_keys = {"condition", "temperature_c", "temperature_f"}
            assert not weather_keys.intersection(data.keys()), (
                "greet() returned weather-like JSON — something is wrong."
            )
        except (json.JSONDecodeError, AttributeError):
            pass  # Not JSON at all — that's fine
