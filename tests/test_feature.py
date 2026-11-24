"""Unit tests for src/ (promoted from hw1/Luka-Dumbadze/src/test_feature.py). Offline: no API key needed."""
import json
from datetime import date

import pytest

from src import prefilter
from src.llm import (MAX_CALLS, MAX_INPUT_TOKENS, PROVIDERS, Completion, MockClient, OpenAICompatibleClient,
                  TransientError, build_messages, estimate_prompt_tokens, make_client)
from src.pipeline import ESCALATE_EN, triage

TODAY = date(2026, 10, 15)
GUIDE = prefilter.load_guide()
ROOMS = prefilter.load_rooms()


class ScriptedClient:
    """Returns queued responses in order; an Exception in the queue is raised instead."""
    mode = "scripted"

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def complete(self, messages):
        self.calls.append(messages)
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        text = r if isinstance(r, str) else json.dumps(r, ensure_ascii=False)
        return Completion(text, 100, 20, estimated=False)


def model_json(reply="OK.", tasks=(), intent="service", cited=(), clarify=False):
    return {"intent": intent, "reply": reply, "tasks": list(tasks), "cited_sections": list(cited),
            "needs_clarification": clarify}


def run(message, client, room=None):
    return triage(message, client, today=TODAY, payload_room=room, sleep=lambda s: None)


# --- Context budget (criterion 3) ---------------------------------------------------------------

def test_prefilter_keeps_only_matching_sections():
    ids = [s["id"] for s in prefilter.select_sections("What time does breakfast end?", GUIDE)]
    assert ids == ["breakfast"]


def test_prefilter_matches_georgian_stems_and_caps_at_three():
    ids = [s["id"] for s in prefilter.select_sections("ბალიში, საუზმე, აუზი, ვაიფაი და პარკინგი?", GUIDE)]
    assert len(ids) == prefilter.MAX_SECTIONS


def test_prefilter_does_not_match_door_stem_inside_good():
    # "კარგი" (good) contains "კარ" (door stem); must not pull in the maintenance section.
    assert prefilter.select_sections("ყველაფერი კარგია, მადლობა", GUIDE) == []


def test_prefilter_georgian_stem_matches_only_at_word_start():
    # Regression (golden case 1): "აუზ" (pool) is a substring of "საუზმე" (breakfast).
    ids = [s["id"] for s in prefilter.select_sections("ოთახი 204-ში 2 ბალიში. როდემდეა საუზმე?", GUIDE)]
    assert sorted(ids) == ["breakfast", "housekeeping"]


def test_prompt_contains_only_selected_sections_and_no_other_guests():
    msg = "Can we get 2 extra pillows in room 204?"
    sections = prefilter.select_sections(msg, GUIDE)
    prompt = json.dumps(build_messages(msg, sections, "204", "valid"), ensure_ascii=False)
    assert "Breakfast is served" not in prompt and "rooftop pool" not in prompt
    for record in ROOMS:
        assert record["guest_name"] not in prompt  # names are never sent, not even the guest's own
    assert estimate_prompt_tokens(build_messages(msg, sections, "204", "valid")) < MAX_INPUT_TOKENS


def test_over_budget_prompt_is_refused_before_any_call():
    huge_guide = [{"id": f"s{i}", "keywords": ["pool"], "text": "x" * 4000} for i in range(3)]
    client = ScriptedClient()
    result = triage("pool?", client, today=TODAY, guide=huge_guide, rooms=ROOMS)
    assert client.calls == [] and result.tasks == []
    assert any(e.startswith("budget:") for e in result.guardrail_events)


def test_georgian_text_estimates_heavier_than_english():
    assert prefilter.estimate_tokens("სტუმრის რეგისტრაცია") > 2 * prefilter.estimate_tokens("guest registration")


# --- Room gate (criterion 2) --------------------------------------------------------------------

@pytest.mark.parametrize("room,status", [
    ("204", "valid"), ("999", "unknown"), ("305", "not_checked_in"), ("112", "not_checked_in"),
    ("501", "outside_stay_dates"), (None, "missing"),
])
def test_validate_room(room, status):
    assert prefilter.validate_room(room, ROOMS, TODAY)[1] == status


def test_conflicting_payload_and_message_rooms_are_not_trusted():
    assert prefilter.resolve_room("204", "send towels to room 410") == (None, "conflicting_rooms")


@pytest.mark.parametrize("room", ["999", "305", "501", None])
def test_tasks_dropped_for_invalid_room_even_if_model_proposes_them(room):
    client = ScriptedClient(model_json("Sure, towels are on the way!",
                                       [{"department": "housekeeping", "priority": "normal", "task": "2 towels"}]))
    result = run("Please send 2 towels", client, room=room)
    assert result.tasks == [] and result.room_validated is False
    assert "room number" in result.reply
    assert any(e.startswith("room_gate: dropped") for e in result.guardrail_events)


