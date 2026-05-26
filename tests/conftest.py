"""Shared pytest fixtures for test-agent."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
_SRC = _ROOT / "src"

if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

os.chdir(str(_ROOT))
os.environ.setdefault("DEFAULT_PLUGIN_PATHS", json.dumps(["nodeai_plugins"]))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env", override=True)

from nodeai.api import Node

import agents.TestBot  # noqa: F401


@pytest.fixture(scope="session")
def mind():
    """Live TestBot Mind instance shared across all tests in the session."""
    node = Node(auto_start=True)
    m = node.get_mind("TestBot", "test_session")
    yield m
    node.shutdown(block=True)
