"""CLI: python -m hw1.Luka-Dumbadze.src.main --query "..." [--room 204] [--today 2026-10-15] [--mock]"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from .llm import PROVIDERS, MockClient, make_client
from .pipeline import triage

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv is optional: exported environment variables work without it
    load_dotenv = None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Triage one guest message into a grounded reply + tasks.")
    parser.add_argument("--query", required=True, help="guest message (English or Georgian)")
    parser.add_argument("--room", help="room number from the request payload, if known")
    parser.add_argument("--today", type=date.fromisoformat, default=date.today(), help="YYYY-MM-DD (default: today)")
    parser.add_argument("--model", help="override the provider's default model")
    parser.add_argument("--mock", action="store_true", help="force the offline mock client")
    parser.add_argument("--log-file", type=Path, help="append per-attempt usage records (JSONL)")
    args = parser.parse_args(argv)

    if load_dotenv:
        load_dotenv()  # nearest .env walking up from src/ (hw1/Luka-Dumbadze/.env); real env vars win
    try:
        client = MockClient() if args.mock else make_client(args.model)
    except ImportError:
        print("An API key is set but the openai package is missing: "
              "pip install -r hw1/Luka-Dumbadze/requirements.txt", file=sys.stderr)
        return 2
    if client.mode == "mock" and not args.mock:
        keys = " or ".join(p.key_env for p in PROVIDERS)
        print(f"[mock mode] neither {keys} is set; using the deterministic mock client.", file=sys.stderr)
    elif client.mode == "live":
        print(f"[live] {client.label}", file=sys.stderr)

    result = triage(args.query, client, today=args.today, payload_room=args.room, log_file=args.log_file)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
