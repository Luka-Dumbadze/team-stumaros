# ADR 002 · Georgian keywords match at word start only

- **Status:** Accepted (Week 3, HW1; recorded Week 4)
- **Owner:** [@Luka-Dumbadze](https://github.com/Luka-Dumbadze)
- **Code:** `src/prefilter.py` (`_keyword_hits`, `select_sections`). **Test:** `test_prefilter_georgian_stem_matches_only_at_word_start`

## Context
To keep the prompt small ([context budget](../spec.md): ≤ 3 policy sections, ~400–470 tokens instead of ~2,560), `select_sections` picks guide sections by keyword. Georgian is agglutinative: one stem takes many suffixes (`ბალიში`, `ბალიშები`, `ბალიშს`). So Georgian keywords are **stems** (`ბალიშ`, `საუზმ`, `აუზ`), and they must match inflected forms.

The first version matched Georgian stems as plain substrings. That broke on the golden input *"ოთახი 204-ში 2 ბალიში. როდემდეა საუზმე?"* (pillows + breakfast): **`აუზ` (pool) occurs inside `საუზმე` (breakfast)**. The pool rules went into the prompt and then into the reply. The unit test for that input still passed, because it only checked that `10:30` appeared. The bug was caught by reading the actual golden output, not the green test run.

## Decision
- ASCII keywords match as whole words, plus simple English suffixes: `\bkeyword(?:s|es|ing|ed)?\b`, case-insensitive.
- Georgian stems match **at word start only**: `\b<stem>` with no trailing boundary. Suffixes are still allowed (`აუზი`, `აუზზე`), but a stem buried inside another word (`ს·აუზ·მე`) is not.
- A regression test asserts the **exact** selected sections (`["breakfast", "housekeeping"]`), not just a fact in the reply. A second test covers `კარ` (door) inside `კარგი` (good).

## Consequences
- **Good:** fixes the collision without a Georgian morphological analyser or any new dependency. Golden case G1 asserts that pool hours (`22:00`) never leak into the breakfast reply.
- **Limits:**
  - Prefix stems can still collide with unrelated words that *start* with the same letters. Each new Georgian keyword needs a quick check against common words.
  - Matching is exact. There is no typo tolerance and no Latin-script ("translit") Georgian. Golden case **G4** (`"gamarjoba! wat time is chek out tmrw??"`) gets no policy section at all, so the system escalates instead of answering 11:00. That gap is recorded in `evals/results/`.
  - Candidate fixes for later weeks: normalised/fuzzy keyword matching, or embedding retrieval. Both need their own context-budget and false-positive tests.