def test_valid_room_task_gets_room_from_code_not_model():
    client = ScriptedClient(model_json(tasks=[{"department": "housekeeping", "priority": "normal",
                                              "task": "Deliver 2 extra pillows"}]))
    result = run("Can we get 2 extra pillows in room 204?", client)
    assert [t.room for t in result.tasks] == ["204"] and result.room_validated


# --- Priority overrides -------------------------------------------------------------------------

def test_ac_issue_forced_urgent_and_supplies_never_urgent():
    client = ScriptedClient(model_json(tasks=[
        {"department": "maintenance", "priority": "low", "task": "AC not cooling"},
        {"department": "housekeeping", "priority": "urgent", "task": "Bring extra towels"}]))
    result = run("room 204: AC is broken, also towels", client)
    assert [t.priority for t in result.tasks] == ["urgent", "normal"]


# --- Strict output + call budget (criterion 1) --------------------------------------------------

def test_malformed_json_gets_one_corrective_retry():
    client = ScriptedClient("Sure! here you go", model_json("Breakfast is 07:00-10:30.", intent="question",
                                                         cited=["breakfast"]))
    result = run("When is breakfast?", client)
    assert result.usage.attempts == 2 and "07:00" in result.reply
    assert "not valid for the required schema" in client.calls[1][-1]["content"]


def test_second_schema_failure_stops_and_falls_back():
    client = ScriptedClient("nope", {"intent": "service"}, model_json())
    result = run("towels to room 204", client)
    assert result.usage.attempts == 2 and result.tasks == []
    assert "front desk" in result.reply


def test_invalid_department_is_a_schema_error():
    client = ScriptedClient(model_json(tasks=[{"department": "spa", "priority": "normal", "task": "massage"}]),
                            model_json(tasks=[{"department": "front_desk", "priority": "normal", "task": "Book spa"}]))
    result = run("room 204 book a massage", client)
    assert result.usage.attempts == 2 and result.tasks[0].department == "front_desk"


def test_transient_errors_capped_at_three_calls():
    client = ScriptedClient(*[TransientError("HTTP 503")] * 5)
    result = run("When is breakfast?", client)
    assert len(client.calls) == MAX_CALLS and result.usage.attempts == MAX_CALLS
    assert result.tasks == [] and "front desk" in result.reply


def test_temperature_above_ceiling_rejected():
    with pytest.raises(ValueError):
        OpenAICompatibleClient(PROVIDERS[0], "not-a-key", temperature=0.7)


# --- Provider selection (no network: constructing a client sends nothing) ------------------------

def test_no_keys_or_empty_keys_fall_back_to_mock():
    assert make_client(env={}).mode == "mock"
    assert make_client(env={"GEMINI_API_KEY": "", "OPENROUTER_API_KEY": "  "}).mode == "mock"


def test_gemini_key_wins_over_openrouter_key():
    pytest.importorskip("openai")
    client = make_client(env={"GEMINI_API_KEY": "g-test", "OPENROUTER_API_KEY": "o-test"})
    assert client.label == "gemini:gemini-3.8-flash"
    assert str(client._client.base_url) == "https://generativelanguage.googleapis.com/v1beta/openai/"
    assert client._client.max_retries == 0  # SDK retries off: the 3-call cap is ours


def test_gemini_request_disables_thinking_and_keeps_output_budget():
    # Regression (live, 2026-10-15): default thinking spent the 300-token budget and truncated the JSON.
    pytest.importorskip("openai")
    from types import SimpleNamespace as NS
    client = make_client(env={"GEMINI_API_KEY": "g-test"})
    sent = {}

    def fake_create(**kwargs):
        sent.update(kwargs)
        return NS(choices=[NS(message=NS(content=json.dumps(model_json())), finish_reason="stop")],
                  usage=NS(prompt_tokens=463, completion_tokens=50, total_tokens=513))

    client._client.chat.completions.create = fake_create
    completion = client.complete([{"role": "user", "content": "hi"}])
    assert sent["reasoning_effort"] == "none" and sent["max_tokens"] == 300 and sent["temperature"] <= 0.2
    assert sent["response_format"] == {"type": "json_object"}
    assert (completion.prompt_tokens, completion.total_tokens, completion.estimated) == (463, 513, False)


def test_truncated_output_is_reported_as_truncation():
    class TruncatingClient:
        mode = "scripted"

        def complete(self, messages):
            return Completion('{\n  "intent', 973, 5, estimated=False, total_tokens=1270, finish_reason="length")

    result = run("When is breakfast?", TruncatingClient())
    assert result.usage.attempts == 2 and result.tasks == []
    assert any("truncated at max_tokens=300" in e for e in result.guardrail_events)
    assert result.usage.total_tokens == 2540  # hidden tokens are surfaced, not lost


