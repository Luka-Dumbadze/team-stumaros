# AGENTS.md · HW1 · Guest Request Triage (Luka Dumbadze)

*Scoped instructions for this folder. The root `AGENTS.md` still applies; where this file is stricter, this file wins.*

## What this slice is
One guest message (English or Georgian) in → a grounded `reply` plus zero or more dispatch `tasks` out. No server, no session memory. Spec: `spec.md`.

## Layout
```
src/data/hotel_guide.json    mock policy sections (HW1-local, not the root data/ files)
src/data/active_rooms.json   mock stays (valid on 2026-10-15)
src/schemas.py               Task / TriageResult + validation (stdlib dataclasses)
src/prefilter.py             room extraction, room validation, section selection, token estimate
src/llm.py                   prompt, OpenAI-compatible client (Gemini / OpenRouter), mock client, ≤3-call budget
src/pipeline.py              orchestration + guardrails (room gate, priority override, grounding)
src/main.py                  CLI
src/bench.py                 live latency benchmark (spec criterion 5)
src/test_feature.py          tests
requirements.txt             openai, python-dotenv, pydantic, pytest
.env.example                 placeholder keys only; copy to .env (git-ignored)
```

## How to run (from the repo root)
```bash
python3 -m venv .venv && .venv/bin/pip install -r hw1/Luka-Dumbadze/requirements.txt
cp hw1/Luka-Dumbadze/.env.example hw1/Luka-Dumbadze/.env      # then set GEMINI_API_KEY in .env
.venv/bin/python -m hw1.Luka-Dumbadze.src.main --today 2026-10-15 --query "Can we get 2 extra pillows in room 204?"
.venv/bin/python -m pytest hw1/Luka-Dumbadze/src -q
.venv/bin/python -m hw1.Luka-Dumbadze.src.bench --n 20          # live p50/p95 latency
```
`main.py` and `bench.py` load the nearest `.env` with python-dotenv when it is installed; exported environment variables take precedence. The CLI prints which client it chose to stderr (`[live] gemini:gemini-3.8-flash` or `[mock mode] ...`).

## Model providers
Selection is by key, in this order (`llm.PROVIDERS`); an empty value counts as unset:
1. `GEMINI_API_KEY` → Google AI Studio OpenAI-compatible endpoint `https://generativelanguage.googleapis.com/v1beta/openai/`, model `gemini-3.8-flash`, `reasoning_effort="none"`.
2. `OPENROUTER_API_KEY` → `https://openrouter.ai/api/v1`, model `google/gemini-3.8-flash` (**untested live**).
3. Neither → deterministic **mock** client (`"mode": "mock"`). Its token counts are estimates and its latency is not model latency.

`--model` overrides the provider default. `gemini-2.5-flash` returns HTTP 404 ("no longer available to new users") and `gemini-1.5-flash` is retired, so do not set either as the default.

## Feature boundary
- **Code decides:** which room the message is about, whether it is valid, which policy sections are relevant, the final priority for leak/lock/AC and supply tasks, whether tasks are emitted at all, and whether the reply is grounded.
- **Model decides:** intent, wording of the reply, and proposed task department/priority/description. Every model field is validated. The model never sets `room` or `room_validated`.

## Context budget rules
- Prompt = system prompt + ≤ 3 matched policy sections + ≤ 1 room record + the guest message (truncated to 1,000 chars).
- Hard ceiling: 1,200 estimated input tokens, checked before the call. `max_tokens = 300`.
- Temperature ≤ 0.2 (default 0.1). `response_format = json_object`.
- **Thinking off on Gemini:** hidden thinking tokens count against `max_tokens`. With default thinking they used up the 300-token budget and truncated the JSON on the first live run. Keep `reasoning_effort="none"` unless `max_tokens` and the cost math change with it.
- **Forbidden:** sending the full guide or the full room list, sending other guests' names, letting the model choose the room, unbounded retries. The OpenAI SDK's own retries are disabled (`max_retries=0`) so the 3-call cap is real.

## Boundaries
- You may edit files in this folder only. Do not touch the root `data/` or other students' folders.
- **Secrets:** keys live only in the environment or in `hw1/Luka-Dumbadze/.env` (git-ignored). Never read, print or log key values; `.env.example` holds empty placeholders only.
- Dependencies are pinned in `requirements.txt`. `openai` and `python-dotenv` are imported lazily/optionally, and `pydantic` is listed but not imported by `src/`. Tests must pass offline with only the standard library + pytest; the 3 tests that need `openai` skip without it.
- Do not delete or weaken tests to make them pass.
