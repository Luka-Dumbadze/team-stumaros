"""Live latency benchmark for spec criterion 5: python -m src.bench [--n 10] [--gap 12]

Latency is end-to-end per request as triage() measures it: pre-filter + every model call + retry backoff.
Each request gets a fresh client (like one CLI run), so connection setup is included.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from datetime import date

from .llm import make_client
from .pipeline import triage

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

SLA_SECONDS = 2.5
MESSAGES = [
    "გამარჯობა! ოთახი 204-ში 2 დამატებითი ბალიში გვჭირდება. როდემდეა საუზმე?",
    "Room 305 here. Can we use the pool at 23:30 tonight? Also please send 2 towels.",
    "The AC isn't working and it's really hot, please help!",
    "What's the Wi-Fi password?",
    "Do you have an airport shuttle?",
]


def percentile(values: list[float], p: float) -> float:
    """Nearest-rank percentile: with n = 10, p95 is the maximum."""
    ordered = sorted(values)
    return ordered[max(0, math.ceil(p / 100 * len(ordered)) - 1)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--n", type=int, default=10, help="number of requests")
    parser.add_argument("--gap", type=float, default=12.0,
                        help="seconds between request starts (free-tier rate limits)")
    parser.add_argument("--today", type=date.fromisoformat, default=date(2026, 10, 15),
                        help="date the mock stays are valid for (default 2026-10-15)")
    args = parser.parse_args(argv)
    if load_dotenv:
        load_dotenv()

    rows = []
    for i in range(args.n):
        started = time.monotonic()
        client = make_client()
        if client.mode != "live":
            raise SystemExit("benchmark needs GEMINI_API_KEY or OPENROUTER_API_KEY (mock latency is meaningless)")
        message = MESSAGES[i % len(MESSAGES)]
        r = triage(message, client, today=args.today)
        row = {"i": i + 1, "message": message[:40], "latency_s": r.usage.latency_ms / 1000,
               "attempts": r.usage.attempts, "prompt_tokens": r.usage.prompt_tokens,
               "completion_tokens": r.usage.completion_tokens, "total_tokens": r.usage.total_tokens,
               "model_ok": not any(e.startswith("model_failed") for e in r.guardrail_events),
               "tasks": len(r.tasks), "events": r.guardrail_events, "reply": r.reply}
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
        if i < args.n - 1 and (wait := args.gap - (time.monotonic() - started)) > 0:
            time.sleep(wait)

    print(json.dumps({"model": client.label, "sla_s": SLA_SECONDS,
                      "all": summarize(rows),
                      # Fallbacks after a 429 return fast; mixing them in flatters p50 (seen on 2026-10-15).
                      "model_ok_only": summarize([row for row in rows if row["model_ok"]]),
                      "rate_limited": sum(any("RateLimitError" in e for e in row["events"]) for row in rows)}),
          flush=True)
    return 0


def summarize(rows: list[dict]) -> dict:
    latencies = [row["latency_s"] for row in rows]
    if not latencies:
        return {"n": 0}
    return {"n": len(latencies), "p50_s": percentile(latencies, 50), "p95_s": percentile(latencies, 95),
            "max_s": max(latencies), "mean_s": round(statistics.mean(latencies), 3),
            "within_sla": sum(x < SLA_SECONDS for x in latencies),
            "p95_meets_sla": percentile(latencies, 95) < SLA_SECONDS}


if __name__ == "__main__":
    raise SystemExit(main())
