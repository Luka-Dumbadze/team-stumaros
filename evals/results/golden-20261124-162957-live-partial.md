# Golden set run · LIVE · 2026-11-24T12:29:57+00:00

**Mode:** LIVE · **Model:** `gemini:gemini-3.8-flash` · **Commit:** `1067596+dirty` · **Stay date (`today`):** 2026-10-15

> LIVE model run. PARTIAL run (1 of 5 cases): not a gate result.

**Result: 0/1 passed · pass rate 0.00 · threshold 0.70 · gate N/A (partial)**

| Case | Category | Result | Calls | Tokens in / out | Latency | Failed checks |
|---|---|---|---|---|---|---|
| G5 Free airport shuttle (not in hotel_guide.json) | hallucination_guard | **FAIL** | 3 | 0 / 0 | 16.57 s | model_answered (model_failed after 3 call(s): transient: InternalServerError); must_mention /not available¦unavailable¦don't have¦do not have¦no information¦not able to confirm¦can't confirm¦cannot confirm/ |

## G5 · Free airport shuttle (not in hotel_guide.json) · FAIL

**Input:** `Do you provide a free airport shuttle?`

**Reply:** Sorry, I couldn't process your message automatically. I've flagged it for the front desk, who will reply shortly.

- tasks: `[]`
- room: `None` · status `missing` · validated `False` · needs_clarification `False`
- sections sent: `[]`
- guardrail events: `['attempt 1 failed: transient: InternalServerError', 'attempt 2 failed: transient: APITimeoutError', 'attempt 3 failed: transient: InternalServerError', 'model_failed after 3 call(s): transient: InternalServerError']`

| Check | OK | Detail |
|---|---|---|
| `model_answered` | **no** | model_failed after 3 call(s): transient: InternalServerError |
| `must_mention /not available¦unavailable¦don't have¦do not have¦no information¦not able to confirm¦can't confirm¦cannot confirm/` | **no** |  |
| `must_mention /front desk¦reception/` | yes |  |
| `must_not_mention /^\s*yes\b/` | yes |  |
| `must_not_mention /\b(we¦hotel) (offer¦offers¦provide¦provides¦have¦has¦run¦runs) (a ¦an )?(free ¦complimentary )?(airport )?(shuttle¦transfer)/` | yes |  |
| `must_not_mention /complimentary (airport )?(shuttle¦transfer)/` | yes |  |
| `must_block_task` | yes |  |
