# 0003 · One OpenAI-SDK client for Gemini and OpenRouter, thinking off

**Date:** Week 4 (HW1 live runs, 2026-10-15) · **Decided by:** Luka Dumbadze

**Context.** `AGENTS.md` named OpenRouter, but the only working key was a free Google AI Studio key. We wanted to switch providers without new request code. On the first live call, Gemini's default "thinking" used 575 hidden tokens of `max_tokens=300`. The JSON was cut off, the retry timed out, and the request took 25.3 s.

**Decision.** All calls go through the OpenAI SDK (`chat.completions.create`, `response_format=json_object`). A provider is one row in `llm.PROVIDERS`:

| Key | Endpoint | Model |
|---|---|---|
| `GEMINI_API_KEY` | `https://generativelanguage.googleapis.com/v1beta/openai/` | `gemini-3.8-flash`, `reasoning_effort="none"` |
| `OPENROUTER_API_KEY` | `https://openrouter.ai/api/v1` | `google/gemini-3.8-flash` |
| neither | offline mock | none |

SDK retries are off (`max_retries=0`, 10 s timeout), so our `call_with_budget` enforces the `AGENTS.md` cap of 3 calls per request.

**Alternatives.**
- Google's own `google-genai` SDK: a second code path to test.
- Keeping thinking on with a larger `max_tokens`: higher cost per request and slower, for a task that does not need reasoning.

**Consequences.**
- Switching provider is configuration only.
- Behaviour does not port:
  - `gemini-2.5-flash` returns HTTP 404 ("no longer available to new users"), which is why `AGENTS.md` now names `gemini-3.8-flash`;
  - reasoning settings are per provider.
- The OpenRouter row has never made a live call.
- A test pins `reasoning_effort`, `max_tokens=300`, `temperature ≤ 0.2` and `json_object`.
