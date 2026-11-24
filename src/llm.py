"""Prompt construction, model clients (live Gemini / OpenRouter + offline mock) and the 3-call budget.

Week 5 adds complete_tools(): the same client asks the model which tool to call (function calling),
and every such call writes one usage line to logs/usage.jsonl, like every triage call."""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Mapping, Protocol

from .prefilter import estimate_tokens, load_guide, select_sections
from .schemas import ModelOutput, SchemaError, parse_model_output


@dataclass(frozen=True)
class Provider:
    name: str
    key_env: str
    base_url: str
    default_model: str
    reasoning_effort: str | None = None  # sent only when set


# Precedence: the first provider whose key is set wins; with no key at all, the mock client runs.
PROVIDERS = (
    # 2.5-flash: HTTP 404 "no longer available to new users" (2026-10-15). Thinking is off because, live,
    # default thinking used ~290 hidden tokens of max_tokens=300 and truncated the JSON (see golden.md).
    Provider("gemini", "GEMINI_API_KEY", "https://generativelanguage.googleapis.com/v1beta/openai/",
             "gemini-3.8-flash", reasoning_effort="none"),
    # Untested live (no OpenRouter key); may need its own reasoning setting for the same reason.
    Provider("openrouter", "OPENROUTER_API_KEY", "https://openrouter.ai/api/v1", "google/gemini-3.8-flash"),
)
# USD per million tokens (input, output), Gemini 3.8 Flash promotional price used in docs/spec.md napkin math.
# Verify live before relying on cost figures; the standard price is 1.50 / 7.50.
PRICES = {"gemini-3.8-flash": (0.75, 3.75), "google/gemini-3.8-flash": (0.75, 3.75)}


def cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    price_in, price_out = PRICES.get(model, (0.0, 0.0))  # mock / unknown models cost 0
    return round((prompt_tokens * price_in + completion_tokens * price_out) / 1_000_000, 8)


TEMPERATURE = 0.1
MAX_OUTPUT_TOKENS = 300
MAX_INPUT_TOKENS = 1200
MAX_CALLS = 3

SYSTEM_PROMPT = """You are the guest-messaging assistant of a boutique hotel. You receive one JSON object with:
- guest_message: what the guest wrote (English or Georgian)
- room: the room this message is about and its verification status, decided by the hotel system
- policy_sections: the ONLY hotel policy text you may use

Rules:
1. Answer questions only from policy_sections. If they do not contain the answer, say the information is not available and offer to ask the front desk. Never invent services, times, prices or exceptions.
2. If a request breaks a policy (e.g. outside opening hours), say so politely and quote the rule.
3. For physical service requests (supplies, cleaning, repairs) propose a task. Departments: housekeeping, maintenance, front_desk. Priorities: low, normal, urgent. Keep task under 100 characters, in English, with quantities.
4. If room.status is not "valid", do not promise the service: ask the guest for their room number and the name on the booking.
5. Reply in the guest's language, at most 3 sentences.

Return ONLY a JSON object:
{"intent": "question|service|composite|unclear", "reply": str, "tasks": [{"department": str, "priority": str, "task": str}], "cited_sections": [section ids used], "needs_clarification": bool}"""

CORRECTION_PROMPT = ("Your previous output was not valid for the required schema ({error}). "
                     "Return ONLY the JSON object described in the instructions, nothing else.")


def build_messages(message: str, sections: list[dict], room: str | None, room_status: str) -> list[dict]:
    payload = {
        "guest_message": message,
        "room": {"number": room, "status": room_status},
        "policy_sections": [{"id": s["id"], "text": s["text"]} for s in sections],
    }
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]


def estimate_prompt_tokens(messages: list[dict]) -> int:
    return sum(estimate_tokens(m["content"]) + 4 for m in messages)


@dataclass
class Completion:
    text: str
    prompt_tokens: int
    completion_tokens: int
    estimated: bool
    total_tokens: int = 0  # as reported by the API; can exceed prompt + completion (e.g. hidden thinking tokens)
    finish_reason: str | None = None


