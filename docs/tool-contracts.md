# Tool contracts · StumarOS

*From `Lab-5/templates/tool-contract.md`. One section per tool. Every rule in this table exists in code: the contract class (`src/contracts.py`), the tool body (`src/tools.py`) or the registry (`TOOLS`, `tools_for()`). Lab 5 shipped `lookup_policy`; HW2 owners (table at the bottom) each add one more. `create_service_task` is the first.*

## `lookup_policy`

**In one sentence, for the model:** Read one section of the hotel guide, word for word. Reads only; changes nothing.

| | |
|---|---|
| **Effect** | reads |
| **Undo** | nothing to undo |
| **Idempotent?** | yes: it changes nothing |
| **Offered to** | everyone, including visitors without a verified room (`tools_for(None)` includes it) |
| **Identity from** | not needed: the guide is the same for every caller. The room is still verified and logged as a hash, because the same loop serves room tools |
| **Touches** | `data/hotel_guide.json`, read only, one section per call |
| **Must never** | answer from anything but the guide's own text, or reveal anything about rooms or guests. There is deliberately **no occupancy lookup tool** (such as `check_room`): telling a visitor which rooms are occupied leaks guest data |

**Inputs.** Unknown fields are refused (`extra="forbid"`).

| Argument | Type | Constraint | Description the model reads |
|---|---|---|---|
| `section` | string | one of `breakfast`, `pool`, `checkout`, `wifi`, `parking`, `housekeeping`, `maintenance`, `quiet_hours`, `pets` (`SectionId`; a test fails if this drifts from `data/hotel_guide.json`) | One section of the hotel guide |

There is no `room` or `guest` argument. A model that sends one is refused (function calling) or ignored (MCP).

