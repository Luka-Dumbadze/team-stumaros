"""Tests for evals/golden.yaml and the scorer in evals/run_golden.py (Lab 4 pattern). Offline: mock client only."""
import copy
import sys
from collections import Counter
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals"))
import run_golden  # noqa: E402

GOLDEN = run_golden.load_golden()


def item(item_id):
    return next(i for i in GOLDEN["items"] if i["id"] == item_id)


def result(reply="OK.", tasks=(), events=(), cited=(), validated=False, clarify=False):
    return {"reply": reply, "tasks": list(tasks), "guardrail_events": list(events), "cited_sections": list(cited),
            "room_validated": validated, "needs_clarification": clarify}


def broken_golden(tmp_path, mutate):
    bad = copy.deepcopy(GOLDEN)
    mutate(bad)
    path = tmp_path / "golden.yaml"
    path.write_text(yaml.safe_dump(bad, allow_unicode=True), encoding="utf-8")
    return path


def test_golden_set_follows_the_week_4_composition():
    assert Counter(i["type"] for i in GOLDEN["items"]) == run_golden.WEEK4_MIX
    assert GOLDEN["threshold"] == 0.70


def test_every_must_cite_points_at_a_real_guide_section(tmp_path):
    path = broken_golden(tmp_path, lambda g: g["items"][0].update(must_cite=["spa"]))
    with pytest.raises(ValueError, match="unknown guide sections"):
        run_golden.load_golden(path)


def test_schema_rejects_a_missing_template_key(tmp_path):
    path = broken_golden(tmp_path, lambda g: g["items"][1].pop("why"))
    with pytest.raises(ValueError, match="missing keys"):
        run_golden.load_golden(path)


def test_score_passes_a_correct_cited_answer():
    task = {"room": "204", "department": "housekeeping", "priority": "normal", "task": "2 pillows"}
    assert run_golden.score(item("g1"), result("საუზმე 07:00-10:30.", [task], cited=["breakfast"],
                                               validated=True)) == (True, [])


def test_score_fails_the_wrong_source_and_the_wrong_priority():
    task = {"room": "204", "department": "housekeeping", "priority": "urgent", "task": "2 pillows"}
    ok, why = run_golden.score(item("g1"), result("საუზმე 10:30-მდე.", [task], cited=["pool"], validated=True))
    assert not ok and why[0] == "did not cite breakfast" and why[1].startswith("tasks:")


def test_shuttle_hallucination_is_caught_even_with_the_escalation_appended():
    # What the code gates alone let through: no numbers, and guardrail 4 appends the front-desk line.
    reply = "Yes, we offer a free airport shuttle! I don't have that information; I can ask the front desk."
    ok, why = run_golden.score(item("g5"), result(reply))
    assert not ok and len(why) == 2 and all(w.startswith("forbidden claim") for w in why)


def test_honest_shuttle_refusal_passes_and_must_offer_the_front_desk():
    assert run_golden.score(item("g5"), result("Sorry, shuttle information is not available. "
                                               "I can ask the front desk.")) == (True, [])
    _, why = run_golden.score(item("g5"), result("Sorry, shuttle information is not available."))
    assert why == ["refusal does not offer the front desk"]


def test_an_answer_where_a_refusal_was_expected_fails():
    ok, why = run_golden.score(item("g5"), result("Our driver meets you at the airport."))
    assert not ok and why[0] == "expected refused, got answered"


def test_model_failure_fallback_never_passes():
    fallback = "Sorry, I couldn't process your message automatically. I've flagged it for the front desk."
    ok, why = run_golden.score(item("g5"), result(fallback, events=["model_failed after 3 call(s): x"]))
    assert not ok and why[0].startswith("expected refused, got failed")


def test_offline_golden_run_meets_threshold_and_exercises_code_gates():
    report = run_golden.run(GOLDEN, "offline")
    by_id = {r["id"]: r for r in report["items"]}
    assert report["mode"] == "offline" and "OFFLINE" in report["note"]
    assert report["pass_rate"] >= GOLDEN["threshold"]
    for item_id in ("g1", "g2", "g3", "g5"):  # room gate, priority, section selection are code
        assert by_id[item_id]["pass"], by_id[item_id]["why"]
    assert by_id["g1"]["sections_sent"] == ["breakfast", "housekeeping"]  # no pool leak (decision 0002)
    # Known pre-filter gap: "chek out" matches no keyword, so nothing is sent and the reply escalates.
    assert by_id["g4"]["sections_sent"] == [] and by_id["g4"]["status"] == "refused"


def test_offline_run_logs_one_usage_line_per_question(_usage_log_in_tmp):
    run_golden.run(GOLDEN, "offline")
    assert len(_usage_log_in_tmp.read_text().splitlines()) == len(GOLDEN["items"])


def test_partial_run_has_no_gate():
    report = run_golden.run(GOLDEN, "offline", only=["g5"])
    assert [r["id"] for r in report["items"]] == ["g5"] and report["gate"] == "N/A (partial)"
    with pytest.raises(ValueError):
        run_golden.run(GOLDEN, "offline", only=["g9"])


def test_usage_summary_counts_only_live_answered_requests():
    sys.path.insert(0, str(ROOT / "evals"))
    import usage_summary
    base = {"session_id": "s", "latency_ms": 100, "cost_usd": 0.0}
    lines = [{**base, "mode": "live", "request_id": "a", "status": "error", "attempt": 1,
              "prompt_tokens": 0, "completion_tokens": 0},
             {**base, "mode": "live", "request_id": "a", "status": "success", "attempt": 2,
              "prompt_tokens": 463, "completion_tokens": 89},
             {**base, "mode": "live", "request_id": "b", "status": "error", "attempt": 1,
              "prompt_tokens": 0, "completion_tokens": 0},
             {**base, "mode": "mock", "request_id": "c", "status": "success", "attempt": 1,
              "prompt_tokens": 999, "completion_tokens": 999}]
    s = usage_summary.summarize(lines)
    assert (s["live_requests"], s["answered_requests"], s["live_attempts_failed"]) == (2, 1, 2)
    assert s["median"]["tokens_in"] == 463 and s["median"]["latency_ms"] == 200
