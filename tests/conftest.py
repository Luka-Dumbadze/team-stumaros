"""Every test runs offline: no key, no network, no cost. Logs go to a temp folder.
Today is pinned to 2026-10-15, the day the mock stays in data/active_rooms.json are valid."""
import pytest

from src import tools


@pytest.fixture(autouse=True)
def _usage_log_in_tmp(tmp_path, monkeypatch):
    """Keep the suite out of the real logs/, force the offline mock client, and pin the date."""
    log = tmp_path / "usage.jsonl"
    monkeypatch.setenv("STUMAROS_USAGE_LOG", str(log))
    monkeypatch.setenv("STUMAROS_TOOL_LOG", str(tmp_path / "tools.jsonl"))
    monkeypatch.setenv("STUMAROS_TODAY", "2026-10-15")
    for var in ("GEMINI_API_KEY", "OPENROUTER_API_KEY", "STUMAROS_ROOM"):
        monkeypatch.delenv(var, raising=False)
    # Service tasks live in process memory (AGENTS.md: no storage files); every test starts with none.
    monkeypatch.setattr(tools, "SERVICE_TASKS", [], raising=False)
    return log


@pytest.fixture
def tool_log(tmp_path):
    return tmp_path / "tools.jsonl"
