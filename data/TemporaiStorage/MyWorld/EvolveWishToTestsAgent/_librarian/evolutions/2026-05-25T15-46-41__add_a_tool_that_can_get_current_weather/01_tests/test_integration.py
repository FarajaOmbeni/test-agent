"""
Integration tests for the `get_current_weather` tool on TestBot.

Wish: add a tool that can get current weather information for a given location
These conversations are designed to FAIL against the current agent (tool does not exist).
They are scored by IntegrationTesterAgent's judge.

Mode: weather_lookup (single tool-level blast radius)
6 conversations: happy_path_1, happy_path_2, edge_case, edge_case_2, bad_input, no_action
"""
import pytest

WISH = "add a tool that can get current weather information for a given location"
AGENT = "TestBot"

# ---------------------------------------------------------------------------
# Conversation definitions (used by judge + pytest harness)
# ---------------------------------------------------------------------------

CONVERSATIONS = [
    {
        "id": "weather_lookup__happy_path_1",
        "mode": "weather_lookup",
        "user_message": "What's the current weather in London?",
        "expected_behavior": (
            "The agent calls get_current_weather(location='London') and returns "
            "a response that includes current weather conditions and/or temperature for London."
        ),
        "pass_criteria": [
            "Agent uses the get_current_weather tool",
            "Response mentions London",
            "Response includes weather information (temperature, conditions, etc.)",
        ],
        "fail_if": [
            "Agent says it cannot check the weather",
            "Agent uses a different/unrelated tool",
            "Response contains no weather data",
        ],
    },
    {
        "id": "weather_lookup__happy_path_2",
        "mode": "weather_lookup",
        "user_message": "Tell me the current weather for Tokyo, Japan.",
        "expected_behavior": (
            "The agent calls get_current_weather(location='Tokyo, Japan') or similar "
            "and returns weather information for Tokyo."
        ),
        "pass_criteria": [
            "Agent uses the get_current_weather tool",
            "Response mentions Tokyo or Japan",
            "Response includes weather data",
        ],
        "fail_if": [
            "Agent says it cannot check the weather",
            "Response contains no weather data",
        ],
    },
    {
        "id": "weather_lookup__edge_case",
        "mode": "weather_lookup",
        "user_message": "What's the weather like in Reykjavik right now?",
        "expected_behavior": (
            "The agent calls get_current_weather for an unusual/less-common city "
            "and returns a meaningful response (even if it's an error/fallback message). "
            "Agent must not refuse to try."
        ),
        "pass_criteria": [
            "Agent attempts to use get_current_weather tool",
            "Response references Reykjavik",
            "Agent does not flat-out refuse",
        ],
        "fail_if": [
            "Agent says it cannot check weather at all",
            "Agent returns a completely generic response with no weather attempt",
        ],
    },
    {
        "id": "weather_lookup__edge_case_2",
        "mode": "weather_lookup",
        "user_message": "How's the weather?",
        "expected_behavior": (
            "The user asks for weather without specifying a location. "
            "The agent should ask for clarification about which location, "
            "rather than guessing or refusing entirely."
        ),
        "pass_criteria": [
            "Agent asks the user to specify a location",
            "Agent does not crash or give an empty response",
        ],
        "fail_if": [
            "Agent calls get_current_weather with an empty or nonsensical location without asking",
            "Agent says it cannot help at all without any follow-up question",
        ],
    },
    {
        "id": "weather_lookup__bad_input",
        "mode": "weather_lookup",
        "user_message": "Get weather for 00000.",
        "expected_behavior": (
            "The user passes a numeric zip code / clearly invalid location. "
            "The agent should handle gracefully — either attempt the lookup and "
            "return an informative error, or ask for clarification. Must not crash."
        ),
        "pass_criteria": [
            "Agent does not crash",
            "Agent returns a non-empty string response",
            "Response is informative (error message or clarification request)",
        ],
        "fail_if": [
            "Agent raises an unhandled exception",
            "Agent silently returns an empty response",
        ],
    },
    {
        "id": "weather_lookup__no_action",
        "mode": "weather_lookup",
        "user_message": "Tell me a joke about clouds.",
        "expected_behavior": (
            "The user asks for a joke, not actual weather data. "
            "The agent should NOT invoke get_current_weather. "
            "It should respond with a joke or a lighthearted response."
        ),
        "pass_criteria": [
            "Agent does NOT call get_current_weather",
            "Agent responds with a joke or creative content about clouds",
        ],
        "fail_if": [
            "Agent calls get_current_weather unnecessarily",
            "Agent refuses to respond at all",
        ],
    },
]


# ---------------------------------------------------------------------------
# Pytest harness — runs conversations via mind.think()
# ---------------------------------------------------------------------------

try:
    from agents.TestBot.main import Mind
    MIND_AVAILABLE = True
