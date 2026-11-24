# Delegation Log · HW1 · Luka Dumbadze

## What was delegated
Almost everything in this folder was produced by Claude Code (Opus 5.5) from one long operator prompt: the slice choice, `spec.md`, `AGENTS.md`, all of `src/`, the tests, the golden runs, and the first drafts of this log and the journal. Before that, in the same session, I used it to critique the team `docs/spec.md` and `AGENTS.md`. I decided the scope cuts there myself. Later I also delegated the switch to a free Google AI Studio key and the live verification runs.

## Autonomy Ladder rung used
- **Rung 3 was intended for the build:** the agent writes the code, and I read every line of the diff before it is merged (course definition, Lab 3/4 READMEs). This covers `src/`, the tests and the golden runs.
- **In practice, verification sat below rung 3.** I checked the agent's *outputs* (golden replies, test runs, the live JSON), not every line of the diff. By the course's own measure, a rung-3 delegation whose diff is not read has silently moved to rung 4. That stays true until I complete the line-by-line review of `src/pipeline.py` and `src/prefilter.py` in the sign-off table at the end of this file.
- **Scope decisions were rung 2:** the agent suggested and I decided. It critiqued the team `docs/spec.md` and `AGENTS.md`; I rejected the LLM-as-judge (item 3 below), dropped the extra confirmation turn, and kept priorities in code.
- **Evidence over trust:** the agent's claims were accepted only with evidence, namely the live runs in `golden.md` and the test names cited in this log.

## Portability: one SDK, two providers
Moving from OpenRouter to Google AI Studio needed **no rewrite of the request code**. The same OpenAI SDK call (`chat.completions.create` with `response_format=json_object`) works against Google's OpenAI-compatible endpoint (`/v1beta/openai/`). Only `base_url`, the key and the model name change, and those live in one table (`llm.PROVIDERS`). What did *not* port for free was model behaviour, and configuration had to absorb it:
- `gemini-2.5-flash` is still returned by `models.list` but answers HTTP 404 ("no longer available to new users"). The default became `gemini-3.8-flash`, which Google's error message suggests and which the spec already priced.
- Default thinking had to be turned off (`reasoning_effort="none"`, item 5 below).

Both are one-line provider settings, not code changes.

## What came back wrong, and how it was caught
1. **Georgian keyword pre-filter leaked an unrelated section.** The AI-written pre-filter matched Georgian stems as substrings, so `აუზ` (pool) fired inside `საუზმე` (breakfast). The pool rules went into the prompt and the reply. The unit test it had written for the same input still passed, because it only checked that `10:30` was in the reply. **Caught by** reading the actual output of golden case 1 rather than the green test run. **Fixed with** word-start matching plus a regression test asserting the exact selected sections.
2. **A latency metric that couldn't measure what it claimed.** While rewriting the team success criteria, the AI defined end-to-end p95 latency as "computed from `latency_ms` in `logs/usage.jsonl`". That field is logged per model call, not per request. **Caught by** the AI itself on a later re-read, after I tightened `AGENTS.md`. Now measured by harness wall-clock.
3. **Scope creep into an LLM judge.** To grade grounding, the AI added an LLM-as-judge layer to the success criteria. **Rejected by me:** v0 stays deterministic (regex fixtures), and judges are out of scope until Week 11.
4. **The operator prompt itself was wrong about the product.** My HW1 prompt described StumarOS as a KIU campus/dorm visitor system with a curfew test case. The repo spec says boutique hotels. The agent followed `docs/spec.md` and mapped "curfew" to the pool's closing hours. Lesson: the spec, not the prompt, is the source of truth.
5. **Thinking tokens ate the output budget.** The AI-written client set `max_tokens=300` without accounting for Gemini's default thinking. On the first live call, 575 hidden tokens went to thinking, the JSON was cut off after ~4 characters on both completions, the corrective retry timed out, and the request took 25.3 s before returning the fallback. **Caught by** the first live golden run; the mock cannot think, so no offline test could have seen it. **Fixed with** `reasoning_effort="none"` (0 hidden tokens, valid JSON on the next call), a test that pins the request parameters, and truncation now reported as `finish_reason=length` instead of a bare JSON parse error.
6. **The live model ignored a prompt rule; the code gate held.** In golden case 3 (no room given), `gemini-3.8-flash` still proposed a maintenance task, despite prompt rule 4. `room_gate` dropped it. This is the evidence for keeping the room decision in code.
7. **Telemetry bug.** A timed-out attempt (no usage returned) flagged the whole request's real API token counts as "estimated". **Caught by** reading the live JSON. Fixed with a test.

## Known gaps (not fixed, not hidden)
- **Latency misses the SLA.** Successful live answers took 2.7–8.4 s (p50 5.3 s, p95 8.4 s) against a 2.5 s p95 target (`golden.md`). The benchmark is n = 10 on the free tier, below the spec's ≥ 20 runs.
- **Free-tier quota.** The free tier allows 20 requests/day per model, and HTTP 500s and timeouts count against it: 7 of the 20 calls made on 2026-10-15 were server errors. A 20-run benchmark (up to 60 calls with retries) does not fit in one free-tier day.
- **Only one provider tested live.** The live path is Google AI Studio (`gemini-3.8-flash`, free tier). The OpenRouter path has never made a real call.
- **Transient 500s happen.** The first live run of case 3 got three HTTP 500s in a row and returned the fallback after 9.5 s; the re-run passed.
- **The fallback reply over-promises.** It says the message was "flagged for the front desk", but in this slice only the `model_failed` event in the result marks it. A caller has to surface that to staff.
- **Grounding check is numbers-only.** A reply that invents a time or price is replaced, but "Yes, we have an airport shuttle" (no digits) would pass the check. Only the prompt rule stands in the way.
- **Offline tests reflect the mock.** They show that the code gates, filters and validates correctly. Only the live runs in `golden.md` show what Gemini does.

## Human verification checklist (to do before submitting)
- [ ] Read `src/pipeline.py` guardrails and `src/prefilter.py` line by line.
- [x] Live run of the three golden cases with real `usage` in `golden.md`: done by the agent on 2026-10-15, still to be reviewed by me.
- [ ] Try one adversarial non-numeric hallucination prompt live and record the result.
  *(Update 2026-11-24: attempted as team golden question g5, "Do you provide a free airport shuttle?". Both live attempts hit a Gemini outage (HTTP 500/503, timeouts), so the result is still unobserved. See `evals/results/README.md` at the repo root.)*
- [ ] Run `src/bench.py --n 20` to complete spec criterion 5. This needs a fresh daily quota or a paid key.

## Manual line-by-line sign-off (Luka Dumbadze)
> **PENDING.** @Luka-Dumbadze must complete this personally. An agent must not tick these boxes or fill in the signature.

| File | Read line by line | Date | Issues found / notes |
|---|---|---|---|
| **Required for rung 3:** `src/pipeline.py` (room gate, priority override, grounding) | [ ] | | Known since Week 4: urgent keywords over-escalate ("water", "o'clock", "door"); see root `docs/decisions/0001-room-gate-in-code.md` |
| **Required for rung 3:** `src/prefilter.py` (room extraction/validation, section selection) | [ ] | | |
| `src/llm.py` (prompt, provider table, 3-call budget) | [ ] | | |
| `src/schemas.py` (output validation) | [ ] | | |
| `golden.md` live outputs match what I would sign off on | [ ] | | |

I confirm that I have read the code above line by line and understand what it does: **Signature:** __________ **Date:** __________
