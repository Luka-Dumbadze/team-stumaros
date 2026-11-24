# 0001 · Room gate and urgent escalation live in code, not in the prompt

**Date:** Week 3 (HW1), recorded Week 4 · **Decided by:** Luka Dumbadze

**Context.** A dispatched task sends a person to a room. `AGENTS.md` says a room is valid only if `status == "checked_in"` and `check_in <= today <= check_out`, and that leaks, door/lock and AC faults are `urgent`. The prompt states both rules, but in the HW1 live run `gemini-3.8-flash` still proposed a maintenance task for *"The AC isn't working…"* with no room given (`hw1/Luka-Dumbadze/golden.md`, case 3).

**Decision.** The model proposes, and code decides:
- `src/prefilter.py` resolves and validates the room before the model call. The model sees only `{number, status}`.
- `apply_guardrails` in `src/pipeline.py` attaches the room to tasks and drops every task unless the status is `valid`.
- `apply_priority_override` in the same file forces safety keywords to `urgent` and keeps supplies out of `urgent`.

**Alternatives.**
- Prompt rules only: the HW1 live run shows the model ignoring them.
- Letting the model set priority: an agent suggested it, and it was rejected because safety priority must not depend on wording.
- An extra confirmation turn before every dispatch: slower for valid guests, and still trusts the model's room.

**Consequences.**
- A careless or injected reply cannot dispatch staff to an unverified room. Evidence: the parametrised room-status tests in `tests/test_feature.py`, golden g2 and g3, and a deliberate gate breakage that failed 6 tests.
- Guests without a room number get one clarification round-trip (`docs/confidence-policy.md`).
- **Known bug (Week 4, not fixed):** the urgent keywords have no word boundaries. "Bottles of *water*", "7 o'c*lock*" and "towels outside the *door*" become `urgent`. Fix with word boundaries, a fault-intent check and regression tests.
