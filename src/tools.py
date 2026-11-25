"""StumarOS's tools: the code that acts, behind the contracts in src/contracts.py (Lab 5 pattern).

Lab 5 ships one tool, lookup_policy, which reads. Nothing here deletes, edits a booking, or reveals
who is staying in which room: that is the least-privilege decision, made by what we chose NOT to
build (no occupancy lookup). The HW2 tools (owners table in docs/tool-contracts.md) join TOOLS below.

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
from typing import Callable
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from . import prefilter
from .contracts import Contract, LookupPolicy

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
]}


def tools_for(room: str | None) -> dict[str, Tool]:
    """Least privilege by construction: a visitor (no verified room) is never offered a room tool."""
    return {n: t for n, t in TOOLS.items() if room or not t.needs_room}
