import pytest

from src import tools
from src.contracts import CreateServiceTask, MyOpenTasks


def test_my_open_tasks_returns_only_callers_room_tasks(monkeypatch):
    monkeypatch.setattr(tools, "SERVICE_TASKS", [])
    monkeypatch.setenv("STUMAROS_TODAY", "2026-10-15")

    tools.create_service_task(CreateServiceTask(department="housekeeping", task="Bring extra towels"), "204")
    tools.create_service_task(CreateServiceTask(department="maintenance", task="Fix AC"), "410")

    res = tools.my_open_tasks(MyOpenTasks(), "204")
    assert res.room == "204"
    assert len(res.tasks) == 1
    assert res.tasks[0].room == "204"
    assert res.tasks[0].task == "Bring extra towels"


def test_my_open_tasks_refuses_unverified_room(monkeypatch):
    monkeypatch.setenv("STUMAROS_TODAY", "2026-10-15")
    with pytest.raises(tools.ToolFailure, match="checked in today"):
        tools.my_open_tasks(MyOpenTasks(), "305")
