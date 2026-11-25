"""StumarOS as an MCP server: the same tools, now usable by any MCP host (Lab 5 pattern).

Run it over stdio (what Claude Code, Cursor and VS Code launch):
    STUMAROS_ROOM=204 STUMAROS_TODAY=2026-10-15 python -m src.mcp_server
Or over Streamable HTTP:
    python -m src.mcp_server --http          # http://127.0.0.1:8000/mcp

MCP Python SDK 2.x (MCPServer, formerly FastMCP). The schema of every tool comes from the type hints,
which come from src/contracts.py; tests/test_mcp.py checks both doors stay identical.
"""
from __future__ import annotations

import os
import sys
from typing import Annotated

from mcp.server import MCPServer
from mcp.server.mcpserver import Resolve
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from . import tools
from .contracts import CreateServiceTask, Department, LookupPolicy, MyOpenTasks, SectionId, TaskText

mcp = MCPServer("stumaros", instructions="Boutique hotel guest assistant: the hotel guide, read word for word, "
                                       "and service requests for the guest's own room.")
READS = ToolAnnotations(read_only_hint=True, open_world_hint=False)
# Adds a task, never removes or overwrites one; the same request twice is one task (see tools.create_service_task).
ADDS = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False)


def verified_caller_room() -> str:
    """Who is calling, for tools that need a room: `Annotated[str, Resolve(verified_caller_room)]`.
    Set by whoever launches the server (STUMAROS_ROOM), verified against active stays; never by the model."""
    room = tools.verified_room(os.environ.get("STUMAROS_ROOM"))
    if room is None:
        raise ToolError("Not verified: this server was started without an active STUMAROS_ROOM.")
    return room


def _run(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except tools.ToolFailure as e:          # expected failures reach the model as readable errors
        raise ToolError(str(e)) from e


@mcp.tool(annotations=READS, description=LookupPolicy.__doc__)
def lookup_policy(section: SectionId) -> tools.PolicySection:
    return _run(tools.lookup_policy, LookupPolicy(section=section))


@mcp.tool(annotations=ADDS, description=CreateServiceTask.__doc__)
def create_service_task(department: Department, task: TaskText,
                        room: Annotated[str, Resolve(verified_caller_room)]) -> tools.ServiceTask:
    return _run(tools.create_service_task, CreateServiceTask(department=department, task=task), room=room)

@mcp.tool(annotations=READS, description=MyOpenTasks.__doc__)
def my_open_tasks(room: Annotated[str, Resolve(verified_caller_room)]) -> tools.OpenTasksResult:
    return _run(tools.my_open_tasks, MyOpenTasks(), room=room)

if __name__ == "__main__":
    if "--http" in sys.argv:
        mcp.run("streamable-http", host="127.0.0.1", port=8000)
    else:
        mcp.run()