except ImportError:
    MIND_AVAILABLE = False


@pytest.mark.skipif(not MIND_AVAILABLE, reason="TestBot Mind not importable")
class TestWeatherLookupIntegration:
    """
    Integration tests for the weather_lookup mode.
    Sends live messages to the agent and asserts on response content.
    ALL tests MUST fail until get_current_weather is implemented.
    """

    @pytest.fixture(scope="class")
    def mind(self):
        try:
            return Mind()
        except Exception as e:
            pytest.skip(f"Could not instantiate Mind: {e}")

    # --- happy_path_1 ---

    def test_happy_path_1_weather_london(self, mind):
        """
        happy_path_1: 'What's the current weather in London?'
        Expected: agent uses get_current_weather and returns weather data for London.
        FAILS until get_current_weather tool is added.
        """
        result = mind.think("What's the current weather in London?")
        response = result if isinstance(result, str) else str(result)

        assert "London" in response or "london" in response.lower(), (
            f"Response does not mention London. Got: {response[:300]}"
        )
        weather_keywords = {"weather", "temperature", "°", "rain", "cloud", "sun", "wind", "humid", "°c", "°f"}
        assert any(kw in response.lower() for kw in weather_keywords), (
            f"Response contains no weather keywords. Got: {response[:300]}"
        )

    # --- happy_path_2 ---

    def test_happy_path_2_weather_tokyo(self, mind):
        """
        happy_path_2: 'Tell me the current weather for Tokyo, Japan.'
        Expected: agent uses get_current_weather and returns weather data for Tokyo.
        FAILS until get_current_weather tool is added.
        """
        result = mind.think("Tell me the current weather for Tokyo, Japan.")
        response = result if isinstance(result, str) else str(result)

        assert (
            "Tokyo" in response or "Japan" in response
            or "tokyo" in response.lower()
        ), f"Response does not mention Tokyo/Japan. Got: {response[:300]}"

        weather_keywords = {"weather", "temperature", "°", "rain", "cloud", "sun", "wind", "humid", "°c", "°f"}
        assert any(kw in response.lower() for kw in weather_keywords), (
            f"Response contains no weather keywords. Got: {response[:300]}"
        )

    # --- edge_case ---

    def test_edge_case_weather_reykjavik(self, mind):
        """
        edge_case: 'What's the weather like in Reykjavik right now?'
        Expected: agent attempts the lookup for an unusual city; non-empty response.
        FAILS until get_current_weather tool is added.
        """
        result = mind.think("What's the weather like in Reykjavik right now?")
        response = result if isinstance(result, str) else str(result)

        assert response.strip(), "Response should not be empty"
        # Should not flat-out refuse
        hard_refusals = ["i cannot check", "i can't check", "no weather tool", "unable to access weather"]
        assert not any(phrase in response.lower() for phrase in hard_refusals), (
            f"Agent appears to refuse the weather request entirely: {response[:300]}"
        )

    # --- edge_case_2 ---

    def test_edge_case_2_no_location_asks_for_clarification(self, mind):
        """
        edge_case_2: 'How's the weather?'
        Expected: agent asks user to specify a location; does not crash or silently fail.
        FAILS until get_current_weather tool is added (agent can't know to ask).
        """
        result = mind.think("How's the weather?")
        response = result if isinstance(result, str) else str(result)

        assert response.strip(), "Response should not be empty"
        clarification_phrases = ["which", "where", "location", "city", "place", "specify", "what location"]
        assert any(phrase in response.lower() for phrase in clarification_phrases), (
            f"Agent should ask for location clarification. Got: {response[:300]}"
        )

    # --- bad_input ---

    def test_bad_input_numeric_zip_code(self, mind):
        """
        bad_input: 'Get weather for 00000.'
        Expected: agent handles gracefully — informative error or asks for clarification.
        FAILS until get_current_weather tool is added.
        """
        result = mind.think("Get weather for 00000.")
        response = result if isinstance(result, str) else str(result)

        assert response.strip(), "Response should not be empty for bad input"
        assert isinstance(response, str), "Response must be a string"

    # --- no_action ---

    def test_no_action_joke_about_clouds(self, mind):
        """
        no_action: 'Tell me a joke about clouds.'
        Expected: agent does NOT call get_current_weather; responds with a joke.
        Verifies the tool is not over-triggered on cloud/weather-adjacent language.
        """
        result = mind.think("Tell me a joke about clouds.")
        response = result if isinstance(result, str) else str(result)

        assert response.strip(), "Response should not be empty"
        # Should be creative/joke content, not actual weather data
        weather_data_indicators = [
            "temperature is", "°C", "°F", "humidity:", "wind speed",
            "current conditions", "feels like"
        ]
        assert not any(ind in response for ind in weather_data_indicators), (
            f"Agent should not return weather data for a joke request. Got: {response[:300]}"
        )
