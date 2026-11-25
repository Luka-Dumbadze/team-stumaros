# Pattern Journal — ZONDROK (CS6920 · StumarOSI)
**Role:** Eval Keeper & Testing Lead  
**GitHub:** [@ZONDROK](https://github.com/ZONDROK)  
**Team:** team-stumaros  

---

## Week 1: Context as Budget
- **Concept:** LLM context windows are a financial and latency budget.
- **Delegation:** Used AI to review prompt token consumption formulas.
- **Verification:** Verified that token counts (`tokens_in`, `tokens_out`), latency, and cost calculations accurately write to `logs/usage.jsonl`.

---

## Week 2: Spec Before Code
- **Concept:** Define formal contracts (endpoints, error schemas) before writing application logic.
- **Delegation:** Assisted in setting up pytest test harnesses and validating custom error shapes (`{"error": ..., "field": ...}`).
- **Verification:** Ran `pytest -q` ensuring room lookup returns 200 for valid rooms and 422 for non-existent rooms.

---

## Week 3: Uncertainty-Aware UX
- **Concept:** Multimodal vision systems must not hallucinate confidence when input images are degraded, dark, or ambiguous.
- **Delegation:** Generated mock visual test cases for clear vs. blurry photo triage in `tests/test_photo_triage.py`.
- **Verification:** Asserted that blurry images enforce `clarification_needed: true` and confidence `< 0.60`, preventing false dispatch.

---

## Week 4: Grounded Generation (RAG & Golden Set)
- **Concept:** Generation must strictly anchor to retrieved factual chunks (`data/policies.json`).
- **Delegation:** Formulated the evaluation structure in `evals/golden.json` covering policy questions (breakfast, pets) and negative ungrounded queries (unanswerable prompts).
- **Verification:** Executed test suite verifying that ungrounded queries trigger safe refusals and that all golden set test cases pass.