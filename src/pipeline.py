"""Orchestration: pre-filter -> one budgeted model call -> deterministic guardrails."""
from __future__ import annotations

import json
import os
import re
import time
import uuid
from datetime import date
from pathlib import Path

from . import prefilter
from .llm import MAX_INPUT_TOKENS, ModelClient, build_messages, call_with_budget, cost_usd, estimate_prompt_tokens
from .schemas import ModelOutput, Task, TriageResult, Usage

URGENT_KEYWORDS = re.compile(r"leak|flood|water|lock|door|\bac\b|air[- ]?condition|კონდიციონერ|წყალ|საკეტ|კარი",
                             re.IGNORECASE)
SUPPLY_KEYWORDS = re.compile(r"towel|pillow|blanket|toiletr|shampoo|soap|sheets|პირსახოც|ბალიშ|საბან", re.IGNORECASE)
ASKS_VERIFICATION = re.compile(r"room number|ოთახის ნომ", re.IGNORECASE)
MENTIONS_FRONT_DESK = re.compile(r"front desk|reception|მიმღებ", re.IGNORECASE)

VERIFY_EN = "Before we send anyone, please confirm your room number and the name on the booking."
ESCALATE_EN = "I don't have that information; I can ask the front desk to help you."
USAGE_LOG_ENV = "STUMAROS_USAGE_LOG"  # override the log path (tests point it at a temp file)
_DEFAULT_LOG = object()


def default_usage_log() -> Path:
    """logs/usage.jsonl at the repo root (AGENTS.md), unless STUMAROS_USAGE_LOG is set."""
    return Path(os.environ.get(USAGE_LOG_ENV) or Path(__file__).resolve().parent.parent / "logs" / "usage.jsonl")


def write_usage(log_file: Path, attempts: list[dict], session_id: str, client: ModelClient) -> None:
    """One line per model attempt (success, error or retry), in the AGENTS.md shape plus model, mode and cost."""
    model = getattr(client, "model", None) or getattr(client, "label", client.mode)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as f:
        for a in attempts:
            record = {"timestamp": a["timestamp"], "session_id": session_id, "request_id": a["request_id"],
                      "status": a["status"], "attempt": a["attempt"], "prompt_tokens": a["prompt_tokens"],
                      "completion_tokens": a["completion_tokens"], "latency_ms": a.get("latency_ms", 0),
                      "model": model, "mode": client.mode, "tokens_estimated": a.get("tokens_estimated", False),
                      "cost_usd": cost_usd(model, a["prompt_tokens"], a["completion_tokens"])}
            if a.get("error"):
                record["error"] = a["error"]
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


FALLBACK_EN = ("Sorry, I couldn't process your message automatically. "
               "I've flagged it for the front desk, who will reply shortly.")


def _numbers(text: str) -> set[str]:
    """Digit runs with leading zeros stripped, so 07:00 and 7:00 compare equal."""
    return {n.lstrip("0") or "0" for n in re.findall(r"\d+", text)}


def apply_priority_override(task: Task) -> str | None:
    """Root AGENTS.md: leaks, door/lock and AC issues are urgent; extra supplies never are."""
    if URGENT_KEYWORDS.search(task.task) and task.priority != "urgent":
        old, task.priority = task.priority, "urgent"
        return f"priority_override: {old}->urgent ({task.task!r})"
    if SUPPLY_KEYWORDS.search(task.task) and task.priority == "urgent":
        task.priority = "normal"
        return f"priority_override: urgent->normal ({task.task!r})"
    return None


