"""
Integration tests for the wished `get_current_datetime` tool on TestBot.

Wish: "add a tool that gets the current date and time"

Each test drives a live mind.think() conversation and is scored by
IntegrationTesterAgent's judge.  Tests MUST fail against the current agent
(the tool does not exist yet) and PASS once the tool is implemented.

Agent: TestBot
Mode: datetime_tool  (single capability mode)
Conversations: 6 per mode — happy_path_1/2, edge_case/2, bad_input, no_action
"""

import re
import pytest
from datetime import datetime


# ---------------------------------------------------------------------------
# Judge helpers embedded in expected_behavior strings
# The judge should treat these as pass/fail criteria.
# ---------------------------------------------------------------------------

DATETIME_PATTERN = re.compile(r"\d{4}[-/]\d{2}[-/]\d{2}|\d{1,2}:\d{2}")


# ---------------------------------------------------------------------------
# Mode: datetime_tool
# ---------------------------------------------------------------------------

class TestDatetimeToolConversations:
    """
    Six conversation scenarios that exercise the get_current_datetime tool.
    Each scenario provides a user message and expected_behavior for the judge.
    """

    # ------------------------------------------------------------------
    # happy_path_1 — canonical direct request
    # ------------------------------------------------------------------
    def test_happy_path_1_direct_request(self, mind):
        """
        User explicitly asks for the current date and time.

        Expected behavior:
        - Agent MUST call get_current_datetime tool.
        - Response MUST contain the current date (YYYY-MM-DD or similar).
        - Response MUST contain a time value (HH:MM at minimum).
        - Response tone should be helpful and direct.

        Fails now: tool does not exist; agent cannot fulfil request.
        """
        user_message = "What is the current date and time?"

        expected_behavior = (
            "The agent calls the get_current_datetime tool and returns a response "
            "containing today's date (including the year) and the current time "
            "(including at least hours and minutes). The response is a clear, "
            "natural-language sentence or structured string."
        )

        response = mind.think(user_message)

        current_year = str(datetime.now().year)
        assert current_year in response, (
            f"Response does not contain current year {current_year}: {response!r}\n"
            f"Expected behavior: {expected_behavior}"
        )
        assert DATETIME_PATTERN.search(response), (
            f"Response does not contain a recognisable date or time pattern: {response!r}\n"
            f"Expected behavior: {expected_behavior}"
        )

    # ------------------------------------------------------------------
    # happy_path_2 — alternative natural-language phrasing
    # ------------------------------------------------------------------
    def test_happy_path_2_natural_phrasing(self, mind):
        """
        User asks the same question with an alternative phrasing.

        Expected behavior:
        - Agent MUST call get_current_datetime tool.
        - Response contains the current date and time in any readable format.
        - Agent should NOT ask for clarification.

        Fails now: tool does not exist.
        """
        user_message = "Hey, can you tell me what time it is right now?"

        expected_behavior = (
            "The agent recognises this as a request for the current time, "
            "calls get_current_datetime, and replies with the current time "
            "(hours and minutes at minimum). It does NOT ask for clarification."
        )

        response = mind.think(user_message)

        assert DATETIME_PATTERN.search(response), (
            f"Response does not contain a time or date pattern: {response!r}\n"
            f"Expected behavior: {expected_behavior}"
        )
        clarification_phrases = ["what do you mean", "could you clarify", "please specify"]
        for phrase in clarification_phrases:
            assert phrase.lower() not in response.lower(), (
                f"Agent asked for clarification instead of answering: {response!r}"
            )

    # ------------------------------------------------------------------
    # edge_case — asking only for the date (not the time)
    # ------------------------------------------------------------------
    def test_edge_case_date_only_request(self, mind):
        """
        User asks only for the date, not the time.

        Expected behavior:
        - Agent calls get_current_datetime (still the correct tool).
        - Response contains at minimum the current date.
        - It is acceptable (but not required) to include the time as well.

        Fails now: tool does not exist.
        """
        user_message = "What is today's date?"

        expected_behavior = (
            "The agent calls get_current_datetime and returns the current date "
            "(day, month, year). Including the time is acceptable but not required."
        )

        response = mind.think(user_message)

        current_year = str(datetime.now().year)
        assert current_year in response, (
            f"Response does not contain current year {current_year}: {response!r}\n"
            f"Expected behavior: {expected_behavior}"
        )

    # ------------------------------------------------------------------
    # edge_case_2 — asking for the day of the week
    # ------------------------------------------------------------------
    def test_edge_case_2_day_of_week(self, mind):
        """
        User asks what day of the week it is — a derived fact from the date.

        Expected behavior:
        - Agent calls get_current_datetime.
        - Response names the correct day of the week (Monday–Sunday).
        - Derived from the real current date, not hardcoded.

        Fails now: tool does not exist.
        """
        user_message = "What day of the week is it today?"

        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        current_day = datetime.now().strftime("%A").lower()

        expected_behavior = (
            f"The agent calls get_current_datetime and responds with the correct "
            f"day of the week ({current_day.capitalize()}). "
            "The answer must be derived from real current time, not hardcoded."
        )

        response = mind.think(user_message)

        response_lower = response.lower()
        assert any(day in response_lower for day in days), (
            f"Response does not contain a day-of-week name: {response!r}\n"
            f"Expected behavior: {expected_behavior}"
        )
        assert current_day in response_lower, (
            f"Response contains a day name but not the correct one ({current_day}): "
            f"{response!r}\n"
            f"Expected behavior: {expected_behavior}"
        )

    # ------------------------------------------------------------------
    # bad_input — asking about a future or past date (out of scope)
    # ------------------------------------------------------------------
    def test_bad_input_historical_date_request(self, mind):
        """
        User asks about a date in the future — the tool only returns the
        CURRENT datetime and cannot answer questions about other dates.

        Expected behavior:
        - Agent MAY call get_current_datetime to ground itself in the present.
        - Agent MUST acknowledge it cannot provide information about future dates.
        - Agent MUST NOT hallucinate a specific future date as fact.
        - Response should be clear and helpful about the limitation.

        Fails now: tool does not exist (and agent may hallucinate instead).
        """
        user_message = "What will the date be exactly 100 days from now? Give me the exact date."

        expected_behavior = (
            "The agent either (a) uses get_current_datetime and computes the future date "
            "correctly, or (b) clearly states that it can report the current date and time "
            "but notes any uncertainty about date arithmetic. "
            "It MUST NOT confidently state a wrong future date without tool data."
        )

        response = mind.think(user_message)

        # The response must either contain a computed future date or a clear acknowledgement
        future_year_mentioned = str(datetime.now().year) in response or str(datetime.now().year + 1) in response
        limitation_acknowledged = any(
            phrase in response.lower()
            for phrase in ["current", "today", "right now", "at the moment", "as of"]
        )

        assert future_year_mentioned or limitation_acknowledged, (
            f"Response neither grounds itself in current time nor acknowledges limitation: "
            f"{response!r}\n"
            f"Expected behavior: {expected_behavior}"
        )

    # ------------------------------------------------------------------
    # no_action — unrelated request, tool should NOT be called
    # ------------------------------------------------------------------
    def test_no_action_unrelated_greeting_request(self, mind):
        """
        User asks for a greeting — completely unrelated to date/time.
        The get_current_datetime tool should NOT be invoked.

        Expected behavior:
        - Agent uses the `greet` tool (existing) to respond.
        - Response is a friendly greeting.
        - Response does NOT include date/time information unprompted.
        - get_current_datetime is NOT called.

        Fails now: if the tool doesn't exist, no-action behaviour may still be
        incorrect (agent may try to evolve instead of just greeting).
        """
        user_message = "Please greet me!"

        expected_behavior = (
            "The agent responds with a friendly greeting (uses the greet tool). "
            "It does NOT mention the current date or time, as none was requested. "
            "The get_current_datetime tool is NOT called."
        )

        response = mind.think(user_message)

        # Should be a greeting response
        greeting_words = ["hello", "hi", "hey", "greetings", "welcome"]
        assert any(word in response.lower() for word in greeting_words), (
            f"Response does not appear to be a greeting: {response!r}\n"
            f"Expected behavior: {expected_behavior}"
        )

        # Should NOT contain unsolicited date/time info
        current_year = str(datetime.now().year)
        has_time = DATETIME_PATTERN.search(response)
        has_year = current_year in response
        assert not (has_time or has_year), (
            f"Response unexpectedly contains date/time info in a greeting context: "
            f"{response!r}\n"
            f"Expected behavior: {expected_behavior}"
        )


