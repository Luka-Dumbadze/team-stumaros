"""Run the StumarOS golden set, score it, and write a JSON + Markdown report to evals/results/.

    python evals/run_golden.py                       # live if GEMINI_API_KEY / OPENROUTER_API_KEY is set, else mock
    python evals/run_golden.py --mode mock           # offline: exercises code gates only, NOT model quality
    python evals/run_golden.py --mode live --env-file hw1/Luka-Dumbadze/.env

Exit code: 0 if pass_rate >= threshold, 1 if the gate fails, 2 on setup errors. Every model attempt is appended
to logs/usage.jsonl (git-ignored).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:  # allow `python evals/run_golden.py` from anywhere
    sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from src.llm import MockClient, make_client  # noqa: E402
from src.pipeline import triage  # noqa: E402

GOLDEN = ROOT / "evals" / "golden.yaml"
RESULTS = ROOT / "evals" / "results"
USAGE_LOG = ROOT / "logs" / "usage.jsonl"
CASE_KEYS = {"id", "category", "title", "input", "room", "must_mention", "must_not_mention", "must_block_task",
             "expected_tasks", "expect_room_validated", "expect_needs_clarification"}
OFFLINE_BANNER = ("OFFLINE (mock client): checks pre-filtering, room gate, priority overrides and grounding "
                  "guardrails only. Mock replies are keyword templates, so this is NOT evidence of model behaviour.")


def load_golden(path: Path = GOLDEN) -> dict:
    spec = yaml.safe_load(path.read_text(encoding="utf-8"))
    ids = [c["id"] for c in spec["cases"]]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate case ids in {path}")
    for case in spec["cases"]:
        if unknown := set(case) - CASE_KEYS:
            raise ValueError(f"{case['id']}: unknown keys {sorted(unknown)}")
        if not case["must_block_task"] and not case.get("expected_tasks"):
            raise ValueError(f"{case['id']}: must_block_task is false but expected_tasks is empty")
        for pattern in case.get("must_mention", []) + case.get("must_not_mention", []):
            re.compile(pattern)
    return spec


def _task_key(t: dict) -> tuple:
    return (str(t["room"]), t["department"], t["priority"])


def score_case(case: dict, result: dict) -> list[dict]:
    """Deterministic checks of one triage result (TriageResult.to_dict()) against one golden case."""
    reply = result["reply"]
    checks = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    failed = [e for e in result["guardrail_events"] if e.startswith("model_failed")]
    check("model_answered", not failed, failed[0] if failed else "")
    for pattern in case.get("must_mention", []):
        check(f"must_mention /{pattern}/", re.search(pattern, reply, re.IGNORECASE))
    for pattern in case.get("must_not_mention", []):
        m = re.search(pattern, reply, re.IGNORECASE)
        check(f"must_not_mention /{pattern}/", m is None, f"matched {m.group(0)!r}" if m else "")
    got = Counter(_task_key(t) for t in result["tasks"])
    if case["must_block_task"]:
        check("must_block_task", not got, f"emitted {sorted(got.elements())}" if got else "")
    else:
        want = Counter(_task_key(t) for t in case["expected_tasks"])
        check("expected_tasks", got == want, f"want {sorted(want.elements())}, got {sorted(got.elements())}")
    for key, field in (("expect_room_validated", "room_validated"),
                       ("expect_needs_clarification", "needs_clarification")):
        if key in case:
            check(f"{field} == {case[key]}", result[field] == case[key], f"got {result[field]}")
    return checks


def _git_commit() -> str:
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                             text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True,
                               text=True, check=True).stdout.strip()
        return sha + ("+dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def run(spec: dict, mode: str, gap: float = 0.0, log_file: Path | None = USAGE_LOG) -> dict:
    today = date.fromisoformat(spec["today"])
    rows = []
    label = "mock"
    for i, case in enumerate(spec["cases"]):
        started = time.monotonic()
        client = MockClient() if mode == "mock" else make_client()  # fresh client per case, like one CLI run
        label = getattr(client, "label", client.mode)
        result = triage(case["input"], client, today=today, payload_room=case.get("room"), log_file=log_file)
        r = result.to_dict()
        checks = score_case(case, r)
        rows.append({"id": case["id"], "category": case["category"], "title": case["title"],
                     "input": case["input"], "passed": all(c["ok"] for c in checks), "checks": checks,
                     **{k: r[k] for k in ("reply", "tasks", "room", "room_status", "room_validated",
                                          "needs_clarification", "sections_sent", "guardrail_events",
                                          "usage", "request_id")}})
        if gap and i < len(spec["cases"]) - 1 and (wait := gap - (time.monotonic() - started)) > 0:
            time.sleep(wait)
    passed = sum(r["passed"] for r in rows)
    pass_rate = round(passed / len(rows), 3) if rows else 0.0
    return {"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "commit": _git_commit(),
            "mode": mode, "model": label, "today": spec["today"], "threshold": spec["threshold"],
            "passed": passed, "total": len(rows), "pass_rate": pass_rate,
            "gate": "PASS" if pass_rate >= spec["threshold"] else "FAIL",
            "note": OFFLINE_BANNER if mode == "mock" else "LIVE model run.", "cases": rows}


def to_markdown(report: dict) -> str:
    mode = "OFFLINE (mock)" if report["mode"] == "mock" else "LIVE"
    lines = [f"# Golden set run · {mode} · {report['run_at']}", "",
             f"**Mode:** {mode} · **Model:** `{report['model']}` · **Commit:** `{report['commit']}` · "
             f"**Stay date (`today`):** {report['today']}", "",
             f"> {report['note']}", "",
             f"**Result: {report['passed']}/{report['total']} passed · pass rate {report['pass_rate']:.2f} · "
             f"threshold {report['threshold']:.2f} · gate {report['gate']}**", "",
             "| Case | Category | Result | Calls | Tokens in / out | Latency | Failed checks |",
             "|---|---|---|---|---|---|---|"]
    for r in report["cases"]:
        u = r["usage"]
        failed = "; ".join(f"{c['check']}" + (f" ({c['detail']})" if c["detail"] else "")
                           for c in r["checks"] if not c["ok"]) or "none"
        lines.append(f"| {r['id']} {r['title']} | {r['category']} | {'PASS' if r['passed'] else '**FAIL**'} | "
                     f"{u['attempts']} | {u['prompt_tokens']} / {u['completion_tokens']}"
                     f"{' (est.)' if u['tokens_estimated'] else ''} | {u['latency_ms'] / 1000:.2f} s | "
                     f"{failed.replace('|', '¦')} |")
    for r in report["cases"]:
        lines += ["", f"## {r['id']} · {r['title']} · {'PASS' if r['passed'] else 'FAIL'}", "",
                  f"**Input:** `{r['input']}`", "", f"**Reply:** {r['reply']}", "",
                  f"- tasks: `{json.dumps(r['tasks'], ensure_ascii=False)}`",
                  f"- room: `{r['room']}` · status `{r['room_status']}` · validated `{r['room_validated']}` · "
                  f"needs_clarification `{r['needs_clarification']}`",
                  f"- sections sent: `{r['sections_sent']}`",
                  f"- guardrail events: `{r['guardrail_events']}`", "", "| Check | OK | Detail |", "|---|---|---|"]
        lines += [f"| `{c['check'].replace('|', '¦')}` | {'yes' if c['ok'] else '**no**'} | "
                  f"{c['detail'].replace('|', '¦')} |" for c in r["checks"]]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run and score the StumarOS golden set.")
    parser.add_argument("--mode", choices=("auto", "live", "mock"), default="auto",
                        help="auto = live if an API key is set, otherwise mock (default)")
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env",
                        help="dotenv file with GEMINI_API_KEY / OPENROUTER_API_KEY (default: repo-root .env)")
    parser.add_argument("--gap", type=float, default=None,
                        help="seconds between case starts (default 12 live for free-tier limits, 0 mock)")
    parser.add_argument("--golden", type=Path, default=GOLDEN)
    parser.add_argument("--out", type=Path, default=RESULTS)
    args = parser.parse_args(argv)

    try:
        from dotenv import load_dotenv
        if args.env_file.is_file():
            load_dotenv(args.env_file)  # exported environment variables still win
    except ImportError:
        pass
    mode = args.mode
    if mode != "mock":
        try:
            probe = make_client()
        except ImportError:
            print("An API key is set but the openai package is missing: pip install -r requirements.txt",
                  file=sys.stderr)
            return 2
        if probe.mode != "live":
            if mode == "live":
                print("--mode live needs GEMINI_API_KEY or OPENROUTER_API_KEY", file=sys.stderr)
                return 2
            mode = "mock"
        else:
            mode = "live"
    gap = args.gap if args.gap is not None else (12.0 if mode == "live" else 0.0)
    print(f"[{mode}] running {args.golden.relative_to(ROOT) if args.golden.is_relative_to(ROOT) else args.golden}",
          file=sys.stderr)

    report = run(load_golden(args.golden), mode, gap=gap)
    args.out.mkdir(parents=True, exist_ok=True)
    stem = f"golden-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{mode}"
    (args.out / f"{stem}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.out / f"{stem}.md").write_text(to_markdown(report), encoding="utf-8")

    for r in report["cases"]:
        print(f"{r['id']:<3} {'PASS' if r['passed'] else 'FAIL'}  {r['category']:<20} {r['title']}")
    print(f"{report['passed']}/{report['total']} passed · pass rate {report['pass_rate']:.2f} · "
          f"threshold {report['threshold']:.2f} · gate {report['gate']} · mode {mode} ({report['model']})")
    print(f"report: {(args.out / stem).relative_to(ROOT) if args.out.is_relative_to(ROOT) else args.out / stem}.{{json,md}}")
    return 0 if report["gate"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
