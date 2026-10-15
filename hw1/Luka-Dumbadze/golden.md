# Golden Cases · Guest Request Triage · Live

**Run date:** 2026-10-15 · **Model:** `gemini-3.8-flash` via Google AI Studio's OpenAI-compatible endpoint (free tier) · T = 0.1 · `reasoning_effort="none"` · `max_tokens=300`
**Command (one fresh process per case):** `.venv/bin/python -m hw1.Luka-Dumbadze.src.main --today 2026-10-15 --query "<input>"`
**Latency** is `usage.latency_ms`, measured in-process end to end: pre-filter, every model call and retry backoff. Process wall time, which adds ~0.6 s of Python start-up, is shown in brackets. Tokens are the API's `usage` numbers, not estimates.

> **Why not `gemini-2.5-flash`?** It was the requested default, but the API answered HTTP 404: *"This model models/gemini-2.5-flash is no longer available to new users. Please update your code to use models/gemini-3.8-flash."* `gemini-1.5-flash` is not served at all. 3.8 Flash is also the model the spec already priced.

## Run log: every live run, in order
| # | What | Result | Calls | Tokens in / out / total | Latency |
|---|---|---|---|---|---|
| 1 | Case 1 on `gemini-2.5-flash` | HTTP 404, fallback reply | 1 | 0 / 0 / 0 | 0.61 s (1.24) |
| 2 | Case 1 on `gemini-3.8-flash`, default thinking | **FAIL**: JSON cut off after a few characters on both completions; the corrective retry timed out at 10 s; fallback reply | 3 | 973 / 11 / 1,559 | 25.26 s (25.90) |
| 3 | Diagnostic outside the CLI: same prompt, `reasoning_effort="none"` | valid JSON, 0 hidden tokens | 1 | 463 / 183 / 646 | 6.47 s |
| 4 | Case 1 (thinking off from here on) | **PASS** | 1 | 463 / 145 / 608 | 5.35 s (5.98) |
| 5 | Case 2 | **PASS** | 1 | 466 / 89 / 555 | 6.22 s (6.87) |
| 6 | Case 3 | **FAIL**: 3× HTTP 500 from Google, fallback reply | 3 | 0 / 0 / 0 | 9.46 s (10.12) |
| 7 | Case 3 re-run | **PASS** | 1 | 391 / 83 / 474 | 5.01 s (5.64) |
| 8 | Benchmark, 10 requests | see below | 21 | see below | see below |

Run 2: total 1,559 − prompt 973 − completion 11 = **575 hidden thinking tokens**, which is roughly two completions' worth of the 300-token budget. Thinking consumed `max_tokens` before the JSON was written. The code now sends `reasoning_effort="none"` for Gemini and reports `finish_reason=length` as truncation. A test pins both.

## Case 1 · Happy path, Georgian, composite (question + service): PASS (run 4)
**Input:** `გამარჯობა! ოთახი 204-ში 2 დამატებითი ბალიში გვჭირდება. როდემდეა საუზმე?` ("Hi! We need 2 extra pillows in room 204. Until when is breakfast?")
**Expected:** room 204 is valid; one task `{204, housekeeping, normal, 2 extra pillows}`; reply gives breakfast hours from the guide, in Georgian; only the breakfast and housekeeping sections are sent.
```json
"reply": "გამარჯობა! თქვენს ოთახში 2 დამატებით ბალიშს 30 წუთში მოგართმევენ. საუზმე კი ყოველდღე 07:00-დან 10:30 საათამდე პირველ სართულზე მდებარე კაფეშია ხელმისაწვდომი.",
"tasks": [{"room": "204", "department": "housekeeping", "priority": "normal", "task": "Deliver 2 extra pillows to room 204"}],
"room_validated": true, "sections_sent": ["breakfast", "housekeeping"], "guardrail_events": []
```
Reply in English: "Hello! 2 extra pillows will be brought to your room within 30 minutes. Breakfast is available daily from 07:00 to 10:30 in the café on the first (ground) floor."
**Metrics:** 1 call · 463 in / 145 out / 608 total · 5.35 s (5.98 s).
**Notes:**
- Every number in the reply (2, 30, 07:00, 10:30) comes from the guide or the message, so the grounding check raised nothing.
- Georgian costs output tokens: 145 for two sentences, against 89 for the longer English reply in case 2.

## Case 2 · Policy violation: after-hours pool + request from a checked-out room: PASS (run 5)
**Input:** `Room 305 here. Can we use the pool at 23:30 tonight? Also please send 2 towels.`
**Expected:** room 305 is `checked_out`, so `tasks: []` and the reply asks for room number and name; the reply gives the pool hours (08:00-22:00) instead of allowing 23:30.
```json
"reply": "The pool is open from 08:00 to 22:00 and is closed outside these hours with no exceptions. Before we can send the towels to Room 305, could you please confirm your room number and the name on your booking?",
"tasks": [], "room_validated": false, "room_status": "not_checked_in", "needs_clarification": true,
"sections_sent": ["pool", "housekeeping"], "guardrail_events": []
```
**Metrics:** 1 call · 466 in / 89 out / 555 total · 6.22 s (6.87 s).
**Notes:**
- Unlike the mock, the live model followed prompt rule 4 here and proposed no task, so the room gate had nothing to drop.
- The refusal of 23:30 is implicit: "closed outside these hours with no exceptions".

