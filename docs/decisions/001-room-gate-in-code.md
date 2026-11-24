# ADR 001 · Room gate and urgent escalation are enforced in code, not in the prompt

- **Status:** Accepted (Week 3, HW1; recorded Week 4)
- **Owner:** [@Luka-Dumbadze](https://github.com/Luka-Dumbadze)
- **Code:** `src/pipeline.py` (`apply_guardrails`, `apply_priority_override`), `src/prefilter.py` (`resolve_room`, `validate_room`)

## Context
A dispatched task sends a real person to a real room. Two failure modes cost money or safety:
1. **A task for a room that isn't occupied.** The room could be checked out, reserved, outside its stay dates or unknown, or a prankster could name someone else's room. The rule in `AGENTS.md`: a room is valid only if `status == "checked_in"` and `check_in <= today <= check_out`.
2. **A safety issue filed at the wrong priority.** Water leaks, door/lock failures and AC outages must be `urgent`. Extra supplies must never be.

The prompt states both rules (rule 4: "if room.status is not valid, do not promise the service"). But a prompt rule is a request, not a guarantee. In the HW1 live run, `gemini-3.8-flash` proposed a maintenance task for *"The AC isn't working…"* even though no room was given, ignoring rule 4 (`hw1/Luka-Dumbadze/golden.md`, case 3, run 7).

## Decision
The model **proposes**; code **decides**.
- Code extracts the room (regex over the message plus the payload). If the two disagree, the result is `conflicting_rooms` and nothing is trusted. Code then validates the room against `data/active_rooms.json` before any model call. The model sees only `{number, status}` and never another guest's record or name.
- The model's proposed tasks carry **no room field**. Code attaches the validated room. If the room status is anything other than `valid`, every proposed task is dropped, `room_validated` is `false`, and a verification request (room number + booking name) is appended if the reply lacks one.
- After validation, `apply_priority_override` forces leak/water/lock/door/AC tasks to `urgent` and downgrades supply tasks from `urgent` to `normal`. The model's priority is only a proposal.
- An early agent suggestion to let the model decide priority dynamically was **rejected**.

## Consequences
- **Good:** a prompt-injected or careless model reply cannot dispatch staff to an unverified room. Evidence:
  - parametrised tests over every room status (`tests/test_feature.py`);
  - golden cases G2 and G3 (`evals/golden.yaml`);
  - live HW1 case 3, where the gate dropped the model's task;
  - a deliberate breakage of the gate, which failed 6 tests.
- **Cost:** a legitimate guest who forgets the room number gets one clarification round-trip, which is the intended UX ([ADR 004](004-multimodal-and-confidence-policy.md)).
- **Known issue (found while writing this ADR, not yet fixed):** the urgent keywords are unanchored substrings, so they over-escalate. These task texts all become `urgent`:
  - "Deliver 2 bottles of `water`"
  - "Wake-up call at 7 o'c`lock`"
  - "Leave towels outside the `door`" (the urgent check runs before the supply downgrade)

  Over-escalation is the safer direction, but it wastes the 15-minute urgent channel. Follow-up: add word boundaries and an intent check (a failure, not a mention), with regression tests.
- Keyword lists are English plus a few Georgian stems. Any other language falls back to the model's priority.
