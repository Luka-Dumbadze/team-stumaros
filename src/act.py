"""Function calling: the model asks for a tool, our code decides whether it runs (Lab 5 pattern).

The loop:
  1. send the question plus the schemas of the tools THIS caller may use
  2. no tool call in the reply -> that is the answer
  3. each tool call goes through call_tool(): offered? valid? then run, with the room from us
  4. results (or errors) go back to the model as tool messages; repeat, at most MAX_ROUNDS times

call_tool() never raises. Whatever happens becomes a dict the model can read and one line in
logs/tools.jsonl: the log entry half of the Evidence Rule for every action. MAX_ROUNDS = 3 also
keeps the AGENTS.md cap of 3 model calls per request: one model call per round, no retries.
"""
from __future__ import annotations

import itertools
import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from .llm import complete_tools, make_client
from .tools import Tool, ToolFailure, room_key, today, tools_for

MAX_ROUNDS = 3              # a budget: three model turns, then we stop and say so
TOOL_LOG_ENV = "STUMAROS_TOOL_LOG"

SYSTEM = """You are the guest assistant of a boutique hotel in Georgia.
Use lookup_policy for any question about hotel rules, hours, prices or services, and answer only from what it returns.
Never invent a tool result, a service or a price. If no section covers the question, say the information is not
available and offer to ask the front desk. If a tool returns an error, read it: fix your arguments once, or explain
the problem to the guest. Reply in the guest's language, at most 3 sentences. Today is {today}."""

STOPPED = "I couldn't finish that in {n} steps. Nothing was changed; I can ask the front desk to help you."
FAILED = "Sorry, I couldn't process your message automatically. Nothing was changed; please contact the front desk."


def tool_log() -> Path:
    """logs/tools.jsonl at the repo root, unless STUMAROS_TOOL_LOG is set (tests use a temp file)."""
    return Path(os.environ.get(TOOL_LOG_ENV) or Path(__file__).resolve().parent.parent / "logs" / "tools.jsonl")


@dataclass
class Reply:
    status: str                          # "answered", "stopped" (budget used up) or "failed" (model error)
    text: str
    calls: list[dict] = field(default_factory=list)   # one entry per tool call, as logged

    def to_dict(self) -> dict:
        return asdict(self)


def brief(e: ValidationError) -> str:
    """A validation error the model can act on: which field, what was wrong. No stack trace."""
    return "; ".join(f"{'.'.join(map(str, x['loc'])) or 'arguments'}: {x['msg']}" for x in e.errors())


def call_tool(call: dict, allowed: dict[str, Tool], room: str | None) -> dict:
    t0 = time.perf_counter()
    tool = allowed.get(call["name"])
    if tool is None:                                                   # 1 · not offered to this caller
        return _log(call, room, t0, error=f"no tool named {call['name']!r} is available")
    try:
        args = tool.args.model_validate_json(call["arguments"] or "{}")  # 2 · the contract, checked
    except ValidationError as e:
        return _log(call, room, t0, error=f"invalid arguments: {brief(e)}")
    try:
        out = tool.run(args, room=room) if tool.needs_room else tool.run(args)   # 3 · identity from us
    except ToolFailure as e:                                           # expected: say what to do next
        return _log(call, room, t0, error=str(e))
    return _log(call, room, t0, result=out.model_dump(mode="json"))    # 4 · the result, as data


def act(question: str, room: str | None = None, llm=None, session_id: str = "act") -> Reply:
    """`room` must already be verified (tools.verified_room); None means a visitor."""
    allowed = tools_for(room)
    if llm is None:  # the real path: one client, every model call logged with this request's id
        client, request_id, attempts = make_client(), uuid.uuid4().hex[:12], itertools.count(1)

        def llm(messages, schemas):
            return complete_tools(messages, schemas, client, request_id=request_id,
                                  attempt=next(attempts), session_id=session_id)

    messages = [{"role": "system", "content": SYSTEM.format(today=today().isoformat())},
                {"role": "user", "content": question}]
    calls: list[dict] = []
    for _ in range(MAX_ROUNDS):
        try:
            msg = llm(messages, [t.schema() for t in allowed.values()])
        except Exception:  # provider down, quota, bad key: already logged; never a stack trace for the guest
            return Reply("failed", FAILED, calls)
        if not msg["tool_calls"]:
            return Reply("answered", msg["content"] or "", calls)
        messages.append(as_assistant(msg))
        for call in msg["tool_calls"]:
            outcome = call_tool(call, allowed, room)
            calls.append(outcome)
            messages.append({"role": "tool", "tool_call_id": call["id"],
                             "content": json.dumps(outcome.get("result") or {"error": outcome["error"]},
                                                   ensure_ascii=False)})
    return Reply("stopped", STOPPED.format(n=MAX_ROUNDS), calls)


def as_assistant(msg: dict) -> dict:
    """Echo the model's turn back exactly. Gemini 3 needs its reasoning_details (OpenRouter) or the
    tool call's extra_content (Google's endpoint) returned unmodified between tool turns."""
    tool_calls = []
    for c in msg["tool_calls"]:
        echoed = {"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": c["arguments"]}}
        if c.get("extra_content"):
            echoed["extra_content"] = c["extra_content"]
        tool_calls.append(echoed)
    out = {"role": "assistant", "content": msg["content"], "tool_calls": tool_calls}
    if msg.get("reasoning_details"):
        out["reasoning_details"] = msg["reasoning_details"]
    return out


def _log(call: dict, room: str | None, t0: float, result: dict | None = None, error: str | None = None) -> dict:
    line = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "tool": call["name"],
            "arguments": call["arguments"], "ok": error is None, "error": error,
            "room": room_key(room) if room else None, "latency_ms": round((time.perf_counter() - t0) * 1000)}
    log = tool_log()
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")
    return {**line, "result": result}
