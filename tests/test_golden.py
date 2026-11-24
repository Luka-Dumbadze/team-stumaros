"""Tests for evals/golden.yaml and the scorer in evals/run_golden.py. Offline: mock client only."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "evals"))
import run_golden  # noqa: E402

SPEC = run_golden.load_golden()


def fake_result(reply="OK.", tasks=(), events=(), validated=False, clarify=False):
    return {"reply": reply, "tasks": list(tasks), "guardrail_events": list(events),
            "room_validated": validated, "needs_clarification": clarify}


def failed_checks(case_id, result):
    case = next(c for c in SPEC["cases"] if c["id"] == case_id)
    return [c["check"] for c in run_golden.score_case(case, result) if not c["ok"]]


def test_golden_set_shape():
    assert SPEC["threshold"] == 0.70
    assert [c["id"] for c in SPEC["cases"]] == ["G1", "G2", "G3", "G4", "G5"]
    assert {c["category"] for c in SPEC["cases"]} == {"factual", "policy_refusal", "uncertainty", "edge_typo",
                                                      "hallucination_guard"}


def test_shuttle_hallucination_is_caught_even_with_escalation_appended():
    # What the code gates alone would let through: no numbers, and guardrail 4 appends the escalation.
    reply = "Yes, we offer a free airport shuttle! I don't have that information; I can ask the front desk."
    assert failed_checks("G5", fake_result(reply)) == [
        r"must_not_mention /^\s*yes\b/",
        r"must_not_mention /\b(we|hotel) (offer|offers|provide|provides|have|has|run|runs) (a |an )?"
        r"(free |complimentary )?(airport )?(shuttle|transfer)/"]


def test_honest_shuttle_refusal_passes():
    reply = "Sorry, airport shuttle information is not available. I can ask the front desk to help you."
    assert failed_checks("G5", fake_result(reply)) == []


def test_model_failure_fallback_never_passes():
    reply = "Sorry, I couldn't process your message automatically. I've flagged it for the front desk."
    assert "model_answered" in failed_checks("G5", fake_result(reply, events=["model_failed after 3 call(s): x"]))


def test_task_checks_compare_room_department_priority():
    task = {"room": "204", "department": "housekeeping", "priority": "urgent", "task": "2 pillows"}
    assert "expected_tasks" in failed_checks("G1", fake_result("Breakfast until 10:30.", [task], validated=True))
    task["priority"] = "normal"
    assert failed_checks("G1", fake_result("Breakfast until 10:30.", [task], validated=True)) == []
    assert "must_block_task" in failed_checks("G3", fake_result("room number?", [task], clarify=True))


def test_mock_run_exercises_code_gates(tmp_path):
    report = run_golden.run(SPEC, "mock", log_file=tmp_path / "usage.jsonl")
    by_id = {r["id"]: r for r in report["cases"]}
    assert report["mode"] == "mock" and "OFFLINE" in report["note"]
    # Room gate, priority and section selection are code, so the mock must get these right.
    for case_id in ("G1", "G2", "G3"):
        assert by_id[case_id]["passed"], by_id[case_id]["checks"]
    assert by_id["G1"]["sections_sent"] == ["breakfast", "housekeeping"]
    # Known pre-filter gap: typo'd "chek out" matches no keyword, so no policy is sent (ADR 002 follow-up).
    assert by_id["G4"]["sections_sent"] == []
    assert (tmp_path / "usage.jsonl").read_text().count("\n") == report["total"]


@pytest.mark.parametrize("threshold,gate", [(0.80, "PASS"), (0.81, "FAIL")])
def test_gate_compares_pass_rate_to_threshold(threshold, gate):
    report = run_golden.run({**SPEC, "threshold": threshold}, "mock", log_file=None)
    assert report["pass_rate"] == 0.8 and report["gate"] == gate  # mock: 4/5 (G4 fails, see above)
