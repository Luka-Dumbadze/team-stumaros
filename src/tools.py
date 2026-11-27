"""StumarOS's tools: the code that acts, behind the contracts in src/contracts.py (Lab 5 pattern).

Lab 5 ships lookup_policy, which reads. HW2 adds create_service_task (Luka-Dumbadze), which adds a task
for the caller's own room. Nothing here deletes, edits a booking, or reveals who is staying in which room:
that is the least-privilege decision, made by what we chose NOT to build (no occupancy lookup, no cancel).
The other HW2 tools (owners table in docs/tool-contracts.md) join TOOLS below.

Every tool takes a validated contract object (never raw model output) and returns a pydantic
result. A failure we expected raises ToolFailure with a message written for the model to read and
act on. Anything else is a bug and is allowed to crash.

The caller is a verified room or None (a visitor). verified_room() is the only way to get one: it
applies the AGENTS.md rule through prefilter.validate_room(). The model never supplies it.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import date, datetime
from typing import Callable, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from . import prefilter
from .contracts import CreateServiceTask, LookupPolicy, MyOpenTasks
from .pipeline import is_urgent

TBILISI = ZoneInfo("Asia/Tbilisi")


class ToolFailure(Exception):
    """An expected failure. The message goes back to the model, so make it say what to do next."""


def today() -> date:
    """Today in Kutaisi. STUMAROS_TODAY pins it for tests and the demo (the mock stays are valid 2026-10-15)."""
    pinned = os.environ.get("STUMAROS_TODAY")
    return date.fromisoformat(pinned) if pinned else datetime.now(TBILISI).date()


def verified_room(claimed: str | None) -> str | None:
    """The caller's room if it is an active stay today (AGENTS.md rule), else None (a visitor).
    `claimed` comes from the session (X-Room header, STUMAROS_ROOM), never from the model."""
    claimed = (claimed or "").strip()
    if not claimed or len(claimed) > 8:
        return None
    _, status = prefilter.validate_room(claimed, prefilter.load_rooms(), today())
    return claimed if status == "valid" else None


def room_key(room: str) -> str:
    """We log a hash of the room, not the room itself: room + date identifies a guest."""
    return hashlib.sha256(room.encode()).hexdigest()[:12]


# ---------------------------------------------------------------- results

class PolicySection(BaseModel):
    section: str
    text: str                  # the guide's words, unchanged: the model quotes, it does not invent


# ---------------------------------------------------------------- lookup_policy

def lookup_policy(args: LookupPolicy) -> PolicySection:
    section = next((s for s in prefilter.load_guide() if s["id"] == args.section), None)
    if section is None:  # the contract allows it but the guide no longer has it: tell the model what to do
        raise ToolFailure(f"The hotel guide has no '{args.section}' section right now. "
                          "Say the information is not available and offer to ask the front desk.")
    return PolicySection(section=section["id"], text=section["text"])


# ---------------------------------------------------------------- create_service_task (HW2 · Luka-Dumbadze)

MAX_OPEN_TASKS = 5   # per room: a looping or injected model cannot flood staff with tickets


class ServiceTask(BaseModel):
    room: str                              # the caller's verified room, never an argument
    department: str
    priority: Literal["normal", "urgent"]  # set by is_urgent() (decision 0001), never by the model
    task: str
    status: Literal["created", "already open"]


# Open tasks, in process memory (AGENTS.md: no storage files). my_open_tasks (HW2, @UrjuHub) will read it.
SERVICE_TASKS: list[ServiceTask] = []


def _same(a: str, b: str) -> bool:
    return " ".join(a.split()).casefold() == " ".join(b.split()).casefold()


def create_service_task(args: CreateServiceTask, room: str) -> ServiceTask:
    """`room` comes from the verified session (X-Room header or STUMAROS_ROOM). The contract has no such field."""
    if verified_room(room) != room:  # defence in depth: tools_for() already hides the tool from visitors
        raise ToolFailure("Nothing was filed: this needs a guest who is checked in today. Ask the guest to "
                          "confirm their room number and the name on the booking with the front desk.")
    if others := [r for r in prefilter.extract_rooms(args.task) if r != room]:
        raise ToolFailure(f"Nothing was filed: the text mentions room {others[0]}, and this tool only files "
                          "tasks for your own room. Remove the other room number, or offer to ask the front desk.")
    mine = [t for t in SERVICE_TASKS if t.room == room]
    for t in mine:  # idempotent: the same request twice is one task
        if t.department == args.department and _same(t.task, args.task):
            return t.model_copy(update={"status": "already open"})
    if len(mine) >= MAX_OPEN_TASKS:
        raise ToolFailure(f"Nothing was filed: this room already has {MAX_OPEN_TASKS} open requests. Do not try "
                          "again; tell the guest staff are on their way and offer to ask the front desk.")
    task = ServiceTask(room=room, department=args.department, task=args.task, status="created",
                       priority="urgent" if is_urgent(args.task) else "normal")
    SERVICE_TASKS.append(task)
    return task.model_copy()

# ---------------------------------------------------------------- my_open_tasks (HW2 · @UrjuHub)

class OpenTasksResult(BaseModel):
    room: str
    tasks: list[ServiceTask]


def my_open_tasks(args: MyOpenTasks, room: str) -> OpenTasksResult:
    """`room` comes from the verified session (X-Room header or STUMAROS_ROOM). The contract has no such field."""
    if verified_room(room) != room:
        raise ToolFailure("Nothing was returned: this needs a guest who is checked in today. Ask the guest to "
                          "confirm their room number and the name on the booking with the front desk.")
    mine = [t.model_copy() for t in SERVICE_TASKS if t.room == room]
    return OpenTasksResult(room=room, tasks=mine)


# ---------------------------------------------------------------- the registry

@dataclass(frozen=True)
class Tool:
    name: str
    args: type[Contract]
    run: Callable[..., BaseModel]
    # True: the tool acts on or reads the caller's own stay, so it is offered only to a verified room
    # and receives that room from the server. Wider than the Lab 5 example's `writes`, because a private
    # read (HW2's my_open_tasks) needs the caller too.
    needs_room: bool = False

    def schema(self) -> dict:
        """What the model sees: name, description and JSON Schema, all from the contract."""
        return {"type": "function", "function": {
            "name": self.name, "description": self.args.__doc__.strip(),
            "parameters": self.args.model_json_schema()}}


TOOLS = {t.name: t for t in [
    Tool("lookup_policy", LookupPolicy, lookup_policy),
    Tool("create_service_task", CreateServiceTask, create_service_task, needs_room=True),
    Tool("my_open_tasks", MyOpenTasks, my_open_tasks, needs_room=True),
]}


def tools_for(room: str | None) -> dict[str, Tool]:
    """Least privilege by construction: a visitor (no verified room) is never offered a room tool."""
    return {n: t for n, t in TOOLS.items() if room or not t.needs_room}
