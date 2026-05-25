"""
Unit tests for the `get_current_weather` tool on TestBot.

Wish: add a tool that can get current weather information for a given location
These tests are written to FAIL against the current agent (the tool does not exist yet).
"""
import inspect
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_mind_class():
    """Import the Mind class from the TestBot agent."""
    from agents.TestBot.main import Mind  # noqa: PLC0415
    return Mind


# ---------------------------------------------------------------------------
# Test: tool existence
# ---------------------------------------------------------------------------

class TestGetCurrentWeatherToolExists:
    """The agent must expose a get_current_weather method."""

    def test_tool_is_callable(self):
        """
        Wish: 'add a tool that can get current weather information for a given location'
        get_current_weather must be an attribute and callable on Mind.
        FAILS until the tool is added.
        """
        Mind = get_mind_class()
        assert callable(getattr(Mind, "get_current_weather", None)), (
            "Mind has no callable `get_current_weather` tool — tool does not exist yet"
        )

    def test_tool_in_dir(self):
        """
        Wish: tool existence.
        get_current_weather must appear in dir(Mind).
        FAILS until the tool is added.
        """
        Mind = get_mind_class()
        assert "get_current_weather" in dir(Mind), (
            "`get_current_weather` not found in Mind — tool not yet registered"
        )


# ---------------------------------------------------------------------------
# Test: tool signature
# ---------------------------------------------------------------------------

class TestGetCurrentWeatherSignature:
    """The tool must accept a `location` parameter."""

    def test_has_location_parameter(self):
        """
        Wish: tool accepts 'a given location'.
        get_current_weather must accept a `location` str parameter.
        FAILS until the tool is added.
        """
        Mind = get_mind_class()
        tool = getattr(Mind, "get_current_weather", None)
        assert tool is not None, "Tool does not exist"
        sig = inspect.signature(tool)
        assert "location" in sig.parameters, (
            "`get_current_weather` must have a `location` parameter"
        )

    def test_location_parameter_has_str_annotation(self):
        """
        The `location` parameter should be annotated as str (or unannotated).
        FAILS until the tool is added.
        """
        Mind = get_mind_class()
        tool = getattr(Mind, "get_current_weather", None)
        assert tool is not None, "Tool does not exist"
        sig = inspect.signature(tool)
        param = sig.parameters.get("location")
        assert param is not None, "`location` parameter missing"
        assert param.annotation in (str, inspect.Parameter.empty), (
            "`location` parameter should be annotated as str"
        )

    def test_has_docstring_with_use_when(self):
        """
        Tool docstring must include 'Use when:' to guide the LLM.
        Convention observed in existing tools (greet, get_today_date, etc.).
        FAILS until the tool is added.
        """
        Mind = get_mind_class()
        tool = getattr(Mind, "get_current_weather", None)
        assert tool is not None, "Tool does not exist"
        doc = tool.__doc__ or ""
        assert "Use when" in doc or "use when" in doc.lower(), (
            "Tool docstring must contain 'Use when:' guidance"
        )

    def test_docstring_mentions_weather(self):
        """
        Docstring must mention 'weather' so the LLM can route correctly.
        FAILS until the tool is added.
        """
        Mind = get_mind_class()
        tool = getattr(Mind, "get_current_weather", None)
        assert tool is not None, "Tool does not exist"
        doc = (tool.__doc__ or "").lower()
        assert "weather" in doc, "Docstring must mention 'weather'"

    def test_docstring_mentions_location(self):
        """
        Docstring must mention 'location' so the LLM knows to pass it.
        FAILS until the tool is added.
        """
        Mind = get_mind_class()
        tool = getattr(Mind, "get_current_weather", None)
        assert tool is not None, "Tool does not exist"
        doc = (tool.__doc__ or "").lower()
        assert "location" in doc, "Docstring must mention 'location'"


# ---------------------------------------------------------------------------
# Test: return value shape
# ---------------------------------------------------------------------------

class TestGetCurrentWeatherOutput:
    """The tool must return a non-empty string with weather information."""

    @pytest.fixture
    def mind_instance(self):
        """Create a Mind instance for direct tool invocation."""
        Mind = get_mind_class()
        try:
            return Mind()
        except TypeError:
            pytest.skip("Mind() requires constructor arguments — adjust fixture")

    def test_returns_string(self, mind_instance):
        """
        Wish: 'get current weather information'.
        Tool must return a string.
        FAILS until the tool is added.
        """
        result = mind_instance.get_current_weather(location="London")
        assert isinstance(result, str), (
            f"Expected str, got {type(result)}"
        )

    def test_returns_non_empty(self, mind_instance):
        """
        Tool must return a non-empty string (actual weather info).
        FAILS until the tool is added.
        """
        result = mind_instance.get_current_weather(location="London")
        assert result.strip(), "Return value must not be empty"

    def test_result_references_location(self, mind_instance):
        """
        The result should reference the queried location so the user knows
        which city's weather is being reported.
        FAILS until the tool is added.
        """
        result = mind_instance.get_current_weather(location="Paris")
        assert "Paris" in result or "paris" in result.lower(), (
            "Result should reference the requested location"
        )

    def test_result_contains_weather_keywords(self, mind_instance):
        """
        Wish: 'current weather information'.
        The result should contain at least one weather-related keyword
        (temperature, conditions, humidity, wind, etc.).
        FAILS until the tool is added.
        """
        keywords = {
            "temperature", "temp", "°", "celsius", "fahrenheit",
            "humid", "wind", "cloud", "rain", "sun", "snow",
            "weather", "forecast", "condition",
        }
        result = mind_instance.get_current_weather(location="New York").lower()
        matched = {kw for kw in keywords if kw in result}
        assert matched, (
            f"Result contains no weather keywords. Got: {result[:200]}"
        )


# ---------------------------------------------------------------------------
# Test: edge cases / input validation
# ---------------------------------------------------------------------------

class TestGetCurrentWeatherEdgeCases:
    """The tool must handle unusual inputs gracefully."""

    @pytest.fixture
    def mind_instance(self):
        Mind = get_mind_class()
        try:
            return Mind()
        except TypeError:
            pytest.skip("Mind() requires constructor arguments — adjust fixture")

    def test_empty_location_does_not_crash(self, mind_instance):
        """
        Passing an empty string must not raise an unhandled exception.
        Typed errors (ValueError/TypeError) are acceptable; silent crashes are not.
        FAILS until the tool is added.
        """
        try:
            result = mind_instance.get_current_weather(location="")
            assert isinstance(result, str), "Should return a string even for empty input"
        except (ValueError, TypeError):
            pass  # Raising a typed error for bad input is acceptable

    def test_unknown_location_returns_graceful_message(self, mind_instance):
        """
        An unknown/nonsensical location should return an error/fallback message,
        not an unhandled exception.
        FAILS until the tool is added.
        """
        result = mind_instance.get_current_weather(location="Zzzznonexistentplace9999")
        assert isinstance(result, str), "Should return a string for unknown locations"
        assert result.strip(), "Should return a non-empty string for unknown locations"
