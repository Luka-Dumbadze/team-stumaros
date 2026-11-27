# HW2 · Evidence · `my_open_tasks` · UrjuHub

*Tool: [`contract.md`](contract.md). Product pull request #12. All runs are on GitHub Actions, job `test`, Python 3.11.*

## The five golden cases

[`evals/tools/UrjuHub.yaml`](../../evals/tools/UrjuHub.yaml) is run by `tests/test_tool_golden.py` in the CI job `test`. Each case goes through `call_tool()`: the same three gates the model's request goes through, with no model and no key. The test date is pinned to 2026-10-15: room 204 is checked in, 305 has checked out, and 410 is another guest's room. The results below are the actual outputs, reproduced on 27 November 2026.

| # | Type | Call (caller · arguments) | Expected | Actual | Pass? |
|---|---|---|---|---|---|
| r1 | normal | room 204 · `{}` | ok · `room: "204"` | `{"room": "204", "tasks": []}` | pass |
| r2 | normal | visitor (null) · `{}` | refused · `no tool named` | `no tool named 'my_open_tasks' is available` | pass |
| r3 | normal | room 305 (checked out) · `{}` | refused · `checked in today` | `Nothing was returned: this needs a guest who is checked in today. Ask the guest to confirm their room number and the name on the booking with the front desk.` | pass |
| b1 | bad-input | room 204 · `{unexpected_field: "abc"}` | refused · `invalid arguments` | `invalid arguments: unexpected_field: Extra inputs are not permitted` | pass |
| a1 | adversarial | room 204 · `{room: "410"}` | refused · `invalid arguments`, `room` | `invalid arguments: room: Extra inputs are not permitted` | pass |

**The adversarial case, in one sentence:** a model that obeys an instruction injected into the guest's message tries to read the open tasks of room 410, another guest's room, by adding `room: "410"` to the arguments, which would show what another guest asked staff for.

**The MCP door.** The server was started as a real stdio subprocess (`python -m src.mcp_server`) with a scripted MCP client, not an AI host, on the pinned date 2026-10-15:
- **As room 204** (`STUMAROS_ROOM=204`):
  - `list_tools` returned `['lookup_policy', 'create_service_task', 'my_open_tasks']`.
  - After filing "Bring extra towels" (housekeeping), `my_open_tasks` returned room `204` with that one task.
  - `my_open_tasks` called with an extra `room: "410"`: the SDK dropped the argument and the answer was still room `204`'s list.
- **As room 305** (checked out, `STUMAROS_ROOM=305`): `my_open_tasks` was refused with "Not verified: this server was started without an active STUMAROS_ROOM."

## The red run: proof the gate blocks

**Throwaway branch:** `<<BRANCH-NAME, e.g. throwaway/weak-my-open-tasks>>` added one line to `MyOpenTasks` in `src/contracts.py`: `room: str | None = None`, an identity field the model could fill.

**Pull request:** #`<<NUMBER>>`, `[THROWAWAY - DO NOT MERGE] Weakened my_open_tasks contract`, into `main`. It was closed without merging and the branch was deleted.

- **Red run:** `<<URL of the red run, https://github.com/Luka-Dumbadze/team-stumaros/actions/runs/...>>`. Result: 3 failed, 177 passed `<<check the numbers in your own run>>`.
- **Merge state:** `<<what the Merge button said, or the output of gh pr view <number> --json mergeStateStatus; if GitHub did not block it, say so honestly>>`.
- **Failures** (the same three I got when I reproduced this locally):
  - `tests/test_contracts.py::test_no_contract_names_the_caller`
  - `tests/test_mcp.py::test_both_doors_describe_the_arguments_identically[my_open_tasks]`
  - `tests/test_tool_golden.py::test_tool_golden_case[UrjuHub:a1]`

**What it showed.** <<IN YOUR OWN WORDS, 2-4 sentences. Facts to build on: adding an optional `room` field made 3 checks fail. Golden case `a1` failed because the weakened contract accepted `room: "410"`, so the call ran and returned `{"room": "204", "tasks": []}` instead of being refused. Unlike `create_service_task`, `my_open_tasks` has no text to scan for other room numbers, so the contract was the only guard on the arguments; the runtime still used the session's room, but the schema now told the model it could choose one.>>

## The green run

Product pull request #12, merged into `main`. Green CI run on `main`: https://github.com/Luka-Dumbadze/team-stumaros/actions/runs/46047445147

Last line of `pytest -q tests` on `main`, run locally on 2026-11-27 with no API key:

```
180 passed in 2.82s
```

## Through the MCP door

  **Prompt typed in Claude Code:**
  > <<only fill this in if you really ran it, see the note in the chat. Otherwise delete this section.>>

  **Tool call and output:**
  <<paste the real tool call and its JSON output here>>

The scripted stdio-client run is under **The MCP door** above.