def apply_guardrails(out: ModelOutput, message: str, room: str | None, room_status: str,
                     sections: list[dict]) -> tuple[str, list[Task], list[str]]:
    events: list[str] = []
    reply = out.reply
    tasks: list[Task] = []

    # 1. Room gate: the model never decides whether a task goes out.
    if out.tasks and room_status != "valid":
        events.append(f"room_gate: dropped {len(out.tasks)} task(s), room status {room_status!r}")
    elif room_status == "valid":
        for proposed in out.tasks:
            task = Task(room=room, department=proposed.department, priority=proposed.priority, task=proposed.task)
            if event := apply_priority_override(task):
                events.append(event)
            tasks.append(task)
    needs_verification = room_status != "valid" and (bool(out.tasks) or out.intent in ("service", "composite"))
    if needs_verification and not ASKS_VERIFICATION.search(reply):
        reply = f"{reply} {VERIFY_EN}"
        events.append("room_gate: appended verification request")

    # 2. Citations must refer to sections actually sent.
    sent_ids = {s["id"] for s in sections}
    if bad := [c for c in out.cited_sections if c not in sent_ids]:
        events.append(f"grounding: cited unsent sections {bad}")

    # 3. Every number in the reply must come from the sent policy text, the room, or the guest message.
    allowed = _numbers(" ".join(s["text"] for s in sections) + " " + message + " " + (room or ""))
    if unsupported := sorted(_numbers(reply) - allowed):
        events.append(f"grounding: unsupported numbers {unsupported}; reply replaced")
        reply = ESCALATE_EN + (f" {VERIFY_EN}" if needs_verification else "")

    # 4. A question with no matching policy must be escalated, not answered from thin air.
    if not sections and out.intent in ("question", "composite") and not MENTIONS_FRONT_DESK.search(reply):
        reply = f"{reply} {ESCALATE_EN}"
        events.append("grounding: no policy matched; appended escalation")
    return reply, tasks, events


def triage(message: str, client: ModelClient, today: date, payload_room: str | None = None,
           guide: list[dict] | None = None, rooms: list[dict] | None = None,
           log_file: Path | None = _DEFAULT_LOG, sleep=time.sleep, session_id: str = "cli") -> TriageResult:
    """Triage one guest message. Every model attempt is appended to logs/usage.jsonl unless log_file=None."""
    started = time.perf_counter()
    request_id = uuid.uuid4().hex[:12]
    guide = guide if guide is not None else prefilter.load_guide()
    rooms = rooms if rooms is not None else prefilter.load_rooms()

    message = prefilter.truncate_message(message)
    room, problem = prefilter.resolve_room(payload_room, message)
    _, room_status = prefilter.validate_room(room, rooms, today)
    if problem:
        room_status = problem
    sections = prefilter.select_sections(message, guide)
    messages = build_messages(message, sections, room, room_status)

    result = TriageResult(request_id=request_id, mode=client.mode, model=getattr(client, "label", client.mode),
                          reply=FALLBACK_EN, tasks=[], room=room,
                          room_validated=room_status == "valid", room_status=room_status,
                          needs_clarification=False, sections_sent=[s["id"] for s in sections])
    if (estimated := estimate_prompt_tokens(messages)) > MAX_INPUT_TOKENS:
        result.guardrail_events.append(f"budget: ~{estimated} input tokens > {MAX_INPUT_TOKENS}; no model call")
        result.usage.latency_ms = round((time.perf_counter() - started) * 1000)
        return result

    outcome = call_with_budget(client, messages, request_id, sleep=sleep)
    result.usage = Usage(attempts=len(outcome.attempts),
                         prompt_tokens=sum(a["prompt_tokens"] for a in outcome.attempts),
                         completion_tokens=sum(a["completion_tokens"] for a in outcome.attempts),
                         total_tokens=sum(a.get("total_tokens", 0) for a in outcome.attempts),
                         # Only attempts that returned usage count; a timed-out call reports none (and may
                         # still have been billed), which is not the same as an estimate.
                         tokens_estimated=any(a["tokens_estimated"] for a in outcome.attempts
                                              if "tokens_estimated" in a))
    # Failed attempts stay visible even when a later retry succeeds.
    result.guardrail_events += [f"attempt {a['attempt']} failed: {a['error']}" for a in outcome.attempts
                                if a.get("error")]
    if outcome.output is None:
        result.guardrail_events.append(f"model_failed after {len(outcome.attempts)} call(s): {outcome.error}")
    else:
        result.reply, result.tasks, events = apply_guardrails(outcome.output, message, room, room_status, sections)
        result.guardrail_events += events
        result.cited_sections = list(outcome.output.cited_sections)
        result.needs_clarification = outcome.output.needs_clarification or (
            room_status != "valid" and bool(outcome.output.tasks))
    result.usage.latency_ms = round((time.perf_counter() - started) * 1000)

    if log_file is _DEFAULT_LOG:
        log_file = default_usage_log()
    if log_file:
        write_usage(Path(log_file), outcome.attempts, session_id, client)
    return result
