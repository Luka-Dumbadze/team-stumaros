# Pattern Journal · UrjuHub · Weeks 5 to 7

*One entry per week: the pattern, one place I saw or used it, one thing I would do differently. Two to three sentences per entry, in my own words: no AI-written text (originality rules apply). `docs/journal/UrjuHub.md` on `main` holds Weeks 1–4; Weeks 5–7 are written here.*

## Week 5 · Tool Contract · <<date>>

<<2-3 sentences in your own words. Cover: (1) where you used it: `my_open_tasks`, an empty `MyOpenTasks` contract with no `room` field, room comes from `X-Room` / `STUMAROS_ROOM`; (2) what you noticed: the red run, 3 checks failed when `room` was added; (3) what you would do differently.>>

*Closest real code in the repo (delete this list before submitting):*
- `src/contracts.py`: `MyOpenTasks` (line 58), `Contract` with `extra="forbid"` (line 43).
- `src/tools.py`: `my_open_tasks` (line 123); `src/mcp_server.py`: `my_open_tasks` (line 59).
- `evals/tools/UrjuHub.yaml`, product PR #12, your red-run PR.

## Week 6 · Session State · <<date>>

<<2-3 sentences in your own words. Honest facts to build on: the repo has no `docs/state-contract.md`, no `src/memory.py` and no `DELETE /me/memory` yet. The only state is `SERVICE_TASKS` in `src/tools.py` (line 89), in process memory, which `my_open_tasks` reads: it disappears on restart, and tasks are never closed or cleared at check-out.>>

## Week 7 · Supervised Autonomy Loop · <<date>>

<<2-3 sentences in your own words. Honest facts to build on: the repo has no `NEEDS_YES` and no `confirm()` yet. The loop in `src/act.py` has `MAX_ROUNDS = 3`. `my_open_tasks` only reads, so it is safe to run without a yes; `request_late_checkout` (20 GEL) is the one that would need approval.>>
