# Delegation log · StumarOS

One entry per delegation that mattered (`Lab-2/templates/delegation-log.md`). Individual HW1 logs stay in `hw1/<username>/delegation.md`.

Entries 1–8 cover the Weeks 1–4 catch-up on branch `chore/weeks1-4-catchup` (2026-11-24). Luka Dumbadze delegated the whole pass to **Claude Code (Opus 5.5)** in one session, in two prompts:
- **Pass 1** worked from the prompt and the team repo only.
- **Pass 2** realigned everything to the course templates in `AIPSD-F26` (Weeks 1–4).

Everything below is AI-drafted and **not yet reviewed by a teammate**. It goes through the PR.

### Entry 1 · Promote HW1 slice to root
- **Task:** promote `hw1/Luka-Dumbadze/src/` to root `src/` and `tests/`. Add the mock data to `data/`, plus `requirements.txt`, `.env.example` and `pytest.ini`.
- **Delegated to:** Claude Code (Opus 5.5), with the full repo, `AGENTS.md` and the HW1 folder.
- **Plan check:** none. Gate 1 was skipped; the prompt was executed directly.
- **Came back wrong:** nothing in the move itself. Checked: 38/38 tests pass at the root and in the untouched HW1 copy. One choice to review: the data moved to root `data/` (per `AGENTS.md`), not `src/data/`.
- **Caught by:** running both suites.
- **Decision:** committed on the branch; merge pending PR review.
- **AGENTS.md change:** none.
- **Cost:** a few minutes; no API calls.

### Entry 2 · Golden set and runner
- **Task:** `evals/golden.yaml` (5 questions), `evals/run_golden.py` and committed results.
- **Delegated to:** Claude Code. Pass 1 had no course templates; pass 2 used `Lab-4/templates/golden-set.yaml` and the CampusPulse runner.
- **Plan check:** none.
- **Came back wrong:**
  - Pass 1 invented its own schema (`cases`, `must_block_task`) instead of the Lab 4 one.
  - Pass 1 **mislabelled the Week 11 mix** as factual / policy / uncertainty / edge / hallucination. The course mix is **3 factual, 2 reasoning, 2 edge, 2 refusal, 1 format**.
- **Caught by:** Luka asked whether the course templates had been used. The agent then compared its output with the templates.
- **Decision:** converted to the Lab 4 schema (`items`, `type`, `expect`, `must_cite`, `must_mention`, `why`) in the Week 4 mix. The same five scenarios are kept, dispatch checks stay as documented extensions, and nothing was weakened.
- **AGENTS.md change:** none yet. Proposed: "Course templates in AIPSD-F26 are the source of truth for milestone documents; read them before drafting."
- **Cost:** one extra pass.

### Entry 3 · Live golden runs
- **Task:** run the golden set live if the key and quota allow.
- **Delegated to:** Claude Code, using the free Gemini key in `hw1/Luka-Dumbadze/.env`. The key was loaded with `--env-file`, never printed or copied.
- **Plan check:** none.
- **Came back wrong:**
  - Every live call failed (HTTP 500/503 "high demand", timeouts, 429s).
  - The first report labelled its commit `+dirty`, because the snapshot was taken after the run while docs were being edited.
- **Caught by:** the agent read the reports, then made one diagnostic call that showed the 503.
- **Decision:** the failed runs are committed as an outage record, not a model result. The runner now snapshots the commit before running and offers `--only` partial runs. g5 is still unverified.
- **AGENTS.md change:** none.
- **Cost:** 19 of about 20 free-tier calls that day (18 runner + 1 diagnostic), all failed.

### Entry 4 · Decision records 0001 to 0004
- **Task:** record the room gate, Georgian matching, endpoint portability, and the multimodal decision.
- **Delegated to:** Claude Code.
- **Plan check:** none.
- **Came back wrong:**
  - Pass 1 used its own numbering and format.
  - Pass 1's ADR 004 **suggested check-in ID capture** as a future feature. The Lab 3 multimodal template forbids ID documents. Removed.
  - While drafting 0001, the agent found a real bug: urgent keywords without word boundaries ("water", "o'clock", "door").
