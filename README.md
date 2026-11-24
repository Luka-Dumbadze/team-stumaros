# StumarOS (სტუმაროს)

An AI guest-operations assistant for 15–60 room boutique hotels in Georgia. One guest message (English or Georgian) goes in; a **grounded reply** and zero or more **dispatch tasks** for housekeeping, maintenance or the front desk come out.

The working rule is *prompting proposes, code governs*. The model drafts the reply and proposes tasks. Deterministic Python decides which room a message is about, whether that stay is active, which policy text the model may see, the final priority of safety issues, and whether any task is dispatched at all.

- Spec and measurable success criteria: [`docs/spec.md`](docs/spec.md)
- Milestone 1 design review: [`docs/DESIGN-REVIEW.md`](docs/DESIGN-REVIEW.md)
- Architecture decision records: [`docs/decisions/`](docs/decisions/)
- Agent instructions (read before changing code): [`AGENTS.md`](AGENTS.md)

> **Status (Week 4):** a CLI triage pipeline (`src/`), promoted from the HW1 slice. The FastAPI `POST /chat` service, session memory and `app/` described in `AGENTS.md` are the Week 5+ target and do not exist yet.

## Layout
```
src/                 triage pipeline (promoted from hw1/Luka-Dumbadze/src)
  prefilter.py         room extraction + validation, keyword section selection (≤ 3), token estimate
  llm.py               prompt, OpenAI-SDK client for Gemini / OpenRouter, offline mock, ≤ 3-call budget
  pipeline.py          orchestration + guardrails: room gate, priority overrides, grounding checks
  schemas.py           Task / model-output validation (stdlib dataclasses)
  main.py              CLI
  bench.py             live latency benchmark
data/                hotel_guide.json, active_rooms.json (mock data; stays are valid on 2026-10-15; read-only)
tests/               pytest suite (offline, no API key needed)
evals/
  golden.yaml          5 checkable golden cases + 0.70 pass threshold
  run_golden.py        runs, scores and reports the golden set
  results/             committed reports (JSON + Markdown), live or clearly labelled offline
docs/                spec, design review, ADRs, team, pattern journal
hw1/                 individual HW1 submissions (historical; do not edit)
logs/                usage.jsonl, one record per model attempt (git-ignored)
```

## Setup
Python 3.11+ (developed on 3.12).
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env        # then set GEMINI_API_KEY (or OPENROUTER_API_KEY); .env is git-ignored
```
With no key set, everything runs against a deterministic **mock** client. That is enough for the tests and for checking the code gates, but it says nothing about model quality.

## Run
All commands run from the repo root.

**CLI: triage one message.** The mock stays are valid on 2026-10-15, so pin `--today`:
```bash
.venv/bin/python -m src.main --today 2026-10-15 --query "Can we get 2 extra pillows in room 204?"
.venv/bin/python -m src.main --today 2026-10-15 --query "The AC isn't working!" --mock   # force offline
.venv/bin/python -m src.main --today 2026-10-15 --query "..." --log-file logs/usage.jsonl
```

**Unit tests** (offline):
```bash
.venv/bin/python -m pytest                          # root suite: tests/
.venv/bin/python -m pytest hw1/Luka-Dumbadze/src    # HW1 snapshot's own suite
```

**Golden evaluation:**
```bash
.venv/bin/python evals/run_golden.py                # live if a key is set, otherwise offline mock
.venv/bin/python evals/run_golden.py --mode mock    # force offline (code gates only)
.venv/bin/python evals/run_golden.py --mode live    # fail if no key
```
Each run writes `evals/results/golden-<timestamp>-<live|mock>.{json,md}`, appends every model attempt to `logs/usage.jsonl`, and exits `1` if the pass rate is below the 0.70 threshold. Live runs space cases 12 s apart, because the free Gemini tier allows about 20 requests per day.

**Latency benchmark** (live only, uses quota):
```bash
.venv/bin/python -m src.bench --n 10 --gap 12
```

## Model access
`GEMINI_API_KEY` → Google AI Studio's OpenAI-compatible endpoint (`gemini-3.8-flash`, thinking off); otherwise `OPENROUTER_API_KEY` → OpenRouter; otherwise the mock client. See [ADR 003](docs/decisions/003-openai-endpoint-portability.md). Keys come from the environment or `.env` only, and are never logged.

## Team
[@Luka-Dumbadze](https://github.com/Luka-Dumbadze). See [`docs/team.md`](docs/team.md) and [`docs/team-contract.md`](docs/team-contract.md).
