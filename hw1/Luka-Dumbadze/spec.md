# HW1 Spec · Guest Request Triage (StumarOS slice) · Luka Dumbadze

## Problem
A solo receptionist at a 15–60 room boutique hotel reads every guest WhatsApp message by hand to decide two things: *is this a question I can answer from policy?* and *does someone need to go to a room?* Requests for rooms that are no longer occupied (e.g. a guest who checked out yesterday asking for towels) and confident-sounding but wrong policy answers (e.g. "the pool is open late") both create real staff work. This slice takes one guest message and returns a grounded reply plus zero or more dispatch tasks, with the room gate enforced in code rather than in the prompt.

## Persona
Front-desk receptionist on a shared phone during check-in rush; secondary: the guest writing in English or Georgian.

## Feature boundary
| Deterministic code | Model (`gemini-3.8-flash`, T = 0.1, thinking off) |
|---|---|
| Room extraction (regex), room validation (`status == "checked_in"` and `check_in <= today <= check_out`) | Classify intent: question / service / composite / unclear |
| Pre-filter policy sections by keyword (≤ 3) | Phrase the reply from the supplied sections only |
| Priority overrides (leak/lock/AC → `urgent`; supplies never `urgent`) | Propose tasks: `department`, `priority`, `task` |
| Schema validation, ≤ 3 calls, grounding check on times/prices | — |

## Context budget (what enters the prompt)
1. Fixed system prompt (rules + output JSON schema).
2. **≤ 3 policy sections** whose keywords match the message. All other sections are pruned before the call.
3. **≤ 1 room record**: the one matching the extracted/payload room, plus its computed validity. The rest of the room list is never sent.
4. The guest message (≤ 1,000 chars; longer is truncated).
Hard ceiling: **1,200 estimated input tokens** (request rejected before the call if exceeded), `max_tokens = 300`.

## Napkin cost
Monthly Cost = (req/day × (tokens_in × price_in + tokens_out × price_out)) × 30, at $0.75/M in, $3.75/M out, 200 req/day.
- **English** (≈ 570 in, 110 out): 200 × (570 × 0.75 + 110 × 3.75) / 1M × 30 ≈ **$5.04/month**.
- **Georgian** ("სტუმრის რეგისტრაცია" tokenizes 2–4× heavier; assume 3× on message and reply, so ≈ 630 in, 330 out): ≈ **$10.26/month**. Output is the expensive side, so the reply length cap matters more than the input.
- **Unfiltered baseline** (whole guide + 60 room records ≈ 2,400 in): ≈ **$13.27/month**. The pre-filter roughly halves cost in English.
Estimates only. Post-build check with the code's estimator: built prompts are 397 (EN) to 465 (KA) tokens in; unfiltered (full guide + 60 rooms) ≈ 2,560, so the filtered prompt is ~6x smaller. **Measured live** (gemini-3.8-flash, 2026-10-15, `golden.md`): 391–466 prompt and 83–145 completion tokens per request, so ≈ **$4.10/month** in English (466 / 89) and ≈ **$5.35/month** in Georgian (463 / 145). The Georgian penalty showed up in the output (1.6x), not the input, because the English system prompt dominates the input.

## Acceptance criteria
1. **Strict output:** 100% of runs return JSON with `reply`, `tasks`, `room_validated`, and each task has `room`, `department` ∈ {housekeeping, maintenance, front_desk}, `priority` ∈ {low, normal, urgent}, `task`. Malformed model JSON triggers 1 corrective retry; total model calls ≤ 3 per request.
2. **Room gate:** if the room is missing, unknown, not `checked_in`, or outside its stay dates, `tasks == []` and the reply asks for room number and name, even if the model proposed tasks.
3. **Context budget:** the prompt contains only matched sections (≤ 3) and ≤ 1 room record; a test asserts that unrelated sections and other guests' names are absent.
4. **Grounding:** any time or price in the reply that appears neither in the supplied sections nor in the guest message replaces the reply with a front-desk escalation; questions with no matching section get "not available + front desk".
5. **Latency:** p95 end-to-end < 2.5 s over ≥ 20 live runs (measured, not assumed). **Measured 2026-10-15: FAIL.** p95 8.36 s, p50 5.33 s, and 0 of 9 successful live answers under 2.5 s (`golden.md`). This is still short of 20 runs, because the free tier allows 20 requests/day.

## Out of scope
Multi-turn memory, FastAPI endpoint, persistence, model-as-judge grading.

**Run:** put `GEMINI_API_KEY` (or `OPENROUTER_API_KEY`) in `hw1/Luka-Dumbadze/.env`, then `python -m hw1.Luka-Dumbadze.src.main --query "..."` from the repo root. With no key the CLI runs the offline mock. Setup details are in `AGENTS.md`.