class TransientError(RuntimeError):
    """Retryable failure: 429, 5xx, timeout, connection error."""


class ModelClient(Protocol):
    mode: str

    def complete(self, messages: list[dict]) -> Completion: ...

    def complete_tools(self, messages: list[dict], tools: list[dict]) -> tuple[dict, Completion]: ...


class OpenAICompatibleClient:
    """Any OpenAI-compatible chat endpoint (Google AI Studio, OpenRouter): only base_url, key and model differ."""
    mode = "live"

    def __init__(self, provider: Provider, api_key: str, model: str | None = None,
                 temperature: float = TEMPERATURE):
        if temperature > 0.2:
            raise ValueError("temperature must be <= 0.2 for triage")
        import openai  # imported lazily so offline/mock runs need no dependency

        self._openai = openai
        # max_retries=0: the SDK would otherwise retry on its own and break the 3-call cap.
        self._client = openai.OpenAI(base_url=provider.base_url, api_key=api_key, max_retries=0, timeout=10.0)
        self.model = model or provider.default_model
        self.label = f"{provider.name}:{self.model}"
        self.temperature = temperature
        self._extra = {"reasoning_effort": provider.reasoning_effort} if provider.reasoning_effort else {}

    def _create(self, **kwargs):
        """One request. Retryable failures become TransientError; anything else propagates."""
        o = self._openai
        try:
            return self._client.chat.completions.create(**kwargs)
        except (o.APITimeoutError, o.APIConnectionError, o.RateLimitError, o.InternalServerError) as exc:
            raise TransientError(type(exc).__name__) from exc
        except o.APIStatusError as exc:
            if exc.status_code >= 500:
                raise TransientError(f"HTTP {exc.status_code}") from exc
            raise

    def complete(self, messages: list[dict]) -> Completion:
        resp = self._create(
            model=self.model, messages=messages, temperature=self.temperature,
            max_tokens=MAX_OUTPUT_TOKENS, response_format={"type": "json_object"}, **self._extra,
        )
        usage = resp.usage
        choice = resp.choices[0]
        return Completion(choice.message.content or "", usage.prompt_tokens if usage else 0,
                          usage.completion_tokens if usage else 0, estimated=usage is None,
                          total_tokens=(usage.total_tokens or 0) if usage else 0,
                          finish_reason=choice.finish_reason)

    def complete_tools(self, messages: list[dict], tools: list[dict]) -> tuple[dict, Completion]:
        """Function calling: the model may answer, or ask for tools. No response_format here."""
        resp = self._create(model=self.model, messages=messages, tools=tools, tool_choice="auto",
                            temperature=self.temperature, max_tokens=MAX_OUTPUT_TOKENS, **self._extra)
        m = resp.choices[0].message
        calls = []
        for c in m.tool_calls or []:
            call = {"id": c.id, "name": c.function.name, "arguments": c.function.arguments or "{}"}
            # Gemini's OpenAI-compatible endpoint may attach a thought signature here; echo it back unchanged.
            if (extra := getattr(c, "model_extra", None) or {}).get("extra_content"):
                call["extra_content"] = extra["extra_content"]
            calls.append(call)
        extra = getattr(m, "model_extra", None) or {}
        usage = resp.usage
        return ({"content": m.content, "tool_calls": calls, "reasoning_details": extra.get("reasoning_details")},
                Completion("", usage.prompt_tokens if usage else 0, usage.completion_tokens if usage else 0,
                           estimated=usage is None, total_tokens=(usage.total_tokens or 0) if usage else 0))


