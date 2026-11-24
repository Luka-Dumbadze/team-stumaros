# StumarOS (სტუმაროს)

**Answers boutique-hotel guests from the hotel's own policy, and turns their requests into validated housekeeping, maintenance and front-desk tasks, in English or Georgian.**
CS6920 capstone · Fall 2026 · team-stumaros · Luka Dumbadze, Urju

> Status: Week 4. A CLI triage pipeline (`src/`) with a code-enforced room gate, priority overrides, grounding checks and a 5-question golden set. The FastAPI `POST /chat` service and session memory in `AGENTS.md` are the Week 5+ target.

## The problem
One receptionist on a shared phone reads every guest message during the check-in rush. They answer the same policy questions and retype requests into staff tasks. A request from a room that already checked out, or a confident wrong answer, costs real staff time.

## Demo
Not yet: the narrated video comes in Week 14, deployment in Week 12.

## Run it
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env        # then set GEMINI_API_KEY (or OPENROUTER_API_KEY); with no key, a mock client runs
.venv/bin/python -m src.main --today 2026-10-15 --query "Can we get 2 extra pillows in room 204?"
.venv/bin/python -m pytest -q tests                  # unit tests, offline, no key (what CI runs)
.venv/bin/python evals/run_golden.py                 # golden set: live if a key is set, else offline (mock)
.venv/bin/python evals/usage_summary.py              # medians from logs/usage.jsonl
```
- **Stay dates:** the mock stays in `data/active_rooms.json` are valid on 2026-10-15, so pin `--today`.
- **Mock vs live:** `--mock` forces the offline client. `evals/run_golden.py --mode live --only g5` runs one question live.
- **Usage log:** every model attempt is appended to `logs/usage.jsonl` (git-ignored).
- **HW1 suite:** the HW1 snapshot keeps its own tests: `pytest hw1/Luka-Dumbadze/src`.

## How it works
- **Pipeline:** guest message → **room gate** in code (`src/prefilter.py`, against `data/active_rooms.json`) → **keyword pre-filter** sends at most 3 sections of `data/hotel_guide.json` → one `gemini-3.8-flash` call returns JSON (at most 3 calls with retries, `src/llm.py`) → **guardrails** in `src/pipeline.py`. The guardrails drop tasks for invalid rooms, force leak/lock/AC tasks to `urgent`, and replace replies with unsupported numbers.
- **Uncertainty:** when unsure, it asks or escalates to the front desk ([`docs/confidence-policy.md`](docs/confidence-policy.md)).
- **Architecture and budget:** [`docs/DESIGN-REVIEW.md`](docs/DESIGN-REVIEW.md) · **Key decisions:** [`docs/decisions/`](docs/decisions/)

```
src/      triage pipeline          tests/    pytest suite (CI)         evals/   golden.yaml, runner, results/
data/     mock guide + stays       docs/     spec, review, decisions   hw1/     individual HW1 (historical)
```

## Does it work? (evidence)
| What we measure | Result | Where |
|---|---|---|
| Unit tests | 53 passing locally; CI added Week 4, no run on `main` yet | `tests/`, `.github/workflows/ci.yml` |
| Golden set | 4/5 offline (0.80, threshold 0.70); live **not yet measured** (provider outage 2026-11-24) | [`evals/results/`](evals/results/README.md) |
| Cost per request | $0.00068 median (463 / 89 tokens) | HW1 live usage; `logs/usage.jsonl` from the next live run |
| p95 latency | 8.36 s, against a 3 s target: **fails** | `hw1/Luka-Dumbadze/golden.md` |

## Case study
From Week 13: `docs/case-study.md`.

## Team and how we work
Luka Dumbadze ([@Luka-Dumbadze](https://github.com/Luka-Dumbadze)) · Urju ([@UrjuHub](https://github.com/UrjuHub)) · Team rules: [docs/TEAM-REPO.md](docs/TEAM-REPO.md) · Spec: [docs/spec.md](docs/spec.md) · Delegation log: [docs/delegation-log.md](docs/delegation-log.md) · Journals: [docs/journal/](docs/journal/) · Team contract: [TEAM-CONTRACT.md](TEAM-CONTRACT.md) · Agent rules: [AGENTS.md](AGENTS.md)
