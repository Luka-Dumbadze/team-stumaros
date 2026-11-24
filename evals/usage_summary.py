"""Per-request medians from logs/usage.jsonl, the evidence behind docs/DESIGN-REVIEW.md section 5.

    python evals/usage_summary.py                    print the summary of live requests
    python evals/usage_summary.py --save             also write evals/results/<date>-usage.json

Only live attempts count (mock token counts are estimates). A request groups its attempts by request_id:
tokens and cost come from all of its attempts, latency is the sum of its model calls (retry backoff excluded).
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pipeline import default_usage_log  # noqa: E402


def summarize(lines: list[dict]) -> dict:
    live = [r for r in lines if r.get("mode") == "live"]
    requests: dict[str, list[dict]] = defaultdict(list)
    for r in live:
        requests[r["request_id"]].append(r)
    answered = [a for a in requests.values() if any(x["status"] == "success" for x in a)]

    def med(values: list[float]) -> float | None:
        return statistics.median(values) if values else None

    per_req = [{"tokens_in": sum(x["prompt_tokens"] for x in a), "tokens_out": sum(x["completion_tokens"] for x in a),
                "latency_ms": sum(x.get("latency_ms", 0) for x in a), "cost_usd": sum(x.get("cost_usd", 0) for x in a),
                "attempts": len(a)} for a in answered]
    log = default_usage_log()
    shown = log.relative_to(ROOT) if log.is_relative_to(ROOT) else log.name  # never commit a home-directory path
    return {"log": str(shown), "live_attempts": len(live),
            "live_attempts_failed": sum(r["status"] != "success" for r in live),
            "live_requests": len(requests), "answered_requests": len(answered),
            "median": {k: med([p[k] for p in per_req]) for k in ("tokens_in", "tokens_out", "latency_ms", "cost_usd")},
            "max_attempts_per_request": max((len(a) for a in requests.values()), default=0)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--log", type=Path, default=None, help="usage log (default: logs/usage.jsonl)")
    parser.add_argument("--save", action="store_true", help="write evals/results/<date>-usage.json")
    args = parser.parse_args(argv)
    path = args.log or default_usage_log()
    lines = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()] if path.exists() else []
    summary = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), **summarize(lines)}
    print(json.dumps(summary, indent=1))
    if summary["answered_requests"] < 10:
        print(f"note: {summary['answered_requests']} answered live requests; the Design Review asks for >= 10",
              file=sys.stderr)
    if args.save:
        out = ROOT / "evals" / "results" / f"{datetime.now().strftime('%Y-%m-%d-%H%M')}-usage.json"
        out.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
        print(f"saved {out.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
