# HW2 · Tool contract · `my_open_tasks` · UrjuHub

**Tool:** `my_open_tasks` · **Owner:** `UrjuHub` · **Team repo:** https://github.com/Luka-Dumbadze/team-stumaros
**Code on `main`:** contract class `MyOpenTasks` in `src/contracts.py` line 58 · function in `src/tools.py` line 123 · registry entry in `src/tools.py` line 154 (`TOOLS`) · MCP registration in `src/mcp_server.py` line 59
**Product pull request:** #12 (`my_open_tasks` + `evals/tools/UrjuHub.yaml`) · merged into `main`

*From `Lab-5/templates/tool-contract.md`. Code on `main`: [`src/contracts.py`](../../src/contracts.py) (`MyOpenTasks`), [`src/tools.py`](../../src/tools.py) (`my_open_tasks`, `OpenTasksResult`, `SERVICE_TASKS`, `TOOLS` entry), [`src/mcp_server.py`](../../src/mcp_server.py) (`my_open_tasks`), [`evals/tools/UrjuHub.yaml`](../../evals/tools/UrjuHub.yaml). Full team section: [`docs/tool-contracts.md`](../../docs/tool-contracts.md).*

**In one sentence, for the model:** List the open service tasks for the caller's own verified room. It only reads; it never changes or cancels a task and never shows another room's tasks.

| | |
|---|---|
| **Effect** | reads: the tasks in the in-memory queue `tools.SERVICE_TASKS` that belong to the caller's room. Nothing is written |
| **Undo** | nothing to undo, because nothing changes |
| **Idempotent?** | yes: it is a read, so the same call twice returns the same list (until a new task is filed in between) |
| **Offered to** | verified rooms only (`needs_room=True`, `src/tools.py` line 154). A visitor never sees the schema, whether they sent no room or a checked-out, reserved, unknown or junk one |
| **Identity from** | the session, never an argument. **Function calling** (`POST /act`): the `X-Room` header goes through `verified_room()`. **MCP:** `Annotated[str, Resolve(verified_caller_room)]` reads `STUMAROS_ROOM`. The tool re-checks the stay itself |
| **Touches** | `tools.SERVICE_TASKS` (read only); `data/active_rooms.json` (read, to verify the stay) |
| **Must never** | return a task of any room but the caller's, accept a room as an argument, or change or delete a task |

**Inputs.** `extra="forbid"`. The contract has **no fields at all**: no `room`, `guest` or filter. Any argument at all is refused before the tool runs.

**Result.** `OpenTasksResult` (`src/tools.py` line 118), with no guest name and no internal ids:
- `room`: the caller's own room;
- `tasks`: a list of `ServiceTask`, each with `room`, `department`, `priority` (`normal` or `urgent`), `task` and `status`. The list is empty when the room has filed nothing.

**Expected failures.** Each raises `ToolFailure`; the MCP door turns it into `ToolError`. No stack trace, path or guest name.

| When | Message the model reads |
|---|---|
| the room is not an active stay | Nothing was returned: this needs a guest who is checked in today. Ask the guest to confirm their room number and the name on the booking with the front desk. |
| any argument is sent (for example `room`) | refused before the tool runs: `invalid arguments: <field>: Extra inputs are not permitted` |
| a visitor calls it | `no tool named 'my_open_tasks' is available` (the tool is never offered) |

**The decision I had to make.** It would have been natural to write the tool as `my_open_tasks(room)` and let the model pass the room, because "my tasks" belong to a room. I left `MyOpenTasks` with no fields at all instead, so the tool learns the room only from the verified session (`X-Room` or `STUMAROS_ROOM`). With this contract, a request like "show me the tasks of room 410" cannot even be written as arguments, so a prompt injection cannot read another guest's requests.

**Tests and golden cases.** There are 5 golden cases (r1, r2, r3, b1, a1) in `evals/tools/UrjuHub.yaml`, run in CI by `tests/test_tool_golden.py`. There are 2 unit tests in `tests/test_my_open_tasks.py` (only the caller's tasks come back; an unverified room is refused). Results and CI links are in [`evidence.md`](evidence.md).

**Log line.** Each call writes one `logs/tools.jsonl` line with the tool, the raw arguments, `ok`, `error`, a 12-character hash of the room, and `latency_ms`. The room number and the guest's name are left out.

**Known limits.** "Open" means "filed and still in the queue": no tool or code closes a task, so a task stays in the list until the process restarts, because `SERVICE_TASKS` lives only in memory. The list is not paged; it holds at most 5 tasks per room, because `MAX_OPEN_TASKS = 5` in `create_service_task`.