class MockClient:
    """Deterministic keyword stand-in for the model so the pipeline runs offline and in CI.
    It is NOT evidence of model quality: it only exercises pre-filtering, validation and guardrails."""

    mode = "mock"
    label = "mock"
    _SUPPLIES = {"towel": "towels", "პირსახოც": "towels", "pillow": "pillows", "ბალიშ": "pillows",
                 "blanket": "blankets", "საბან": "blankets", "toiletr": "toiletries", "shampoo": "shampoo"}
    _REPAIRS = {"air condition": "air conditioning not working", r"\bac\b": "air conditioning not working",
                "კონდიციონერ": "air conditioning not working", "leak": "water leak",
                "lock": "door lock problem", "საკეტ": "door lock problem", "broken": "item broken",
                "გაფუჭ": "item broken"}
    _QUESTION = re.compile(r"\?|\b(what|when|where|how|can|could|is|are|does|until)\b|რა |როდის|როდემდე|სად|შეიძლება",
                           re.IGNORECASE)

    def complete(self, messages: list[dict]) -> Completion:
        payload = json.loads(messages[-1]["content"])
        msg = payload["guest_message"]
        low = msg.lower()
        room_ok = payload["room"]["status"] == "valid"
        info_sections = [s for s in payload["policy_sections"] if s["id"] not in ("housekeeping", "maintenance")]

        tasks = []
        for stem, item in self._SUPPLIES.items():
            if stem in low and not any(item in t["task"] for t in tasks):
                qty = re.search(r"(\d+)\s+(?:\S+\s+){0,2}?" + stem, low)
                tasks.append({"department": "housekeeping", "priority": "normal",
                              "task": f"Deliver {qty.group(1) + ' ' if qty else ''}extra {item}"})
        for pattern, issue in self._REPAIRS.items():
            if re.search(pattern, low) and not any(issue in t["task"] for t in tasks):
                tasks.append({"department": "maintenance", "priority": "normal", "task": f"Inspect: {issue}"})

        asks = bool(self._QUESTION.search(msg)) and (bool(info_sections) or not tasks)
        parts = []
        if asks:
            parts += [s["text"] for s in info_sections] or [
                "I'm sorry, I don't have that information; I can ask the front desk to help you."]
        if tasks:
            parts.append("I've passed your request to our team." if room_ok else
                         "To arrange this, please confirm your room number and the name on the booking.")
        intent = "composite" if asks and tasks else "service" if tasks else "question" if asks else "unclear"
        out = {"intent": intent, "reply": " ".join(parts) or "Could you tell me a bit more about what you need?",
               # Proposes tasks even for unverified rooms, like a model ignoring rule 4: the code gate must catch it.
               "tasks": tasks,
               "cited_sections": [s["id"] for s in (info_sections if asks else [])],
               "needs_clarification": bool(tasks) and not room_ok}
        text = json.dumps(out, ensure_ascii=False)
        return Completion(text, estimate_prompt_tokens(messages), estimate_tokens(text), estimated=True)

    def complete_tools(self, messages: list[dict], tools: list[dict]) -> tuple[dict, Completion]:
        """Offline stand-in for function calling: picks lookup_policy by the guide's keywords and
        reads tool results back. Like complete(), it only exercises our gates and loop, not a model."""
        names = {t["function"]["name"] for t in tools}
        last_user = max(i for i, m in enumerate(messages) if m["role"] == "user")
        question = messages[last_user]["content"]
        results = [json.loads(m["content"]) for m in messages[last_user + 1:] if m["role"] == "tool"]
        calls = []
        if results:
            content = " ".join(r["text"] if "text" in r else f"Sorry, that did not work: {r.get('error')}"
                               for r in results)
        else:
            sections = select_sections(question, load_guide())
            if sections and "lookup_policy" in names:
                content = None
                calls = [{"id": f"call_{len(messages)}", "name": "lookup_policy",
                          "arguments": json.dumps({"section": sections[0]["id"]})}]
            else:
                content = "I'm sorry, I don't have that information; I can ask the front desk to help you."
        out = {"content": content, "tool_calls": calls, "reasoning_details": None}
        text = content or json.dumps(calls)
        prompt = json.dumps(messages, ensure_ascii=False) + json.dumps(tools)
        return out, Completion(text, estimate_tokens(prompt), estimate_tokens(text), estimated=True)


