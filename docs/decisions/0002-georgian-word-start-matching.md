# 0002 · Georgian keywords match at word start only

**Date:** Week 3 (HW1), recorded Week 4 · **Decided by:** Luka Dumbadze

**Context.** The pre-filter (`select_sections` in `src/prefilter.py`) sends at most 3 guide sections, about 460 tokens instead of about 2,560. It picks them by keyword. Georgian keywords are stems (`ბალიშ`, `საუზმ`, `აუზ`) because one stem takes many suffixes. With plain substring matching, **`აუზ` (pool) matched inside `საუზმე` (breakfast)**, and the HW1 golden case 1 reply quoted pool rules. The unit test for that input still passed because it only checked for `10:30`; reading the actual output caught it.

**Decision.**
- ASCII keywords match as whole words plus simple English suffixes.
- Georgian stems match only at word start: `\b<stem>`, suffixes allowed.
- A regression test asserts the exact sections selected (`["breakfast", "housekeeping"]`). A second test covers `კარ` (door) inside `კარგი` (good).

**Alternatives.**
- A Georgian morphological analyser: correct, but a new dependency for nine sections.
- Embedding retrieval (the Lab 4 default): fuzzier, but adds an embedding call and index for a 9-section guide.
- Sending the whole guide: about 5x the input tokens (DESIGN-REVIEW §5).

**Consequences.**
- No new dependency, and golden g1 guards the bug (`must_not_mention: 22:00`).
- Prefix collisions are still possible, so each new Georgian stem needs a check against common words.
- No typo or Latin-script tolerance: golden **g4** ("chek out") gets no section and escalates instead of answering 11:00. That failure is recorded in `evals/results/`.
- Revisit with fuzzy matching or embeddings, with a new decision record.
