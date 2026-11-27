# Pattern Journal · UrjuHub · Weeks 5 to 7

*One entry per week: the pattern, one place I saw or used it, one thing I would do differently. Two to three sentences per entry, in my own words: no AI-written text (originality rules apply). `docs/journal/UrjuHub.md` on `main` holds Weeks 1–4; Weeks 5–7 are written here.*

## Week 5 · Tool Contract · 2026-11-27

I used the Tool Contract pattern in `my_open_tasks` by giving it an empty `MyOpenTasks` contract (`extra="forbid"`) with no `room` field, so the room always comes from the session (`X-Room` or `STUMAROS_ROOM`) instead of the model. When I added `room` to the contract for the red run, three checks failed—even though the function still read room 204 from the session and returned `{"room": "204", "tasks": []}`, the schema was already telling the model it could pick a room, so one future edit reading `args.room` would have exposed another guest's tasks. Next time, I would write the adversarial and contract tests first so any schema leak gets caught before wiring the tool in.

## Week 6 · Session State · 2026-11-27

Right now, the repo has no `docs/state-contract.md`, `src/memory.py`, or `DELETE /me/memory`—the only state is the in-memory `SERVICE_TASKS` list in `src/tools.py` that `my_open_tasks` reads. Because it only lives in process memory, open tasks disappear whenever the server restarts and never get cleared when a guest checks out. If I were building this properly, I would tie task state to a guest's active stay and clear or archive it automatically at check-out.

## Week 7 · Supervised Autonomy Loop · 2026-11-27

The loop in `src/act.py` caps execution at `MAX_ROUNDS = 3`, though `NEEDS_YES` and `confirm()` are not implemented in the repo yet. Because `my_open_tasks` only reads the caller's own tasks, it is safe to run without asking, while something like `request_late_checkout` (20 GEL) changes state and charges money so it would need a confirmation step first. Going forward, I would tag read-only tools separately from paid or state-changing ones in the contract layer so anything with real side effects always pauses for guest approval.
