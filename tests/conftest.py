"""Keep the test suite from writing to the real logs/usage.jsonl."""
import pytest


@pytest.fixture(autouse=True)
def _usage_log_in_tmp(tmp_path, monkeypatch):
    log = tmp_path / "usage.jsonl"
    monkeypatch.setenv("STUMAROS_USAGE_LOG", str(log))
    return log
