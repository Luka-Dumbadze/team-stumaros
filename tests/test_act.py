"""The function-calling loop: offered? valid? then run, with the room from the server."""
import json

import pytest

from src import tools
from src.act import MAX_ROUNDS, act, call_tool
from src.contracts import LookupPolicy
from src.tools import Tool, tools_for


def call(name, **args):
    return {"id": "c1", "name": name, "arguments": json.dumps(args)}


def test_valid_call_runs_and_returns_data():
    out = call_tool(call("lookup_policy", section="wifi"), tools_for(None), None)
    assert out["ok"] and "StumarGuest" in out["result"]["text"]


def test_invalid_arguments_never_reach_the_tool(monkeypatch):
    ran = []
    monkeypatch.setattr(tools.prefilter, "load_guide", lambda: ran.append(1) or [])
    out = call_tool(call("lookup_policy", section="../../.env"), tools_for(None), None)
    assert not out["ok"] and out["error"].startswith("invalid arguments: section") and ran == []


def test_a_tool_not_offered_is_not_run(monkeypatch):
    ran = []
    private = Tool("my_open_tasks", LookupPolicy, lambda args, room: ran.append(room), needs_room=True)
    monkeypatch.setitem(tools.TOOLS, "my_open_tasks", private)
    assert "my_open_tasks" not in tools_for(None) and "my_open_tasks" in tools_for("204")
    out = call_tool(call("my_open_tasks", section="pool"), tools_for(None), None)
    assert not out["ok"] and "no tool named 'my_open_tasks'" in out["error"] and ran == []


def test_a_tool_that_does_not_exist_is_not_run():
    assert not call_tool(call("delete_all_tasks"), tools_for("204"), "204")["ok"]


def test_model_cannot_choose_the_room():
    out = call_tool(call("lookup_policy", section="pool", room="305"), tools_for("204"), "204")
    assert not out["ok"] and "room" in out["error"] and "Extra inputs are not permitted" in out["error"]


def test_room_tools_get_the_room_from_the_server_not_the_model(monkeypatch):
    seen = []
    private = Tool("my_open_tasks", LookupPolicy,
                   lambda args, room: seen.append(room) or tools.PolicySection(section=args.section, text="ok"),
                   needs_room=True)
    monkeypatch.setitem(tools.TOOLS, "my_open_tasks", private)
    assert call_tool(call("my_open_tasks", section="pool"), tools_for("204"), "204")["ok"] and seen == ["204"]


def test_expected_failure_goes_back_as_a_message(monkeypatch):
    monkeypatch.setattr(tools.prefilter, "load_guide", lambda: [])
    out = call_tool(call("lookup_policy", section="pool"), tools_for(None), None)
    assert not out["ok"] and "front desk" in out["error"]


def test_every_call_writes_one_log_line_with_a_hashed_room(tool_log):
    call_tool(call("lookup_policy", section="pool"), tools_for("204"), "204")
    call_tool(call("lookup_policy", section="spa"), tools_for(None), None)
    lines = [json.loads(x) for x in tool_log.read_text().splitlines()]
    assert [(x["tool"], x["ok"]) for x in lines] == [("lookup_policy", True), ("lookup_policy", False)]
    assert lines[0]["room"] == tools.room_key("204") and "204" not in json.dumps(lines[0]["room"])
    assert lines[1]["room"] is None


def test_end_to_end_offline_answer(_usage_log_in_tmp):
    reply = act("What time is breakfast?")
    assert reply.status == "answered" and "07:00-10:30" in reply.text and reply.calls[0]["ok"]
    usage = [json.loads(x) for x in _usage_log_in_tmp.read_text().splitlines()]
    assert [(u["attempt"], u["status"], u["session_id"]) for u in usage] == [(1, "success", "act"), (2, "success", "act")]
    assert len({u["request_id"] for u in usage}) == 1


def test_unanswerable_question_offers_the_front_desk():
    reply = act("Do you have a free airport shuttle?")
    assert reply.calls == [] and "front desk" in reply.text


