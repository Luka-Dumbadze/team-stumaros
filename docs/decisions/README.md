# Architecture Decision Records

| # | Decision | Status |
|---|---|---|
| [001](001-room-gate-in-code.md) | Room gate and urgent escalation are enforced in code, not in the prompt | Accepted |
| [002](002-georgian-word-start-matching.md) | Georgian keywords match at word start only | Accepted |
| [003](003-openai-endpoint-portability.md) | One OpenAI-SDK client for Gemini and OpenRouter; thinking off | Accepted |
| [004](004-multimodal-and-confidence-policy.md) | No multimodal input in v1; explicit uncertainty-aware confidence policy | Proposed |

New ADRs: next number, one decision per file. Sections: Status / Owner / Context / Decision / Consequences, with evidence (test names, golden cases, logs). Mark a decision superseded; never delete it.