## Case 3 · Ambiguous input: maintenance issue with no room: FAIL (run 6), then PASS (run 7)
**Input:** `The AC isn't working and it's really hot, please help!`
**Expected:** no room can be resolved, so no task and no guess; the reply asks for room number and name; `needs_clarification: true`.

**Run 6: FAIL.** Google returned HTTP 500 on all three calls. The 3-call cap held and no task went out. But the guest got "Sorry, I couldn't process your message…" instead of a clarifying question, after 9.46 s.

**Run 7: PASS.**
```json
"reply": "I am sorry to hear your AC is not working. Could you please provide your room number and the name on your booking so we can send maintenance right away?",
"tasks": [], "room": null, "room_validated": false, "room_status": "missing", "needs_clarification": true,
"sections_sent": ["maintenance"],
"guardrail_events": ["room_gate: dropped 1 task(s), room status 'missing'"]
```
**Metrics:** 1 call · 391 in / 83 out / 474 total · 5.01 s (5.64 s).
**Note:** the model **proposed a maintenance task anyway**, ignoring prompt rule 4. The code's room gate dropped it. This is the clearest live evidence for keeping the room decision in code.

## Latency benchmark (`src/bench.py`, n = 10)
Five messages × 2: the 3 golden inputs, "What's the Wi-Fi password?" and "Do you have an airport shuttle?". A fresh client per request; request starts 12 s apart.

| # | Message | Latency | Calls | Tokens in / out | Outcome |
|---|---|---|---|---|---|
| 1 | Georgian composite | 7.33 s | 1 | 463 / 139 | answer, 1 task |
| 2 | Pool + room 305 | 5.33 s | 3 | 466 / 96 | answer after 2× HTTP 500 |
| 3 | AC, no room | 3.77 s | 1 | 391 / 62 | answer (no task proposed this time) |
| 4 | Wi-Fi | 8.36 s | 1 | 372 / 65 | answer |
| 5 | Shuttle | 2.71 s | 1 | 339 / 67 | answer (reply text not recorded) |
| 6 | Georgian composite | 6.17 s | 2 | 463 / 135 | answer after 1× HTTP 500, 1 task |
| 7 | Pool + room 305 | 3.16 s | 3 | 0 / 0 | fallback: HTTP 500, then 429 ×2 |
| 8–10 | AC / Wi-Fi / shuttle | 2.29–2.62 s | 3 each | 0 / 0 | fallback: 429 ×3 (daily quota) |

| Set | n | p50 | p95 | max | under 2.5 s |
|---|---|---|---|---|---|
| **Model answered** | 6 | **5.33 s** | **8.36 s** | 8.36 s | **0** |
| All requests, fallbacks included | 10 | 3.16 s | 8.36 s | 8.36 s | 2 (both were 429 fallbacks) |
| All successful live answers today (benchmark + final golden runs) | 9 | 5.35 s | 8.36 s | 8.36 s | 0 |

Percentiles are nearest-rank, so with n ≤ 20, p95 is the maximum. The script's original summary line reported the "all requests" row only. Its p50 of 3.16 s is flattered by fast 429 failures, so `bench.py` now prints both rows.

**Verdict: spec criterion 5 fails.** p95 is 8.36 s against a 2.5 s target, and even the fastest successful answer (2.71 s) misses it. n = 10 is below the spec's 20 runs. But with 0 of 9 successful answers under 2.5 s, the verdict is very unlikely to flip without a change such as a paid tier, shorter replies or streaming.

**Reliability:**
- **Free-tier limit:** 20 generate requests per day per model (`GenerateRequestsPerDayPerProjectPerModel-FreeTier`), and failed calls count against it.
- **How today's 20 calls went:** 10 valid answers, 7 HTTP 500s, 2 truncated completions and 1 timeout. The quota ran out at benchmark request 7, and the reset is about 9 h later.
- **What that means for the spec's benchmark:** a 20-run benchmark needs up to 60 calls with retries. That is more than one day of free quota; it needs a paid key or OpenRouter.

## Spec acceptance criteria, as measured
| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Strict output, ≤ 3 calls | **PASS** | Every run returned a valid result. All 10 model answers with thinking off passed schema validation on the first parse; with thinking on, 0 of 2 did (run 2). No request exceeded 3 calls. |
| 2 | Room gate | **PASS** | Case 2: checked-out room, no task. Case 3: missing room, and the model's proposed task was dropped in code. |
| 3 | Context budget | **PASS** | Prompts of 339–466 tokens against a 1,200 ceiling, with only the matched sections sent. The estimator was within ~3% (465 / 452 / 399 estimated vs 463 / 466 / 391 real). |
| 4 | Grounding | **PASS on observed runs** | No unsupported-number events. The check is numbers-only, and the shuttle replies were not recorded, so `bench.py` now records replies. |
| 5 | p95 < 2.5 s | **FAIL** | p95 8.36 s, p50 5.33 s (successful answers, n = 6). |

**Earlier offline finding:** the mock-mode golden run found the Georgian pre-filter bug, where `აუზ` matched inside `საუზმე`. It was fixed before going live; see `delegation.md` item 1. **Tests:** 38 passed in `.venv`; 35 passed and 3 skipped offline without `openai`.

## Reproduce
```bash
.venv/bin/python -m hw1.Luka-Dumbadze.src.main --today 2026-10-15 --query "<input>"
.venv/bin/python -m hw1.Luka-Dumbadze.src.bench --n 20 --gap 12   # 20-60 calls: more than one free-tier day
```
