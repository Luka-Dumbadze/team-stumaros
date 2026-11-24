"""Run the golden set against the real pipeline, score it, and save the evidence (Lab 4 pattern).

    python evals/run_golden.py                        live if GEMINI_API_KEY / OPENROUTER_API_KEY is set, else offline
    python evals/run_golden.py --mode offline         mock client: exercises the code gates only, NOT model quality
    python evals/run_golden.py --mode live --env-file hw1/Luka-Dumbadze/.env
    python evals/run_golden.py --mode live --only g5  partial run (no gate), e.g. to save free-tier quota

Writes evals/results/<YYYY-MM-DD-HHMM>-<mode>.json (+ .md) and exits 1 if the pass rate is below threshold
(0 for a partial run, 2 on setup errors). Every model attempt is appended to logs/usage.jsonl.
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
from src.prefilter import load_guide  # noqa: E402

GOLDEN = ROOT / "evals" / "golden.yaml"
RESULTS = ROOT / "evals" / "results"

TYPES = {"factual", "reasoning", "edge", "refusal", "format"}
WEEK4_MIX = {"factual": 2, "reasoning": 1, "edge": 1, "refusal": 1}
REQUIRED = {"id", "type", "question", "expect", "must_cite", "must_mention", "why"}  # Lab-4 template keys
EXTENSIONS = {"room", "must_not_mention", "tasks", "room_validated", "needs_clarification"}

# "refused" (AGENTS.md groundedness rule): the reply states the information is not available...
REFUSAL = re.compile(r"not available|unavailable|don't have|do not have|no information|can't confirm|cannot confirm"
                     r"|not able to confirm|არ მაქვს|ინფორმაცია არ", re.IGNORECASE)
# ...and offers to escalate to the front desk.
FRONT_DESK = re.compile(r"front desk|reception|მიმღებ", re.IGNORECASE)

OFFLINE_NOTE = ("OFFLINE (mock client): checks pre-filtering, room gate, priority overrides and grounding "
                "guardrails only. Mock replies are keyword templates, so this is NOT evidence of model behaviour.")


def load_golden(path: Path = GOLDEN) -> dict:
    """Load and validate golden.yaml against the course schema (plus the documented StumarOS extensions)."""
    spec = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(spec.get("threshold"), (int, float)) or not 0 < spec["threshold"] <= 1:
        raise ValueError("threshold must be a number in (0, 1]")
    section_ids = {s["id"] for s in load_guide()}
    ids = []
    for item in spec["items"]:
        where = item.get("id", "?")
        if missing := REQUIRED - item.keys():
            raise ValueError(f"{where}: missing keys {sorted(missing)}")
        if unknown := item.keys() - REQUIRED - EXTENSIONS:
            raise ValueError(f"{where}: unknown keys {sorted(unknown)}")
        if item["type"] not in TYPES:
            raise ValueError(f"{where}: type {item['type']!r} not in {sorted(TYPES)}")
        if item["expect"] not in ("answered", "refused"):
            raise ValueError(f"{where}: expect must be answered or refused")
        if bad := [c for c in item["must_cite"] if c not in section_ids]:
            raise ValueError(f"{where}: must_cite names unknown guide sections {bad}")
        if not str(item["why"]).strip():
            raise ValueError(f"{where}: why is empty")
        for pattern in item.get("must_not_mention", []):
            re.compile(pattern)
        ids.append(item["id"])
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate item ids")
    return spec


def status_of(result: dict) -> str:
    if any(e.startswith("model_failed") for e in result["guardrail_events"]):
        return "failed"
    return "refused" if REFUSAL.search(result["reply"]) else "answered"


def _task_key(t: dict) -> tuple:
    return (str(t["room"]), t["department"], t["priority"])


def score(item: dict, result: dict) -> tuple[bool, list[str]]:
    """Pass or fail one golden question, with every reason it failed (same contract as the Lab 4 runner)."""
    why = []
    reply = result["reply"]
    status = status_of(result)
    if status != item["expect"]:
        failed = [e for e in result["guardrail_events"] if e.startswith("model_failed")]
        why.append(f"expected {item['expect']}, got {status}" + (f" ({failed[0]})" if failed else ""))
    if item["expect"] == "refused" and status == "refused" and not FRONT_DESK.search(reply):
        why.append("refusal does not offer the front desk")
    if item["expect"] == "answered":
        cited = set(result.get("cited_sections", []))
        why += [f"did not cite {c}" for c in item["must_cite"] if c not in cited]
        why += [f"did not mention '{m}'" for m in item["must_mention"] if str(m).lower() not in reply.lower()]
    for pattern in item.get("must_not_mention", []):
        if m := re.search(pattern, reply, re.IGNORECASE):
            why.append(f"forbidden claim {m.group(0)!r} (/{pattern}/)")
    if "tasks" in item:
        want = Counter(_task_key(t) for t in item["tasks"])
        got = Counter(_task_key(t) for t in result["tasks"])
        if got != want:
            why.append(f"tasks: want {sorted(want.elements())}, got {sorted(got.elements())}")
    for key in ("room_validated", "needs_clarification"):
        if key in item and result[key] != item[key]:
            why.append(f"{key}: want {item[key]}, got {result[key]}")
    return (not why), why


def _git_commit() -> str:
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                             text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--", "src", "evals", "data"], cwd=ROOT,
                               capture_output=True, text=True, check=True).stdout.strip()
        return sha + ("+dirty" if dirty else "")  # dirty = uncommitted changes in src/, evals/ or data/
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def run(spec: dict, mode: str, gap: float = 0.0, only: list[str] | None = None, **triage_kwargs) -> dict:
    today = date.fromisoformat(spec["today"])
    commit = _git_commit()  # snapshot before the run: live cases wait between calls
    items = [i for i in spec["items"] if not only or i["id"] in only]
    if only and len(items) != len(set(only)):
        raise ValueError(f"unknown item id in {only}")
    rows, label = [], "mock"
    for n, item in enumerate(items):
        started = time.monotonic()
        client = MockClient() if mode == "offline" else make_client()  # fresh client per question
        label = getattr(client, "label", client.mode)
        r = triage(item["question"], client, today=today, payload_room=item.get("room"),
                   session_id=f"golden-{mode}", **triage_kwargs).to_dict()
        ok, why = score(item, r)
        rows.append({"id": item["id"], "type": item["type"], "pass": ok, "why": why, "status": status_of(r),
                     "question": item["question"], "answer": r["reply"], "cited": r["cited_sections"],
                     **{k: r[k] for k in ("tasks", "room", "room_status", "room_validated", "needs_clarification",
                                          "sections_sent", "guardrail_events", "usage", "request_id")}})
        print(f"{'PASS' if ok else 'FAIL'}  {item['id']}  {item['type']:<9}  {item['question']}")
        for w in why:
            print(f"        {w}")
        if gap and n < len(items) - 1 and (wait := gap - (time.monotonic() - started)) > 0:
            time.sleep(wait)
    passed = sum(r["pass"] for r in rows)
    pass_rate = round(passed / len(rows), 2) if rows else 0.0
    partial = len(rows) < len(spec["items"])
    note = OFFLINE_NOTE if mode == "offline" else "LIVE model run."
    if partial:
        note += f" PARTIAL run ({len(rows)} of {len(spec['items'])} questions): not a gate result."
    return {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "mode": mode, "chat_model": label,
            "commit": commit, "today": spec["today"], "passed": passed, "total": len(rows), "pass_rate": pass_rate,
            "threshold": spec["threshold"],
            "gate": "N/A (partial)" if partial else "PASS" if pass_rate >= spec["threshold"] else "FAIL",
            "note": note, "items": rows}


def _cell(text: str) -> str:
    return str(text).replace("|", "¦").replace("\n", " ")


def to_markdown(report: dict) -> str:
    mode = "OFFLINE (mock)" if report["mode"] == "offline" else "LIVE"
    lines = [f"# Golden set run · {mode} · {report['ts']}", "",
             f"**Model:** `{report['chat_model']}` · **Commit:** `{report['commit']}` · "
             f"**Stay date (`today`):** {report['today']}", "", f"> {report['note']}", "",
             f"**{report['passed']}/{report['total']} passed · pass rate {report['pass_rate']:.2f} · "
             f"threshold {report['threshold']:.2f} · gate {report['gate']}**", "",
             "| Id | Type | Status | Result | Calls | Tokens in / out | Latency | Why it failed |",
             "|---|---|---|---|---|---|---|---|"]
    for r in report["items"]:
        u = r["usage"]
        lines.append(f"| {r['id']} | {r['type']} | {r['status']} | {'PASS' if r['pass'] else '**FAIL**'} | "
                     f"{u['attempts']} | {u['prompt_tokens']} / {u['completion_tokens']}"
                     f"{' (est.)' if u['tokens_estimated'] else ''} | {u['latency_ms'] / 1000:.2f} s | "
                     f"{_cell('; '.join(r['why']) or '-')} |")
    for r in report["items"]:
        lines += ["", f"## {r['id']} · {r['type']} · {'PASS' if r['pass'] else 'FAIL'}", "",
                  f"**Question:** `{r['question']}`", "", f"**Answer:** {r['answer']}", "",
                  f"- status `{r['status']}` · cited `{r['cited']}` · sections sent `{r['sections_sent']}`",
                  f"- tasks `{json.dumps(r['tasks'], ensure_ascii=False)}`",
                  f"- room `{r['room']}` · status `{r['room_status']}` · validated `{r['room_validated']}` · "
                  f"needs_clarification `{r['needs_clarification']}`",
                  f"- guardrail events `{r['guardrail_events']}`"]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run and score the StumarOS golden set.")
    parser.add_argument("--mode", choices=("auto", "live", "offline"), default="auto",
                        help="auto = live if an API key is set, otherwise offline (default)")
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env",
                        help="dotenv file with GEMINI_API_KEY / OPENROUTER_API_KEY (default: repo-root .env)")
    parser.add_argument("--gap", type=float, default=None,
                        help="seconds between question starts (default 12 live for free-tier limits, 0 offline)")
    parser.add_argument("--only", nargs="+", metavar="ID", help="run only these ids; the report is partial, no gate")
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
    if mode != "offline":
        try:
            live = make_client().mode == "live"
        except ImportError:
            print("An API key is set but the openai package is missing: pip install -r requirements.txt",
                  file=sys.stderr)
            return 2
        if not live and mode == "live":
            print("--mode live needs GEMINI_API_KEY or OPENROUTER_API_KEY", file=sys.stderr)
            return 2
        mode = "live" if live else "offline"
    gap = args.gap if args.gap is not None else (12.0 if mode == "live" else 0.0)
    print(f"[{mode}] {args.golden}", file=sys.stderr)

    report = run(load_golden(args.golden), mode, gap=gap, only=args.only)
    args.out.mkdir(parents=True, exist_ok=True)
    stem = f"{datetime.now().strftime('%Y-%m-%d-%H%M')}-{mode}" + ("-partial" if args.only else "")
    (args.out / f"{stem}.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (args.out / f"{stem}.md").write_text(to_markdown(report), encoding="utf-8")
    print(f"\n{report['passed']}/{report['total']} passed · pass rate {report['pass_rate']:.2f} · "
          f"threshold {report['threshold']} · gate {report['gate']} · {mode} ({report['chat_model']})")
    print(f"report: {args.out / stem}.json (+ .md)")
    return 0 if report["gate"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
