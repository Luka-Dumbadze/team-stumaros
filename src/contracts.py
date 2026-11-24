"""The tool contracts: what each capability accepts, as types the code can check (Lab 5 pattern).

This file is the single source of truth for tool inputs. Two doors read it:
  * src/tools.py builds the function-calling schemas the model sees (Args models below)
  * src/mcp_server.py builds the MCP tools from the same type aliases
tests/test_mcp.py fails if the two doors ever describe a tool differently.

Rules that hold for every contract:
  * extra="forbid": an argument we did not ask for is an error, never ignored
  * every string that reaches a lookup or a file has a pattern or a fixed set of values
  * nothing here names WHO is calling: no room, guest, user or account field. The caller's
    room comes from the session (X-Room header or STUMAROS_ROOM), verified in code.
"""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

# The section ids of data/hotel_guide.json. tests/test_contracts.py fails if the guide and this list drift.
SectionId = Annotated[
    Literal["breakfast", "pool", "checkout", "wifi", "parking", "housekeeping", "maintenance", "quiet_hours", "pets"],
    Field(description="One section of the hotel guide"),
]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LookupPolicy(Contract):
    """Read one section of the hotel guide, word for word. Reads only; changes nothing."""
    section: SectionId
