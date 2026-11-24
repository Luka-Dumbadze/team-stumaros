# Confidence policy · Guest message triage (StumarOS)

*From `Lab-3/templates/confidence-policy.md`, filled in for a text feature: v1 has no image input ([decision 0004](decisions/0004-text-only-v1.md)). This table is what the code must implement. Today it is implemented inside `apply_guardrails()` and `triage()` in `src/pipeline.py`, without explicit route names. The "Today" notes mark the differences. Owner: [@Luka-Dumbadze](https://github.com/Luka-Dumbadze).*

## 1 · Routes

| Route | What it means | What the guest sees | What gets created |
|---|---|---|---|
| `accepted` | the room is valid (or no service was requested), the reply uses only the policy sections sent, and the model output passed validation | the reply as written, in the guest's language | the dispatch tasks, with the room attached by code |
| `confirm` | soft flags only: the guest left something out | the answer to any policy question, plus one question: room number and booking name | nothing until the guest replies. *Today: no draft is kept; v1 has no session state (Week 6).* |
| `review` | at least one hard flag: the room cannot be trusted, the reply is ungrounded, or the model failed | a verification request, a front-desk escalation, or the fallback (section 4); never an invented answer | no task. *Today: no staff review queue exists. `POST /chat` (Week 5+) must surface these to the front desk.* |
| `rejected` | the guide does not answer the question (the Lab 4 refusal path) | "not available" plus an offer of the front desk | nothing |

## 2 · Signals

Self-rated confidence is **not used at all**. We never ask the model for a confidence number. Every signal below is computed by code, and the evidence checks run before any model output is trusted.

| Field | Signal | Condition | Flag | Hard or soft |
|---|---|---|---|---|
| room | value present | no room in the payload or the message | `missing` | soft |
| room | one source | payload and message name different rooms | `conflicting_rooms` | soft |
| room | exists | not in `data/active_rooms.json` | `unknown` | hard |
| room | checked in | `status != "checked_in"` | `not_checked_in` | hard |
| room | stay is current | today outside `check_in..check_out` | `outside_stay_dates` | hard |
| reply | policy found | no guide section matched a question | `no_policy` | `rejected` |
| reply | numbers grounded | a time or price not in the sent sections, the room or the message | `unsupported_numbers` | hard |
| reply | citations real | cites a section that was not sent | `cited_unsent` | soft. *Today: logged only; the reply is not changed.* |
| reply | non-numeric claims grounded | "yes, we have a shuttle" | none | **not checked in code**; prompt rule only (golden g5) |
| output | schema valid | invalid JSON or schema after 1 corrective retry | `model_failed` | hard |
| output | answered at all | 3 calls failed (5xx, 429, timeout), or the prompt is over the 1,200-token budget | `model_failed` / `budget` | hard |
| task | priority | leak, lock, door or AC keywords | override to `urgent` | not a flag; code sets it ([decision 0001](decisions/0001-room-gate-in-code.md)) |

Order:
1. Room status is checked before the model call (`src/prefilter.py`).
2. Model output is schema-checked before any guardrail runs.
3. Numbers are checked before the "no policy" escalation.

## 3 · From flags to a route

```
model_failed or budget                            → review    reply = FALLBACK, no tasks
room flag (any) and the model proposed a service  → confirm if every room flag is soft, else review
                                                    tasks dropped; VERIFY appended if the reply lacks a room-number request
unsupported_numbers                               → review    reply replaced by ESCALATE (+ VERIFY if a service was asked)
no_policy for a question                          → rejected  ESCALATE appended if the reply lacks "front desk"
no flags                                          → accepted
```

## 4 · The text the guest reads

These are exact strings from `src/pipeline.py`. Everything else is the model's own wording, already checked by the rules above.

| Flag | On screen |
|---|---|
| `missing`, `conflicting_rooms`, `unknown`, `not_checked_in`, `outside_stay_dates` | "Before we send anyone, please confirm your room number and the name on the booking." (`VERIFY_EN`) |
| `no_policy`, `unsupported_numbers` | "I don't have that information; I can ask the front desk to help you." (`ESCALATE_EN`) |
| `model_failed`, `budget` | "Sorry, I couldn't process your message automatically. I've flagged it for the front desk, who will reply shortly." (`FALLBACK_EN`) |

*Gaps in this text:*
- `FALLBACK_EN` says "flagged for the front desk", but nothing notifies staff yet. Fix the wording or add the notification when `POST /chat` lands.
- The soft and hard room flags show the same sentence today.
- The strings are English. The model replies in Georgian, but these appended sentences do not.

## 5 · Tests (in `tests/`, no API calls)

1. `accepted`: `test_valid_room_task_gets_room_from_code_not_model`, `test_golden_georgian_happy_path`.
2. `confirm`: `test_golden_missing_room_asks_for_clarification`, `test_conflicting_payload_and_message_rooms_are_not_trusted`.
3. `review` (room): `test_tasks_dropped_for_invalid_room_even_if_model_proposes_them` (unknown, checked-out and expired rooms); `test_golden_after_hours_pool_from_checked_out_room`.
4. `review` (reply and model):
   - `test_invented_time_replaces_reply`
   - `test_transient_errors_capped_at_three_calls`
   - `test_second_schema_failure_stops_and_falls_back`
   - `test_over_budget_prompt_is_refused_before_any_call`
5. `rejected`: `test_unanswerable_question_gets_escalation`, plus golden g5 (`evals/golden.yaml`).
6. Order: room status first, so a model that proposes a task for an invalid room is overruled (`room_gate: dropped` event).

## 6 · What we measure once it runs

- **Share of requests per route.** *Today the route is not logged.* Follow-up: add `route` and `flags` to the `logs/usage.jsonl` record so the share can be computed. If more than 30% go to `confirm` or `review`, the room extraction is too strict, or guests are not being asked for the room up front.
- **Wrong accepts:** a task dispatched to the wrong room, or an invented amenity a guest repeats to staff. Each one becomes a golden question or a test.
- **Wrong reviews:** valid guests asked for their room twice. The rules are revisited after twenty real conversations, and the change is recorded in `docs/decisions/`.
