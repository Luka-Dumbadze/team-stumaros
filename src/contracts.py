"""The tool contracts: what each capability accepts, as types the code can check (Lab 5 pattern).

This file is the single source of truth for tool inputs. Two doors read it:
  * src/tools.py builds the function-calling schemas the model sees (Args models below)
  * src/mcp_server.py builds the MCP tools from the same type aliases
tests/test_mcp.py fails if the two doors ever describe a tool differently.

Rules that hold for every contract:
  * extra="forbid": an argument we did not ask for is an error, never ignored
  * every string has a pattern or a fixed set of values, and free text has length bounds
  * nothing here names WHO is calling: no room, guest, user or account field. The caller's
    room comes from the session (X-Room header or STUMAROS_ROOM), verified in code.
"""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from .schemas import MAX_TASK_CHARS

# The section ids of data/hotel_guide.json. tests/test_contracts.py fails if the guide and this list drift.
SectionId = Annotated[
    Literal["breakfast", "pool", "checkout", "wifi", "parking", "housekeeping", "maintenance", "quiet_hours", "pets"],
    Field(description="One section of the hotel guide"),
]

# create_service_task (HW2, Luka-Dumbadze). Front desk is not dispatched here: request_late_checkout covers it.
Department = Annotated[
    Literal["housekeeping", "maintenance"],
    Field(description="housekeeping (towels, pillows, cleaning) or maintenance (repairs, leaks, AC, doors, locks)"),
]
# The guest's request for staff, in the guest's words. One line: no control characters (no newline smuggling a
# second instruction into the staff ticket). The same 120-character cap as the triage Task (src/schemas.py).
TaskText = Annotated[
    str,
    Field(min_length=3, max_length=MAX_TASK_CHARS, pattern=r"^[^\x00-\x1f\x7f]+$",
          description="What staff should do, in one line, e.g. 'Bring 2 extra towels'"),
]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LookupPolicy(Contract):
    """Read one section of the hotel guide, word for word. Reads only; changes nothing."""
    section: SectionId


class CreateServiceTask(Contract):
    """File one housekeeping or maintenance request for the guest's own room. Adds a task for staff; never
    changes or cancels one. The hotel sets the priority from the text (leaks, door, lock and AC faults are
    urgent), so do not ask the guest for one."""
    department: Department
    task: TaskText