- **Caught by:** the course templates (pass 2); a probe script for the bug.
- **Decision:** rewritten in `0000-template.md` form. 0004 is **Proposed**, decided in PR review. The bug is documented, not fixed.
- **AGENTS.md change:** none.
- **Cost:** small.

### Entry 5 · Design Review revision (all six sections)
- **Task:** fix the Design Review per instructor feedback. Every section of this revision (§1–§6), the Mermaid diagram and the model-call table were drafted by the agent.
- **Delegated to:** Claude Code, with `Lab-4/DESIGN-REVIEW.md` (rubric), the template and the CampusPulse example (pass 2).
- **Plan check:** none.
- **Came back wrong:**
  - Pass 1 **invented a cost criterion** (S6) that the spec does not have; the agent removed it.
  - Pass 1 claimed a **one-member team**; `git log` showed Urju's 22 commits.
  - Pass 1 grew the file to 2,581 words, against a limit of about 1,600.
  - The old §5.2 claimed a 2.5–3.2x Georgian *input* penalty. HW1 measured 463 vs 466 input tokens, with the difference in output (about 1.6x).
- **Caught by:** the agent's own checks (git history, arithmetic) and the course rubric.
- **Decision:** rebuilt on the Lab 4 template at 1,596 words. Every number was recomputed from `hw1/Luka-Dumbadze/golden.md`. The team must review it before merge.
- **AGENTS.md change:** none.
- **Cost:** two drafts.

### Entry 6 · Confidence policy
- **Task:** `docs/confidence-policy.md` from the Lab 3 template.
- **Delegated to:** Claude Code.
- **Plan check:** none.
- **Came back wrong:** pass 1 buried the policy inside ADR 004 instead of the template file. Checked in pass 2: every quoted guest message was copied from `src/pipeline.py`, and every test named exists.
- **Caught by:** the course templates.
- **Decision:** a standalone file. It marks where the code does not yet match the table (no route names, no review queue, cited-unsent is only logged).
- **AGENTS.md change:** none.
- **Cost:** small.

### Entry 7 · Repo files and usage logging
- **Task:**
  - README on the course template
  - `TEAM-CONTRACT.md` moved to the root
  - `docs/TEAM-REPO.md`, `docs/journal/*.md`
  - `.github/workflows/ci.yml`, the PR template, `CLAUDE.md`
  - the `AGENTS.md` model line
  - default logging of every model attempt to `logs/usage.jsonl`, plus `evals/usage_summary.py`
- **Delegated to:** Claude Code.
- **Plan check:** none.
- **Came back wrong:** nothing found. Checked: 53/53 tests, including a log-shape test for the `AGENTS.md` fields. All links resolve. TEAM-REPO sections 2–11 are byte-identical to the course guide.
- **Caught by:** tests, a link checker, `diff` against the template.
- **Decision:** human-owned content is left as marked skeletons: roles, contract terms, journal entries.
- **AGENTS.md change:** the model became `gemini-3.8-flash` (`gemini-2.5-flash` returns 404), and `GEMINI_API_KEY` was added.
- **Cost:** small.

### Entry 8 · HW1 rung wording and PII scrub
- **Task:**
  - name the Autonomy Ladder rung in `hw1/Luka-Dumbadze/delegation.md`;
  - remove personal emails from the docs.
- **Delegated to:** Claude Code.
- **Plan check:** none.
- **Came back wrong:** pass 1 wrote "Rung 3… I did not review each line". By the course definition, rung 3 *requires* reading every line. Now reworded: rung 3 was intended, and verification stays below rung 3 until Luka signs off `pipeline.py` and `prefilter.py`. The email is gone from current files, but old commits keep it. History is deliberately not rewritten, to avoid force-pushing over a teammate's clone.
- **Caught by:** Luka's question about the templates, then the rung definition in the Lab 3/4 READMEs.
- **Decision:** wording fixed. The sign-off table is left for Luka; an agent must not tick it.
- **AGENTS.md change:** none.
- **Cost:** small.

