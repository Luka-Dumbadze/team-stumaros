# Pattern Journal · Luka-Dumbadze · Weeks 5 to 7

*Copied from [`docs/journal/Luka-Dumbadze.md`](../../docs/journal/Luka-Dumbadze.md). One entry per week: the pattern, one place I saw or used it, one thing I would do differently. Two to three sentences per entry, in my own words: no AI-written text (originality rules apply).*

## Week 5 · Tool Contract

- **Where I used it:** On `lookup_policy` (Lab 5) and `create_service_task` (HW2), keeping `room` out of the Pydantic contract (`extra="forbid"`) and injecting the verified room from the `X-Room` header or `Resolve(verified_caller_room)`.

-  **What I noticed:** When I deliberately added `room` back to CreateServiceTask on the throwaway PR, 5 CI checks failed and blocked the merge, while our internal room-number check inside `create_service_task` still blocked the adversarial prompt `"room 410"`.

- **Do differently:** Next time I would test the weakened contract before adding the extra regex guard inside the tool function, so I can verify each defense layer separately.

## Week 6 · Session State

**Where I used it:** [Fill in your own words, after the Week 6 lecture]. **What I noticed:** [ ]. **Do differently:** [ ].

## Week 7 · Supervised Autonomy Loop

**Where I used it:** [Fill in your own words, after the Week 7 lecture]. **What I noticed:** [ ]. **Do differently:** [ ].
