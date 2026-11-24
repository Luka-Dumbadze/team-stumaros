# Tool contracts · StumarOS

*From `Lab-5/templates/tool-contract.md`. One section per tool. Every rule in this table exists in code: the contract class (`src/contracts.py`), the tool body (`src/tools.py`) or the registry (`TOOLS`, `tools_for()`). Lab 5 ships one tool. The HW2 owners at the bottom each add one more.*

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
| [@Luka-Dumbadze](https://github.com/Luka-Dumbadze) | `create_service_task` | adds: dispatches a housekeeping or maintenance task to the caller's room | verified room only (`needs_room=True`) | department and item from fixed sets, bounded text; priority still set by code (decision 0001) |
| [@UrjuHub](https://github.com/UrjuHub) | `my_open_tasks` | reads: open tasks for the caller's room only | verified room only (`needs_room=True`) | a private read: never another room's tasks |
| [@ZONDROK](https://github.com/ZONDROK) (Mariami) | `request_late_checkout` | adds: a front-desk request for 12:00 or 13:00 (20 GEL, subject to availability) | verified room only (`needs_room=True`) | the time is a fixed set; it requests, it does not confirm |

None of them deletes, pays or sends to other people. Anything that would needs the instructor's agreement by email first (HW2 brief).