### Entry 9 · Spec, contract, team guide, journal
- **Task:**
  - align `docs/spec.md` with the Design Review (model, napkin math);
  - fill `TEAM-CONTRACT.md` and `docs/TEAM-REPO.md` §1 from the real repo activity;
  - assemble `docs/journal/Luka-Dumbadze.md` from Luka's existing entries;
  - set a noreply git identity;
  - run g5 live once;
  - push and open a draft PR.
- **Delegated to:** Claude Code (Opus 5.5), with `git log`, `hw1/UrjuHub/`, the `gh` CLI (Luka's account) and the course guide.
- **Plan check:** none. Executed from a detailed prompt.
- **Came back wrong / judgement calls to review:**
  - **Roles are inferred, not agreed.** Luka is Repo + Eval keeper, because the guide says the repo keeper stays the owner and Luka owns the repo. Urju is Spec + Data & content keeper, with no `src/` or `tests/` commits yet. The contract is marked *proposed*; Urju may change any line when signing.
  - **Unpushed history was rewritten.** The noreply rule was "future commits only". But 5 of the branch's 7 unpushed commits carried the personal gmail address, so before the first push all 7 were re-stamped with `<id>+Luka-Dumbadze@users.noreply.github.com`. The tree, messages and dates are identical; `main` and pushed history are untouched. Old hashes are mapped in `evals/results/README.md`.
  - **The journal is verbatim, but its provenance is mixed.** HW1's `delegation.md` says the agent wrote the first draft of the HW1 journal. The entries were copied by script, unchanged, with a note asking Luka to confirm or rewrite them.
  - **g5 live failed again:** 3 × HTTP 500 (server-side, not 429), run once as instructed.
  - **Found while preparing Luka's line-by-line walkthrough** (confirmed by probe; not fixed, listed in the PR as follow-ups):
    - `pipeline.py:151` leaves `needs_clarification` false when the verification request is appended for a service intent with no proposed task;
    - the Georgian stem `კარი` (door) matches `კარიერა` (career), both in section selection and in the urgent regex;
    - truncation at 1,000 characters (`prefilter.py:88`) is silent and can drop the room number.
- **Caught by:** `git log` stats; a check that the tree is identical after the identity rewrite; a script asserting every journal entry is a verbatim substring; a `diff` showing TEAM-REPO §2–11 still match the course guide byte for byte.
- **Decision:** committed on the branch and pushed as a **draft** PR. Merge waits for Urju's signing commit and review.
- **AGENTS.md change:** none.
- **Cost:** 3 live calls (all failed); 22 live calls that day in total.

### Entry 10 · Sign-off recorded, third member added
- **Task:** record Luka's line-by-line review in `hw1/Luka-Dumbadze/delegation.md`, sign Luka's line in `TEAM-CONTRACT.md`, add Mariami Tskhomelidze (@ZONDROK) to the team docs, and mark PR #1 ready for review.
- **Delegated to:** Claude Code (Opus 5.5). Mariami's display name was read from their public GitHub profile; no email was fetched.
- **Plan check:** none.
- **Came back wrong / judgement calls to review:**
  - **Sign-off scope:** only the `pipeline.py` and `prefilter.py` rows are ticked, because those are the files Luka said he reviewed. `llm.py`, `schemas.py` and the `golden.md` row stay open, and the signature statement names the two files instead of "the code above".
  - **Which copy:** Luka reviewed the root `src/` copy. A `diff` shows its gate and guardrail logic matches the HW1 folder, and the note says so.
  - **Who ticked:** the boxes and Luka's contract line were entered by the agent on Luka's explicit instruction, in a commit from his account. Both files say this.
  - **Keeping files consistent:** Mariami was also added to the Design Review's Members line, §6 and the README, so no file lists two members. Mariami's roles are left "to agree", and the rota now runs Luka → Urju → Mariami.
- **Caught by:** `diff` (HW1 vs root code, and TEAM-REPO §2–11 vs the course guide), the Design Review word count (1,597), the link checker.
- **Decision:** committed, pushed, PR #1 marked ready for review.
- **AGENTS.md change:** none.
- **Cost:** no API calls.
