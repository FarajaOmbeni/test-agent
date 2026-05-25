# Plan: add a tool that can get current weather information for a given location

## Wish
Add a `get_current_weather(location)` tool to TestBot that fetches live weather
from the wttr.in free public API (stdlib-only, no new dependencies).

## Capability gaps consulted
None — TestBot has no tracked gaps in the refactor pipeline.

## Phases

### Phase 01 — `01_add-get-current-weather-tool`
Single self-contained change to `src/agents/TestBot/main.py`:
- Add `urllib.request/parse/error` imports
- Add `get_current_weather` tool function (after `get_current_datetime`, before `evolve_capability`)
- Expose on `Mind` class
- Register in `TOOLS` list

## End-to-end flow for EvolveCodeWriterAgent
1. Read `src/agents/TestBot/main.py`
2. Follow `01_add-get-current-weather-tool/prompt_for_claude_code.txt` exactly
3. Run `minimal_tests_to_pass.txt` to verify all 4 gates pass
4. No other files need to change