def test_timed_out_attempt_does_not_mark_real_usage_as_estimated():
    client = ScriptedClient(TransientError("APITimeoutError"),
                            model_json("Breakfast is 07:00-10:30.", intent="question", cited=["breakfast"]))
    result = run("When is breakfast?", client)
    assert result.usage.attempts == 2 and result.usage.tokens_estimated is False
    assert "attempt 1 failed: transient: APITimeoutError" in result.guardrail_events


def test_bench_percentiles_and_split_on_live_numbers():
    from src.bench import percentile, summarize
    ok = [7.325, 5.325, 3.769, 8.356, 2.71, 6.165]  # successful answers, live benchmark 2026-10-15
    rows = [{"latency_s": x, "model_ok": True} for x in ok] + \
           [{"latency_s": x, "model_ok": False} for x in (3.162, 2.336, 2.624, 2.288)]  # 429 fallbacks
    assert (percentile(ok, 50), percentile(ok, 95)) == (5.325, 8.356)
    assert summarize(rows)["p50_s"] == 3.162  # what the original summary printed: flattered by fast failures
    assert summarize([r for r in rows if r["model_ok"]])["within_sla"] == 0


def test_openrouter_used_when_gemini_key_missing_and_model_override_applies():
    pytest.importorskip("openai")
    client = make_client(env={"OPENROUTER_API_KEY": "o-test"})
    assert client.label == "openrouter:google/gemini-3.8-flash"
    assert str(client._client.base_url).startswith("https://openrouter.ai/api/v1")
    assert make_client("gemini-3.5-flash", env={"GEMINI_API_KEY": "g-test"}).label == "gemini:gemini-3.5-flash"


# --- Grounding (criterion 4) --------------------------------------------------------------------

def test_invented_time_replaces_reply():
    client = ScriptedClient(model_json("The pool is open until 24:00 for you!", intent="question", cited=["pool"]))
    result = run("Can I swim at 23:30 tonight?", client)
    assert result.reply == ESCALATE_EN
    assert any("unsupported numbers ['24']" in e for e in result.guardrail_events)


def test_numbers_from_guest_message_are_allowed():
    client = ScriptedClient(model_json("Sorry, at 23:30 the pool is closed; it is open 08:00-22:00.",
                                       intent="question", cited=["pool"]))
    assert "23:30" in run("Can I swim at 23:30 tonight?", client).reply


def test_unanswerable_question_gets_escalation():
    client = ScriptedClient(model_json("Let me check that.", intent="question"))
    result = run("Do you have an airport shuttle?", client)
    assert result.sections_sent == [] and "front desk" in result.reply


# --- Golden cases through the mock client -------------------------------------------------------

def test_golden_georgian_happy_path():
    result = run("გამარჯობა! ოთახი 204-ში 2 დამატებითი ბალიში გვჭირდება. როდემდეა საუზმე?", MockClient())
    assert [(t.room, t.department, t.priority) for t in result.tasks] == [("204", "housekeeping", "normal")]
    assert "10:30" in result.reply and "pool" not in result.sections_sent


def test_golden_after_hours_pool_from_checked_out_room():
    result = run("Room 305 here. Can we use the pool at 23:30 tonight? Also please send 2 towels.", MockClient())
    assert result.tasks == [] and result.room_status == "not_checked_in"
    assert "22:00" in result.reply and "room number" in result.reply


def test_golden_missing_room_asks_for_clarification():
    result = run("The AC isn't working and it's really hot, please help!", MockClient())
    assert result.tasks == [] and result.room_status == "missing" and result.needs_clarification
    assert "room number" in result.reply


# --- Usage logging (AGENTS.md: every attempt, success or error, goes to logs/usage.jsonl) -------

def test_every_attempt_is_logged_with_the_agents_md_fields(_usage_log_in_tmp):
    client = ScriptedClient(TransientError("HTTP 503"),
                            model_json("Breakfast is 07:00-10:30.", intent="question", cited=["breakfast"]))
    result = triage("When is breakfast?", client, today=TODAY, sleep=lambda s: None, session_id="s-42")
    lines = [json.loads(line) for line in _usage_log_in_tmp.read_text().splitlines()]
    assert [(r["attempt"], r["status"]) for r in lines] == [(1, "error"), (2, "success")]
    required = {"timestamp", "session_id", "request_id", "status", "attempt", "prompt_tokens",
                "completion_tokens", "latency_ms"}
    assert all(required <= r.keys() for r in lines)
    assert {r["session_id"] for r in lines} == {"s-42"} and {r["request_id"] for r in lines} == {result.request_id}
    assert result.cited_sections == ["breakfast"]


def test_cost_uses_gemini_price_and_mock_is_free():
    from src.llm import cost_usd
    assert cost_usd("gemini-3.8-flash", 463, 89) == round((463 * 0.75 + 89 * 3.75) / 1e6, 8)
    assert cost_usd("mock", 463, 89) == 0.0
