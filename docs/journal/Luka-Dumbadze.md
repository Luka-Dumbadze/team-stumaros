# Pattern Journal · Luka Dumbadze (@Luka-Dumbadze)

*Rename this file to your GitHub username. Same format as `Lab-1/templates/pattern-journal.md`: if you started one in Lab 1, move its entries here. One entry per week, 2 to 3 sentences: pattern · where I applied it · what I delegated to AI · how I verified it. Graded only inside HW1 (Weeks 1 to 4), HW2 (Weeks 5 to 7) and one Repository Review line (Weeks 10 to 14).*

> **Assembled 2026-11-24 from entries already committed. Every entry is copied verbatim, by script, with its source labelled.** No new prose was written.
> - **Lab 1 journal:** `docs/pattern-journal.md`, W1–W2.
> - **HW1 journal:** `hw1/Luka-Dumbadze/journal.md`, W1–W4.
>
> **Provenance, for @Luka-Dumbadze to confirm:** `hw1/Luka-Dumbadze/delegation.md` records that the agent wrote "the first drafts of this log and the journal". Before grading, confirm each entry is in your own words, rewrite any that are not, and keep one version per week. Weeks 5+ are yours to write.

## Week 1 · Context as Budget

*Source: Lab 1 journal (`docs/pattern-journal.md`)*

**W1 · Context as Budget** · Applied to the context list and session memory constraints in `docs/spec.md` and `AGENTS.md`. I delegated an initial context list to the model; it proposed retaining full guest stay history and live PMS sync, which I cut to keep token costs within our $5.30/month napkin estimate. Verified by enforcing a strict 4-turn (8-message) memory cap and confirming that only `hotel_guide.json` and `active_rooms.json` enter the prompt.

*Source: HW1 journal (`hw1/Luka-Dumbadze/journal.md`)*

**W1 · Context as Budget** · `src/prefilter.py`: the prompt gets at most 3 keyword-matched policy sections and 1 room number with its status. The rest of the guide and the guest list never leave the server, and guest names are never sent at all. Delegated the pre-filter and token estimator to Claude Code. Verified by a test asserting that unrelated sections and every guest name are absent from the built prompt, a hard 1,200-token ceiling checked before any call, and the estimator: 397–465 tokens filtered vs ≈ 2,560 unfiltered (≈ $14/month vs ≈ $4–5/month at 200 req/day on Gemini 3.8 Flash, before the 2–4x Georgian penalty).

## Week 2 · Spec Before Code

*Source: Lab 1 journal (`docs/pattern-journal.md`)*

**W2 · Spec Before Code** · Wrote `docs/spec.md` and `AGENTS.md` contracts before writing a single line of backend code. Delegated a critique of our success criteria to Claude Code; it caught that auditing our "≤3 model calls" rule was impossible without adding `request_id` to logs, but also attempted scope creep by proposing an LLM-as-a-judge system. Verified by rejecting the LLM judge in favor of deterministic regex fixtures, adding `request_id` across both documents, and ensuring all 24 golden scenarios have explicit distributions.

*Source: HW1 journal (`hw1/Luka-Dumbadze/journal.md`)*

**W2 · Spec Before Code** · `spec.md` (feature boundary, budget, napkin math, 5 falsifiable criteria) was written before anything in `src/`, on top of the team spec I had already critiqued. In that critique I rejected the AI's LLM-as-judge grading in favour of deterministic regex fixtures, and dropped the extra confirmation turn before dispatch. Verified by mapping each test in `test_feature.py` to a numbered acceptance criterion. The latency criterion stayed "pending" until it could be measured live, and it is now recorded as a FAIL (p95 8.36 s against 2.5 s) rather than relaxed to pass.

## Week 3 · Uncertainty-Aware UX

*Source: HW1 journal (`hw1/Luka-Dumbadze/journal.md`)*

**W3 · Uncertainty-Aware UX** · When the room is missing, unknown, checked out, outside its stay dates, or when the payload and the message name different rooms, the system emits no task and asks for room number and name instead of guessing (`room_gate` in `src/pipeline.py`). Delegated the gate and the conflict rule. Verified by parametrised tests over all five room statuses, golden case 3 (AC broken, no room → clarification, no dispatch), and a deliberate breakage of the gate in a temp copy, which failed 6 tests. Live, `gemini-3.8-flash` proposed a maintenance task for that no-room message anyway, and the gate dropped it.

## Week 4 · Grounded Generation

*Source: HW1 journal (`hw1/Luka-Dumbadze/journal.md`)*

**W4 · Grounded Generation** · The model sees only the selected sections and must cite them. Code rejects citations of unsent sections, replaces any reply containing a number absent from the policy text or the guest's message, and appends a front-desk escalation when no policy matched. Delegated the checks. Verified with tests (invented "24:00" pool time → reply replaced; guest's own "23:30" allowed) and a breakage that removed the number check (1 test failed). Live on `gemini-3.8-flash` (`golden.md`), every number in the recorded English and Georgian replies came from the guide or the guest's message. Honest gap: non-numeric hallucinations ("yes, we have a shuttle") are only blocked by the prompt, and the live shuttle replies were not recorded before the free-tier quota ran out.