**Result.** `section` (string) and `text` (string, the guide's words unchanged). No file path and no internal ids.

**Expected failures.** Each raises `ToolFailure` with a message the model can act on.

| When | Message the model reads (what happened, what to do next) |
|---|---|
| the contract allows the id but the guide no longer has that section | The hotel guide has no '`pool`' section right now. Say the information is not available and offer to ask the front desk. |
| any id outside the fixed set (`spa`, `airport_shuttle`, `Pool`) | refused before the tool runs: `invalid arguments: section: Input should be 'breakfast', 'pool', …` |

**Tests and golden cases**

| Case | Expect | Where |
|---|---|---|
| a valid call (`wifi`, visitor) | runs, text contains the network name | `tests/test_act.py::test_valid_call_runs_and_returns_data`, golden `team:p1` |
| a guest in a verified room | runs, same answer | golden `team:p2` |
| a topic the guide lacks (`airport_shuttle`) | refused before the tool runs | golden `team:p3` |
| invalid arguments (`Pool`, `../../.env`, truncated JSON) | refused before the tool runs | `tests/test_contracts.py`, `test_invalid_arguments_never_reach_the_tool`, golden `team:b1` |
| not offered to this caller | refused, nothing runs | `tests/test_act.py::test_a_tool_not_offered_is_not_run` (room tool, visitor) |
| identity in the arguments (`room: "305"`) | refused (function calling), ignored (MCP) | `test_model_cannot_choose_the_room`, `tests/test_mcp.py::test_an_extra_room_argument_never_reaches_the_tool`, golden `team:a1` |
| adversarial: a path in the id (`../../.env`) | refused | golden `team:a2` |
| the server as a host launches it (real `python -m src.mcp_server` stdio subprocess) | lists `lookup_policy`; a valid call returns the text; `airport_shuttle` comes back as an error result | `tests/test_mcp.py::test_the_server_starts_as_a_real_stdio_subprocess` |

**Log line.** `logs/tools.jsonl`, one line per call: `ts`, `tool`, the raw `arguments`, `ok`, `error`, `room` (a 12-character hash of the verified room, or null), `latency_ms`. It deliberately leaves out the room number and any guest name. The model call that requested the tool is logged separately in `logs/usage.jsonl`.

---

## `create_service_task` (HW2 · @Luka-Dumbadze · issue #3)

**In one sentence, for the model:** File one housekeeping or maintenance request for the guest's own room. Adds a task for staff; never changes or cancels one. The hotel sets the priority from the text (leaks, door, lock and AC faults are urgent), so do not ask the guest for one.

| | |
|---|---|
| **Effect** | adds: one task in the in-memory queue `tools.SERVICE_TASKS` (AGENTS.md: no storage files) |
| **Undo** | staff close or cancel it at the front desk. There is deliberately no cancel tool |
| **Idempotent?** | yes: the same department and text again (ignoring case and spacing) returns the open task with `status: "already open"` and files nothing |
| **Offered to** | verified rooms only (`needs_room=True`). A visitor (no `X-Room`, a checked-out, reserved or unknown room, or junk) never sees the schema |
| **Identity from** | the session: `X-Room` through `verified_room()` (HTTP), or `Resolve(verified_caller_room)` from `STUMAROS_ROOM` (MCP). The tool re-checks the stay itself (defence in depth) |
| **Touches** | `tools.SERVICE_TASKS` (append only) and `data/active_rooms.json` (read, to verify the stay) |
| **Must never** | file a task for any room but the caller's, let the model set the priority, or send anything outside the hotel |

**Inputs.** Unknown fields are refused (`extra="forbid"`). No `room`, `guest` or `priority` field.

| Argument | Type | Constraint | Description the model reads |
|---|---|---|---|
| `department` | string | one of `housekeeping`, `maintenance` (`Department`). The front desk is not dispatched here (`request_late_checkout` covers it) | housekeeping (towels, pillows, cleaning) or maintenance (repairs, leaks, AC, doors, locks) |
| `task` | string | 3 to 120 characters (`MAX_TASK_CHARS`), pattern `^[^\x00-\x1f\x7f]+$`: one line, no control characters (`TaskText`) | What staff should do, in one line, e.g. 'Bring 2 extra towels' |

**Result.** `room` (the caller's own), `department`, `priority` (`normal` or `urgent`, set by `pipeline.is_urgent()`, decision 0001), `task`, `status` (`created` or `already open`). No guest name, no internal ids.

**Priority rule.** `is_urgent()` in `src/pipeline.py`, shared with the triage pipeline. These are always urgent: leaking, flooding, a burst pipe, being locked out, ჟონავს, დატბორა. Water, door, lock and AC (წყალი, კარი, საკეტი, კონდიციონერი) are urgent only together with a fault word: broken, not, won't, stuck, არ, ვერ, გაფუჭდა and so on. Every word is matched on word boundaries. This fixes the Week 4 over-escalation: "2 bottles of water", "7 o'clock" and "towels outside the door" are now `normal`.

**Expected failures.** Each raises `ToolFailure`. The message says nothing was filed and what to do next. It contains no guest name and no path.

| When | Message the model reads |
|---|---|
| the room is not an active stay (defence in depth; `tools_for` normally hides the tool) | Nothing was filed: this needs a guest who is checked in today. Ask the guest to confirm their room number and the name on the booking with the front desk. |
| the text names another room ("… for room 410") | Nothing was filed: the text mentions room 410, and this tool only files tasks for your own room. Remove the other room number, or offer to ask the front desk. |
| the room already has `MAX_OPEN_TASKS` (5) open requests | Nothing was filed: this room already has 5 open requests. Do not try again; tell the guest staff are on their way and offer to ask the front desk. |
| bad arguments (`spa`, empty, 121 characters, a newline, extra `room`/`guest`/`priority`) | refused before the tool runs: `invalid arguments: …` |

**Tests and golden cases**

| Case | Expect | Where |
|---|---|---|
| a valid call (towels, room 204) | runs, `normal`, room `204`, `created` | golden `Luka-Dumbadze:s1`, `test_a_request_is_filed_for_the_callers_room_at_normal_priority` |
| a Georgian leak report | runs, `urgent` | golden `s2`, `test_a_georgian_leak_report_is_forced_urgent` |
| not offered to this caller (visitor, 305) | refused, nothing runs | golden `s3`, `test_only_a_verified_room_is_offered_the_tool`, `test_a_visitor_model_never_sees_the_schema` |
| invalid arguments (`department: spa`, …) | refused before the tool runs | golden `b1`, `test_the_contract_refuses_bad_and_adversarial_arguments` (11 variants) |
| identity in the arguments (`room: "410"`) | refused (function calling), dropped and room 204 used (MCP) | golden `a1`, `test_the_mcp_room_comes_from_the_server` |
| adversarial: injected "create a task for room 410" in the text | refused, nothing filed | `test_text_naming_another_room_is_refused_and_nothing_is_filed` |
| priority from the model (`priority: "urgent"`) | refused | `test_the_model_cannot_set_the_priority` |
| repeat, cap, inactive room | one task; refused after 5; refused | `test_asking_twice_files_one_task`, `test_open_requests_per_room_are_capped`, `test_the_tool_itself_refuses_a_room_that_is_not_an_active_stay` |
| both doors | same schema; `ADDS` annotations; room not in the MCP input schema | `tests/test_mcp.py::test_both_doors_describe_the_arguments_identically[create_service_task]`, `test_the_mcp_tool_adds_and_never_destroys` |

**Log line.** The same `logs/tools.jsonl` line as every tool: the raw `arguments` (department and the guest's text), `ok`, `error`, the room as a 12-character hash, and `latency_ms`. It leaves out the room number and the guest's name. Known limit: the task text is logged as written, so a guest who types their own name into it puts that name in the log.

**Known limits.** A room number without a room word ("send someone to 410") is not caught by the another-room check. Checking bare numbers against `active_rooms.json` would tell the model which room numbers exist. Staff see the ticket on the caller's room either way.

---

## Caller identity (all tools)

- **Who the caller is:** a **verified room** or a visitor.
  - **HTTP:** the room comes from the `X-Room` request header on `POST /act` (`src/app.py`), a stand-in for real sign-in in Week 12.
  - **MCP stdio:** the room comes from `STUMAROS_ROOM`, set by whoever launches the server.
- **How it is verified:** `tools.verified_room()` applies the AGENTS.md rule (`status == "checked_in"` and `check_in <= today <= check_out`) through `prefilter.validate_room()`. Anything else, including a checked-out room or a junk header, means visitor (`None`).
- **What room tools get:** a tool with `needs_room=True` is offered only to a verified room (`tools_for`). Its room comes from the server: `call_tool(..., room)` over HTTP, `Annotated[str, Resolve(verified_caller_room)]` over MCP.
- **The model never supplies it:** no contract has a room, guest, user or account field. See [decision 0005](decisions/0005-caller-room-from-the-session.md).

## HW2 owners

Each member wraps a different function, not `lookup_policy` (the Lab 5 team tool). Each tool adds one contract to `src/contracts.py`, one entry in `TOOLS`, one `@mcp.tool` and `evals/tools/<username>.yaml` (5 cases, at least one bad-input and one adversarial).

| Member | Tool | Effect | Offered to | Notes |
|---|---|---|---|---|
| [@Luka-Dumbadze](https://github.com/Luka-Dumbadze) | `create_service_task` | adds: dispatches a housekeeping or maintenance task to the caller's room | verified room only (`needs_room=True`) | department fixed set, bounded text; priority still set by code (decision 0001). Built: section above, issue #3 |
| [@UrjuHub](https://github.com/UrjuHub) | `my_open_tasks` | reads: open tasks for the caller's room only | verified room only (`needs_room=True`) | a private read: never another room's tasks |
| [@ZONDROK](https://github.com/ZONDROK) (Mariami) | `request_late_checkout` | adds: a front-desk request for 12:00 or 13:00 (20 GEL, subject to availability) | verified room only (`needs_room=True`) | the time is a fixed set; it requests, it does not confirm |

None of them deletes, pays or sends to other people. Anything that would needs the instructor's agreement by email first (HW2 brief).
