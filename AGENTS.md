# AGENTS.md · stumaros

*Instructions for AI coding agents working in this repo. Keep it current; agents read this first.*

## What this project is
An AI guest operations assistant for boutique hotels that handles incoming guest inquiries, provides accurate answers grounded strictly in hotel policy, validates room numbers against active stays, and emits structured dispatch tasks for housekeeping, maintenance, and front-desk staff.

## Stack
- Language: Python 3.11
- Framework: FastAPI
- Model access: OpenRouter · default model: `google/gemini-2.5-flash`
- Data: `data/hotel_guide.json` and `data/active_rooms.json` (checked into repo, read-only)

## How to run
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
pytest
```

## API Contract & State
- **Endpoint:** `POST /chat`
  - **Request Body:** `{ "session_id": str, "message": str, "room": Optional[str] }`
  - **Response Body:** `{ "session_id": str, "reply": str, "tasks": list[Task], "room_validated": bool }`
  - **Task Schema:** `{ "room": str, "department": "housekeeping" | "maintenance" | "front_desk", "priority": "low" | "normal" | "urgent", "task": str }`
- **Session State:** Keep session history in-memory in `app/` (simple dictionary by `session_id`; no external DB files).
- **Turn Definition:** 1 turn = 1 exchange (1 user message + 1 assistant reply).
- **Context Budget:** Strict maximum of the last 4 turns (up to 8 messages total) passed to the model prompt.

## Domain & Validation Rules

### 1. Room Validation
- Schema of `data/active_rooms.json`: `[{ "room": str, "guest_name": str, "check_in": str, "check_out": str, "status": str }]`.
- A room is valid **only if** `status == "checked_in"` and `check_in <= today <= check_out`.
- Room number can be provided via request payload or extracted by the LLM from the user message, but must be checked server-side against `data/active_rooms.json`.
- **Policy/FAQ questions** (e.g., breakfast hours, Wi-Fi) **never** require a valid room. Answer them immediately.
- **Physical service requests** (e.g., towels, repairs) **must** have a validated room. If missing or invalid, do not emit a task; prompt the guest to verify their room number and name.

### 2. Task Dispatching
- **Allowed Departments:** `housekeeping`, `maintenance`, `front_desk`.
- **Allowed Priorities:** `low`, `normal`, `urgent`.
  - Enforce rule overrides in code: water leaks, door/lock failures, and AC issues default to `urgent`; extra supplies default to `normal` or `low`.
- **Composite Messages:** A message containing both a question and a service request produces a conversational answer in `reply` **and** 1 or more items in `tasks`.
- **Groundedness:** If `data/hotel_guide.json` does not answer a query, state the lack of information clearly and offer to escalate to the front desk. Never invent policies or amenities.

## Resilience & Logging
- **Max 3 Calls:** Cap model invocations at 3 per incoming request. This budget covers transient HTTP errors (5xx/429) and at most 1 corrective schema-retry if structured JSON parsing fails.
- **Usage Logging:** Every single LLM attempt (successful, failed, or retried) must append a record to `logs/usage.jsonl` with:
  `{ "timestamp": str, "session_id": str, "request_id": str, "status": "success" | "error", "attempt": int, "prompt_tokens": int, "completion_tokens": int, "latency_ms": int }`.
- **Secrets:** Environment variables only (`OPENROUTER_API_KEY`). Never hardcode or log API keys.

## You may
- Create and edit code in `app/`, `tests/`, `docs/`, `evals/`
- Propose dependency additions in `requirements.txt`
- Add golden scenario fixtures under `evals/`

## You may not
- Introduce external database files or extra storage dependencies (keep state in-memory)
- Modify `data/hotel_guide.json` or `data/active_rooms.json` (these are static human-curated datasets)
- Delete or bypass tests to achieve passing runs
- Execute unbudgeted LLM calls exceeding the 3-attempt limit per request
