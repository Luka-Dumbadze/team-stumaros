# ADR 003 · One OpenAI-SDK client for Gemini and OpenRouter; thinking off

- **Status:** Accepted (Week 4, HW1 live runs on 2026-10-15)
- **Owner:** [@Luka-Dumbadze](https://github.com/Luka-Dumbadze)
- **Code:** `src/llm.py` (`PROVIDERS`, `OpenAICompatibleClient`, `make_client`). **Tests:** `test_gemini_key_wins_over_openrouter_key`, `test_gemini_request_disables_thinking_and_keeps_output_budget`

## Context
`AGENTS.md` names OpenRouter as the model gateway. For HW1 the only working key was a free Google AI Studio key. We wanted to switch providers without rewriting request code or adding a second SDK.

## Decision
- **One client, many endpoints.** All model calls go through the OpenAI Python SDK (`chat.completions.create`, `response_format={"type": "json_object"}`). A provider is just a row in `llm.PROVIDERS`: `base_url`, key variable, default model, optional `reasoning_effort`.
  1. `GEMINI_API_KEY` → `https://generativelanguage.googleapis.com/v1beta/openai/`, `gemini-3.8-flash`
  2. `OPENROUTER_API_KEY` → `https://openrouter.ai/api/v1`, `google/gemini-3.8-flash`
  3. neither → offline `MockClient` (tests and CI)
- **`reasoning_effort="none"` for Gemini.** On the first live call, default thinking spent 575 hidden tokens of the `max_tokens=300` budget. The JSON was cut off after a few characters, the corrective retry timed out, and the request took 25.3 s before falling back. With thinking off, the same prompt returned valid JSON with 0 hidden tokens. A test pins the request parameters (`reasoning_effort`, `max_tokens=300`, `temperature ≤ 0.2`, `json_object`).
- **SDK retries off (`max_retries=0`, `timeout=10 s`).** Our own `call_with_budget` owns retries, so the `AGENTS.md` cap of **3 model calls per request** is real. Truncation (`finish_reason=length`) is reported as truncation, not as a bare JSON error.

## Consequences
- **Good:** moving OpenRouter → Google AI Studio changed configuration only (one table row). Switching back, or A/B testing another OpenAI-compatible model, is a `--model` flag or a key change.
- **Portability is API-shape deep, not behaviour deep.** Model availability and quirks don't port:
  - `gemini-2.5-flash`, the model named in `AGENTS.md`, returned HTTP 404 ("no longer available to new users"), so the default became `gemini-3.8-flash`;
  - thinking behaviour is provider-specific.

  Every provider row needs its own live smoke test.
- **Untested:** the OpenRouter path has never made a live call. It may need its own reasoning setting for the same truncation reason.
- **Follow-up:** `AGENTS.md` still says `google/gemini-2.5-flash`. Update it when the team confirms the provider for the Week 5+ FastAPI service.
