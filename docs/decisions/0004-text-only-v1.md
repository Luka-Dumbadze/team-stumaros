# 0004 · StumarOS v1 is text-only (no Week 3 multimodal input)

**Date:** Week 4 · **Decided by:** proposed by Claude Code in the Weeks 1–4 catch-up; Luka Dumbadze and Urju decide in PR review · **Status:** Proposed

**Context.** Week 3 adds an image-to-data feature with a low-confidence path (`Lab-3/templates/multimodal-spec.md`). Guests of a boutique hotel could send photos: a broken fixture, a menu, a document. Meanwhile, text-only p95 latency is already 8.36 s against the spec's 3 s (`hw1/Luka-Dumbadze/golden.md`). The free Gemini tier allows about 20 requests a day.

**Decision.** v1 accepts text only. No image, voice or document input. A guest who sends one is told that images are not processed and is pointed to the front desk. In line with the Lab 3 template, **faces and ID documents are never accepted** in any version, so there is no passport or ID capture at check-in. The Week 3 pattern we do apply is the uncertainty-aware routing for text: `docs/confidence-policy.md`.

**Alternatives.**
- A photo of a broken fixture to pre-fill a maintenance task: plausible, but it adds image tokens and latency to a request that already misses its target, and a text description already routes correctly.
- Menu or notice OCR: the content is already in `data/hotel_guide.json`.

**Consequences.**
- No image tokens, no image personal-data risk, and nothing in `tests/images/`.
- The Design Review states the Lab 3 feature honestly as "not built".
- If a later team decision adds image input, it needs a filled `docs/multimodal-spec.md` (Lab 3 template), test images, a confidence route per field, and a new decision record that supersedes this one.
