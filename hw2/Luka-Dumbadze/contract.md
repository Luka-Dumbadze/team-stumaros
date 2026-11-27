# HW2 · Tool contract · `create_service_task` · Luka-Dumbadze

**Tool:** `create_service_task` · **Owner:** `Luka-Dumbadze` · **Team repo:** https://github.com/Luka-Dumbadze/team-stumaros
**Code on `main`:** contract class `CreateServiceTask` in `src/contracts.py` line 51 · function in `src/tools.py` line 96 · registry entry in `src/tools.py` line 138 (`TOOLS`) · MCP registration in `src/mcp_server.py` line 53
**Product pull request:** #4 · merged commit `a471bf3` (implementation commit `519c752`)

*From `Lab-5/templates/tool-contract.md`. Code on `main`: [`src/contracts.py`](../../src/contracts.py) (`CreateServiceTask`, `Department`, `TaskText`), [`src/tools.py`](../../src/tools.py) (`create_service_task`, `ServiceTask`, `SERVICE_TASKS`, `MAX_OPEN_TASKS`, `TOOLS` entry), [`src/pipeline.py`](../../src/pipeline.py) (`is_urgent`), [`src/mcp_server.py`](../../src/mcp_server.py) (`create_service_task`), [`evals/tools/Luka-Dumbadze.yaml`](../../evals/tools/Luka-Dumbadze.yaml). Issue #3 · product pull request #4. Full team section: [`docs/tool-contracts.md`](../../docs/tool-contracts.md).*

**In one sentence, for the model:** File one housekeeping or maintenance request for the guest's own room. Adds a task for staff; never changes or cancels one. The hotel sets the priority from the text (leaks, door, lock and AC faults are urgent), so do not ask the guest for one.

| | |
|---|---|
| **Effect** | adds: one task in the in-memory queue `tools.SERVICE_TASKS` (AGENTS.md allows no storage files) |
| **Undo** | staff close or cancel it at the front desk. There is deliberately no cancel tool |
| **Idempotent?** | yes: the same department and text again (ignoring case and spacing) returns the open task as `already open` and files nothing. Second identical call (room 204, through `call_tool()` on `main`): `{"room": "204", "department": "housekeeping", "priority": "normal", "task": "Please bring 2 extra towels", "status": "already open"}` |
| **Offered to** | verified rooms only (`needs_room=True`, `src/tools.py` line 138). A visitor never sees the schema, whether they sent no room or a checked-out, reserved, unknown or junk one |
| **Identity from** | the session, never an argument. **Function calling** (`POST /act`): the `X-Room` header goes through `verified_room()`. **MCP:** `Annotated[str, Resolve(verified_caller_room)]` reads `STUMAROS_ROOM`. The tool re-checks the stay itself |
| **Touches** | `tools.SERVICE_TASKS` (append only); `data/active_rooms.json` (read, to verify the stay) |
| **Must never** | file a task for any room but the caller's, let the model choose the priority, or send anything outside the hotel |

**Inputs.** `extra="forbid"`. No `room`, `guest` or `priority` field.

| Argument | Type | Constraint | Description the model reads |
|---|---|---|---|
| `department` | string | `Literal["housekeeping", "maintenance"]` | housekeeping (towels, pillows, cleaning) or maintenance (repairs, leaks, AC, doors, locks) |
| `task` | string | 3–120 characters, pattern `^[^\x00-\x1f\x7f]+$` (one line, no control characters) | What staff should do, in one line, e.g. 'Bring 2 extra towels' |

**Result.** It returns five fields, with no guest name and no internal ids:
- `room`: the caller's own room;
- `department`;
- `priority`: `normal` or `urgent`, set by `is_urgent()`;
- `task`;
- `status`: `created` or `already open`.

**Priority in code (decision 0001).** `is_urgent()` is shared with the triage pipeline. Words for leaking, flooding, a burst pipe or being locked out (ჟონავს, დატბორა) are always urgent. Water, door, lock and AC (წყალი, კარი, საკეტი, კონდიციონერი) are urgent only together with a fault word: broken, not, won't, stuck, არ, გაფუჭდა. Every word is matched on word boundaries, so "2 bottles of water" and "7 o'clock" stay `normal`.

**Expected failures.** Each raises `ToolFailure`; the MCP door turns it into `ToolError`. No stack trace, path or guest name.

| When | Message the model reads |
|---|---|
| the room is not an active stay | Nothing was filed: this needs a guest who is checked in today. Ask the guest to confirm their room number and the name on the booking with the front desk. |
| the text names another room | Nothing was filed: the text mentions room 410, and this tool only files tasks for your own room. Remove the other room number, or offer to ask the front desk. |
| `MAX_OPEN_TASKS = 5` reached | Nothing was filed: this room already has 5 open requests. Do not try again; tell the guest staff are on their way and offer to ask the front desk. |
| bad arguments | refused before the tool runs: `invalid arguments: <field>: …` |

**The decision I had to make.** In our first triage design, the model could propose any room number, department, and priority directly in its reply, and we only filtered it afterward in `pipeline.py`. For the tool contract, I removed `room`, `priority`, and `front_desk` from `CreateServiceTask` in `src/contracts.py`, leaving only `department` (`housekeeping` or `maintenance`) and bounded `task` text. Now the verified room comes strictly from the server (`X-Room` or `Resolve(verified_caller_room`) in `src/tools.py` and `src/mcp_server.py`), and `is_urgent()` in code assigns priority. That stops prompt injection from filing tasks for another room or spamming unexpected departments.

*Facts you can point to (delete this list before submitting):*
- **`room` is not an argument.** `CreateServiceTask` (`src/contracts.py` line 51) has only `department` and `task`. `extra="forbid"` (`src/contracts.py` line 43) refuses anything else. The room comes from the session: `create_service_task(args, room)` in `src/tools.py` line 96, passed in by `src/act.py` line 72, decision `docs/decisions/0005-caller-room-from-the-session.md`. Red-run PR #5 shows what adding it back breaks.
- **`priority` is not an argument.** `src/tools.py` line 112 sets it with `is_urgent()`; the comment on line 83 cites decision 0001.
- **`front_desk` is not a department.** `Department` (`src/contracts.py` lines 29–32) allows only `housekeeping` and `maintenance`. The comment on line 28 says `request_late_checkout` covers the front desk.

**Tests and golden cases.** There are 5 golden cases (s1, s2, s3, b1, a1) in `evals/tools/Luka-Dumbadze.yaml`, run in CI by `tests/test_tool_golden.py`. Another 51 unit tests are in `tests/test_create_service_task.py`. The both-doors check is `tests/test_mcp.py::test_both_doors_describe_the_arguments_identically[create_service_task]`. Results and CI links are in [`evidence.md`](evidence.md).

**Log line.** Each call writes one `logs/tools.jsonl` line with the tool, the raw arguments, `ok`, `error`, a 12-character hash of the room, and `latency_ms`. The room number and the guest's name are left out. The task text is logged as the guest wrote it.

**Known limits.** A room number without a room word (a bare "410") is not caught by the another-room check: checking bare numbers against `active_rooms.json` would reveal which rooms exist. "The tap is dripping" stays `normal`.
