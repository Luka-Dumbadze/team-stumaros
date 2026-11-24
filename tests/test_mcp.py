"""The MCP door: same contracts, annotations, identity from the server, in-memory client."""
import asyncio

import pytest
from mcp import Client
from mcp.server.mcpserver.exceptions import ToolError

from src import tools
from src.mcp_server import mcp, verified_caller_room


def run(coro):
    return asyncio.run(coro)


async def listed():
    async with Client(mcp) as c:
        return {t.name: t for t in (await c.list_tools()).tools}


async def call(name, args):
    async with Client(mcp) as c:
        return await c.call_tool(name, args)


def strip(schema):
    return {k: {kk: vv for kk, vv in v.items() if kk != "title"} for k, v in schema["properties"].items()}


def test_same_tools_through_both_doors():
    assert set(run(listed())) == set(tools.TOOLS)


@pytest.mark.parametrize("name", sorted(tools.TOOLS))
def test_both_doors_describe_the_arguments_identically(name):
    mcp_schema = run(listed())[name].input_schema
    fc_schema = tools.TOOLS[name].schema()["function"]["parameters"]
    assert strip(mcp_schema) == strip(fc_schema)
    assert set(mcp_schema.get("required", [])) == set(fc_schema.get("required", []))


def test_annotations_mark_the_lookup_read_only():
    assert run(listed())["lookup_policy"].annotations.read_only_hint is True


def test_a_call_through_the_client_returns_the_guide_text():
    r = run(call("lookup_policy", {"section": "pool"}))
    assert not r.is_error and r.structured_content["text"].startswith("The rooftop pool is open 08:00-22:00")


def test_bad_arguments_are_rejected_by_the_sdk():
    assert run(call("lookup_policy", {"section": "../../.env"})).is_error


def test_expected_failure_reaches_the_model_as_text(monkeypatch):
    monkeypatch.setattr(tools.prefilter, "load_guide", lambda: [])
    r = run(call("lookup_policy", {"section": "pool"}))
    assert r.is_error and "front desk" in r.content[0].text


def test_an_extra_room_argument_never_reaches_the_tool():
    # The MCP SDK drops unknown arguments (function calling rejects them); either way the tool never sees it.
    r = run(call("lookup_policy", {"section": "pool", "room": "305"}))
    assert not r.is_error and set(r.structured_content) == {"section", "text"}


@pytest.mark.parametrize("env, ok", [("204", True), ("305", False), ("", False), (None, False)])
def test_the_caller_room_comes_from_the_server_and_is_verified(monkeypatch, env, ok):
    if env is not None:
        monkeypatch.setenv("STUMAROS_ROOM", env)
    if ok:
        assert verified_caller_room() == env
    else:
        with pytest.raises(ToolError, match="Not verified"):
            verified_caller_room()