def make_client(model: str | None = None, env: Mapping[str, str] | None = None) -> ModelClient:
    """GEMINI_API_KEY first, then OPENROUTER_API_KEY, else the offline mock. Empty values count as unset."""
    env = os.environ if env is None else env
    for provider in PROVIDERS:
        if key := (env.get(provider.key_env) or "").strip():
            return OpenAICompatibleClient(provider, key, model)
    return MockClient()


def complete_tools(messages: list[dict], tools: list[dict], client: ModelClient, *, request_id: str,
                   attempt: int, session_id: str = "act") -> dict:
    """One function-calling turn through `client`, logged to logs/usage.jsonl whether it succeeds or not.
    Returns {"content", "tool_calls", "reasoning_details"}. Errors are logged, then re-raised to the loop."""
    from .pipeline import default_usage_log, write_usage  # lazy: pipeline imports this module

    started = time.perf_counter()
    record = {"timestamp": datetime.now(timezone.utc).isoformat(), "request_id": request_id, "attempt": attempt,
              "status": "error", "prompt_tokens": 0, "completion_tokens": 0}
    try:
        msg, usage = client.complete_tools(messages, tools)
        record.update(status="success", prompt_tokens=usage.prompt_tokens,
                      completion_tokens=usage.completion_tokens, tokens_estimated=usage.estimated)
        return msg
    except Exception as exc:
        status = getattr(exc, "status_code", None)  # never the message: it could echo request details
        record["error"] = (f"transient: {exc}" if isinstance(exc, TransientError)
                           else f"fatal: {type(exc).__name__}" + (f" (HTTP {status})" if status else ""))
        raise
    finally:
        record["latency_ms"] = round((time.perf_counter() - started) * 1000)
        write_usage(default_usage_log(), [record], session_id, client)


def _parse_json(text: str) -> object:
    text = text.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    return json.loads(fenced.group(1) if fenced else text)


@dataclass
class CallOutcome:
    output: ModelOutput | None
    attempts: list[dict]
    error: str | None


def call_with_budget(client: ModelClient, messages: list[dict], request_id: str,
                     sleep: Callable[[float], None] = time.sleep) -> CallOutcome:
    """At most MAX_CALLS model calls; transient errors retry with backoff, schema errors get 1 correction."""
    attempts: list[dict] = []
    convo = list(messages)
    corrected = False
    error = None
    for attempt in range(1, MAX_CALLS + 1):
        started = time.perf_counter()
        record = {"timestamp": datetime.now(timezone.utc).isoformat(), "request_id": request_id,
                  "attempt": attempt, "status": "error", "prompt_tokens": 0, "completion_tokens": 0}
        try:
            completion = client.complete(convo)
            record.update(prompt_tokens=completion.prompt_tokens, completion_tokens=completion.completion_tokens,
                          total_tokens=completion.total_tokens or completion.prompt_tokens + completion.completion_tokens,
                          tokens_estimated=completion.estimated)
            try:
                output = parse_model_output(_parse_json(completion.text))
            except (json.JSONDecodeError, SchemaError) as exc:
                error = (f"schema: output truncated at max_tokens={MAX_OUTPUT_TOKENS} (finish_reason=length)"
                         if completion.finish_reason == "length" else f"schema: {exc}")
                record["error"] = error
                if corrected:
                    break
                corrected = True
                convo = convo + [{"role": "assistant", "content": completion.text},
                                 {"role": "user", "content": CORRECTION_PROMPT.format(error=exc)}]
                continue
            record["status"] = "success"
            return CallOutcome(output, attempts, None)
        except TransientError as exc:
            error = f"transient: {exc}"
            record["error"] = error
            if attempt < MAX_CALLS:
                sleep(0.5 * attempt)
        except Exception as exc:  # non-retryable (auth, bad request): stop immediately
            status = getattr(exc, "status_code", None)  # never the message: it could echo request details
            error = f"fatal: {type(exc).__name__}" + (f" (HTTP {status})" if status else "")
            record["error"] = error
            break
        finally:
            record["latency_ms"] = round((time.perf_counter() - started) * 1000)
            attempts.append(record)
    return CallOutcome(None, attempts, error)