def test_the_model_reads_the_error_and_can_repair():
    turns = []

    def model(messages, schemas):
        turns.append(messages[-1]["role"])
        if len(turns) == 1:
            return {"content": None, "tool_calls": [call("lookup_policy", section="Pool")]}
        if len(turns) == 2:
            assert "invalid arguments" in json.loads(messages[-1]["content"])["error"]
            return {"content": None, "tool_calls": [call("lookup_policy", section="pool")]}
        return {"content": "The pool is open 08:00-22:00.", "tool_calls": []}

    reply = act("When does the pool open?", llm=model)
    assert reply.text == "The pool is open 08:00-22:00." and [c["ok"] for c in reply.calls] == [False, True]


def test_loop_stops_after_the_budget():
    calls = []

    def stubborn(messages, schemas):
        calls.append(1)
        return {"content": None, "tool_calls": [call("lookup_policy", section="nope")]}

    reply = act("When does the pool open?", llm=stubborn)
    assert reply.status == "stopped" and len(reply.calls) == MAX_ROUNDS == len(calls) == 3


def test_model_failure_stops_cleanly_without_a_stack_trace():
    def down(messages, schemas):
        raise RuntimeError("HTTP 503 with internal details")

    reply = act("When is breakfast?", llm=down)
    assert reply.status == "failed" and "503" not in reply.text and "front desk" in reply.text


def test_reasoning_details_and_extra_content_are_echoed_back():
    seen = []

    def model(messages, schemas):
        seen.append(messages)
        if len(seen) == 1:
            c = {**call("lookup_policy", section="pool"), "extra_content": {"google": {"thought_signature": "sig"}}}
            return {"content": None, "reasoning_details": [{"type": "reasoning.encrypted", "data": "x"}],
                    "tool_calls": [c]}
        return {"content": "ok", "tool_calls": []}

    act("Pool?", llm=model)
    assistant = [m for m in seen[1] if m["role"] == "assistant"][0]
    assert assistant["reasoning_details"] == [{"type": "reasoning.encrypted", "data": "x"}]
    assert assistant["tool_calls"][0]["extra_content"] == {"google": {"thought_signature": "sig"}}


def test_live_function_calling_request_shape(monkeypatch):
    """No network: the OpenAI SDK call is replaced, so we can see exactly what would be sent."""
    pytest.importorskip("openai")
    from types import SimpleNamespace as NS

    from src.llm import make_client
    client = make_client(env={"GEMINI_API_KEY": "g-test"})
    sent = {}

    def fake_create(**kwargs):
        sent.update(kwargs)
        tc = NS(id="t1", function=NS(name="lookup_policy", arguments='{"section": "pool"}'),
                model_extra={"extra_content": {"google": {"thought_signature": "sig"}}})
        return NS(choices=[NS(message=NS(content=None, tool_calls=[tc], model_extra={}))],
                  usage=NS(prompt_tokens=300, completion_tokens=12, total_tokens=312))

    client._client.chat.completions.create = fake_create
    msg, usage = client.complete_tools([{"role": "user", "content": "pool?"}], [tools.TOOLS["lookup_policy"].schema()])
    assert sent["tool_choice"] == "auto" and "response_format" not in sent and sent["reasoning_effort"] == "none"
    assert msg["tool_calls"][0]["extra_content"] == {"google": {"thought_signature": "sig"}}
    assert (usage.prompt_tokens, usage.completion_tokens) == (300, 12)


def test_post_act_takes_the_room_from_the_header_and_verifies_it(monkeypatch):
    from fastapi.testclient import TestClient

    from src import app as app_module
    seen = []
    monkeypatch.setattr(app_module, "act", lambda q, room: seen.append(room) or act("Wi-Fi?"))
    client = TestClient(app_module.app)
    for header in ({"X-Room": "204"}, {"X-Room": "305"}, {}):
        assert client.post("/act", json={"question": "Wi-Fi?"}, headers=header).status_code == 200
    assert seen == ["204", None, None]  # 305 checked out: a visitor, whatever the header claims