# ---------------------------------------------------------------------------
# Fixture stub — replace with project's real mind fixture if available
# ---------------------------------------------------------------------------

@pytest.fixture
def mind():
    """
    Minimal fixture that instantiates a TestBot Mind for live integration tests.
    Replace this with the project's canonical mind fixture once discovered.

    The fixture is intentionally lightweight so tests fail fast (tool missing)
    rather than failing on fixture setup.
    """
    import importlib
    mod = importlib.import_module("agents.TestBot.main")
    Mind = getattr(mod, "Mind", None)
    assert Mind is not None, (
        "Could not import Mind from agents.TestBot.main. "
        "Check that the agent module is correctly structured."
    )

    class _MindProxy:
        """Thin wrapper that exposes mind.think(message) -> str."""

        def __init__(self):
            self._mind = Mind()

        def think(self, message: str) -> str:
            # Try the framework's think/run/chat method
            for method_name in ("think", "run", "chat", "respond", "__call__"):
                fn = getattr(self._mind, method_name, None)
                if callable(fn) and method_name != "__call__":
                    return str(fn(message))
                elif method_name == "__call__" and callable(self._mind):
                    return str(self._mind(message))
            raise NotImplementedError(
                "Could not find a think/run/chat method on Mind. "
                "Update the fixture for this project's convention."
            )

    return _MindProxy()
