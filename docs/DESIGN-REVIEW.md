# Milestone 1: Design Review · Stumaros

**Product:** Stumaros (სტუმაროს) — AI-Powered Boutique Hotel Operations Assistant  
**Team:** `team-stumaros`  
**Repository:** `https://github.com/Luka-Dumbadze/team-stumaros`  
**Course:** CS6920: Building AI-Powered Applications · Fall 2026 · Kutaisi International University  
**Date:** October 20, 2026  
**Status:** Milestone 1 Release · Tag: `design-review`

---

## 1. Problem Statement and Target Users

### 1.1 The Operational Problem
Boutique hotels in Georgia operate with lean front-desk teams. During peak check-in windows, staff spend over 40% of their shift fielding repetitive guest inquiries (breakfast hours, pool access, checkout policies) while manually transcribing guest requests into housekeeping and maintenance work orders. Miscommunications cause delayed requests, ungrounded amenity promises (e.g., promising late checkouts during full capacity), and operational bottlenecks.

### 1.2 Target Users
1. **The Hotel Guest:** Local and international travelers communicating in English or Georgian via web or messaging apps. They expect instant, accurate answers about hotel amenities and seamless task logging (e.g., extra pillows, AC repair).
2. **The Operations & Front Desk Staff:** Hotel administrators who require structured, validated tasks (categorized by department, room, and urgency) rather than raw, ambiguous chat logs.

### 1.3 Success Criteria (checkable)
The full definitions, scenario mix and fixture format are in [`docs/spec.md` § Success criteria](spec.md#success-criteria). Each criterion below has a numeric threshold, a mechanical check and its status as of Week 4.

| # | Criterion | Threshold | How it is checked | Status (Week 4) |
|---|---|---|---|---|
| S1 | End-to-end latency | p95 ≤ 3,000 ms, max ≤ 6,000 ms per request, retries included (spec); HW1 slice target p95 < 2.5 s | Harness wall-clock (`src/bench.py`; `POST /chat` once it exists) | **FAIL**: HW1 live p95 8.36 s, p50 5.33 s (n = 6 answered) |
| S2 | Model-call budget | 100% of requests ≤ 3 model calls | Code cap in `call_with_budget` + test; audit `request_id` in `logs/usage.jsonl` | **PASS**: `test_transient_errors_capped_at_three_calls`; no live request exceeded 3 calls |
| S3 | Grounded answers | ≥ 90% of answerable questions contain all expected facts; 100% of unanswerable ones say "not available" + offer the front desk; 0 forbidden claims | Regex `must_mention` / `must_not_mention` in [`evals/golden.yaml`](../evals/golden.yaml) | **Not yet measured live** ([§4.2](#42-team-golden-set-week-4-evalsgoldenyaml)) |
| S4 | Room gate and dispatch | 100% of valid-room requests emit exactly the expected tasks; 100% of invalid/missing-room requests emit `tasks: []`, `room_validated: false` and a verification prompt | `must_block_task` / `expected_tasks` in the golden set + parametrised tests | **PASS offline** (tests, mock G1–G3); live pending |
| S5 | Golden-set gate | pass rate ≥ 0.70 | `python evals/run_golden.py` (exit code 1 on failure) | Offline 4/5 = 0.80; first live run 0/5 (provider outage, not model behaviour) |

Cost is tracked separately in [§5](#5-token-and-cost-economics-from-real-logs) (napkin estimate ~$5/month at 200 req/day). It is not a pass/fail criterion in `spec.md`.

The 24-scenario harness that `spec.md` describes, run 3 times through `POST /chat`, is the Week 5+ target. Until then, S3–S5 are measured on the 5-case golden set.

---

## 2. System Architecture and Data Flow

Stumaros follows the core operator maxim: **"Prompting proposes, code governs."** The model is never granted direct database write access or permission to hallucinate operational tasks without code-level verification.

```
                      ┌────────────────────────────────────────┐
                      │              Guest Input               │
                      │    (English / Georgian Message)        │
                      └──────────────────┬─────────────────────┘
                                         │
                                         ▼
                      ┌────────────────────────────────────────┐
                      │       Deterministic Room Check         │
                      │  (Active room, stay dates, guest ID)   │
                      └──────────────────┬─────────────────────┘
                                         │
                      ┌──────────────────┴─────────────────────┐
                      │ Context Filter (Pattern 01: Budget)    │
                      │  Prunes 2,560-token guide to <450 tok  │
                      └──────────────────┬─────────────────────┘
                                         │
                                         ▼
                      ┌────────────────────────────────────────┐
                      │ LLM Gateway (Gemini 3.8 Flash / OpenAI)│
                      │  - reasoning_effort="none"             │
                      │  - Strict JSON Task & Reply Schema     │
                      └──────────────────┬─────────────────────┘
                                         │
                                         ▼
                      ┌────────────────────────────────────────┐
                      │  Grounding & Task Validation Gate      │
                      │  - Drops tasks lacking active room     │
                      │  - Forces AC/water leaks to URGENT     │
                      │  - Regex checks prices & times         │
                      └──────────────────┬─────────────────────┘
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
   ┌─────────────────────────────┐                   ┌───────────────────────────┐
   │ Verified Guest Reply        │                   │ Structured Staff Work     │
   │ (Natural Language Response) │                   │ Order (JSON / DB Task)    │
   └─────────────────────────────┘                   └───────────────────────────┘
```

### 2.1 Architectural Invariants
* **Pre-Execution Gate:** Room resolution and validation run in code *before* the model call. If a guest request omits a room number, references an expired stay, or names a conflicting room, the model still answers any policy question, but code drops every proposed task and asks for room number + booking name ([ADR 001](decisions/001-room-gate-in-code.md)).
* **Context Budget Gate:** The complete hotel guide (~2,560 tokens) is never dumped into the prompt. Keyword-anchored pre-filtering extracts at most 3 relevant policy sections, capping prompt input to under 500 tokens.
* **Deterministic Guardrails:** The LLM's role is restricted to natural-language drafting and intent extraction. Code handles priority escalation (e.g., water leaks are automatically forced to `urgent`) and unverified price/time rejection.

### 2.2 Input Scope and Confidence Policy
* **Text only in v1.** No Week 3 multimodal input (no poster/menu OCR, no guest ID photos): latency is already over budget and ID images are high-risk personal data. Check-in ID capture on the staff side is the candidate for a later ADR. See [ADR 004 · Part A](decisions/004-multimodal-and-confidence-policy.md#part-a--multimodal-input-week-3-pattern).
* **Never guess.** A missing, ambiguous or invalid room, a question no guide section answers, an unsupported number, or a model failure always routes to clarification or the front desk. Confidence comes from deterministic signals in code, never from a model-reported score. The full signal → behaviour table, including the gaps that are still prompt-only, is [ADR 004 · Part B](decisions/004-multimodal-and-confidence-policy.md#part-b--confidence-policy-uncertainty-aware-ux).
* All decision records: [`docs/decisions/`](decisions/).

---

## 3. Risks, Safety Threats, and Mitigations

Every risk has a named owner, assigned from the roster in [`docs/team.md`](team.md). The role column says which hat is accountable. Owners should be redistributed once the roster is final (see [§6.1](#61-team-roster-and-responsibilities)). Cross-cutting rule: when the system is unsure, it asks or escalates instead of guessing ([confidence policy, ADR 004 Part B](decisions/004-multimodal-and-confidence-policy.md#part-b--confidence-policy-uncertainty-aware-ux)).

| Threat | Impact | Mitigation implemented | Owner (role) |
| :--- | :--- | :--- | :--- |
| **Ungrounded Financial Liability** | Model invents free services (e.g., free airport shuttle, complimentary breakfast). | **Numbers:** code replaces any reply containing a time/price absent from the sent policy text or the guest message with *"I don't have that information; I can ask the front desk to help you."* **Non-numeric claims** ("yes, we have a shuttle") are blocked **by the prompt only**: a known gap, tracked by golden case G5 ([ADR 004](decisions/004-multimodal-and-confidence-policy.md), signal 7). | @Luka-Dumbadze (grounding & evals) |
| **Georgian Substring Collision** | In Georgian, pool (`აუზ`) is a substring of breakfast (`საუზმე`), causing wrong policy injection. | Word-start matching for Georgian stems in `prefilter.py`, backed by an exact-sections regression test ([ADR 002](decisions/002-georgian-word-start-matching.md)). Typo / Latin-script input is still unmatched (golden G4). | @Luka-Dumbadze (context pre-filter) |
| **Reasoning Token Quota Exhaustion** | Gemini default "thinking" tokens consume output budget, truncating JSON and triggering 25s timeouts. | Hardcoded `reasoning_effort="none"` in the API client adapter, pinned by automated unit tests ([ADR 003](decisions/003-openai-endpoint-portability.md)). | @Luka-Dumbadze (LLM gateway) |
| **Unauthorized Task Injection** | Malicious users fabricate work orders for rooms they do not occupy. | Deterministic verification matches room state against active reservation dates in `active_rooms.json` before creating staff tasks; conflicting rooms are not trusted ([ADR 001](decisions/001-room-gate-in-code.md)). | @Luka-Dumbadze (architecture & guardrails) |
| **Service Quota Denial of Service** | Free-tier limits (20 req/day) and provider outages cause cascading 5xx/429 errors (all 15 calls failed in the 2026-11-24 live golden run). | Graceful degradation: at most 3 calls, then a safe front-desk fallback with no tasks, logged as `model_failed`. **Gap:** the fallback says the message was "flagged for the front desk", but nothing notifies staff until `POST /chat` surfaces it. | @Luka-Dumbadze (LLM gateway) |
| **Priority Over-escalation** *(found Week 4)* | Unanchored urgent keywords mark "bottles of water", "7 o'clock" and "towels outside the door" as `urgent`, flooding the 15-minute channel. | Not yet fixed: word boundaries + failure-intent check + regression tests ([ADR 001](decisions/001-room-gate-in-code.md), consequences). | @Luka-Dumbadze (architecture & guardrails) |

---

## 4. Evaluation Plan and Empirical Telemetry

### 4.1 HW1 Live Golden Results (2026-10-15)
Three golden scenarios were run live through the HW1 slice. Full log: [`hw1/Luka-Dumbadze/golden.md`](../hw1/Luka-Dumbadze/golden.md). *(Inputs corrected in Week 4 to the exact strings that were run.)*

| ID | Scenario | Input | Expected Output | Live Result (Gemini 3.8 Flash) | Tokens (In / Out) | Latency |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **G1** | Georgian: Pillows & Breakfast | *"გამარჯობა! ოთახი 204-ში 2 დამატებითი ბალიში გვჭირდება. როდემდეა საუზმე?"* | Answers breakfast hours (07:00–10:30); dispatches normal housekeeping task for Room 204 within 30 min. | **PASS** | 463 / 145 | 5.35 s |
| **G2** | Policy Violation: Pool at 23:30 | *"Room 305 here. Can we use the pool at 23:30 tonight? Also please send 2 towels."* | Notes pool closes at 22:00; flags Room 305 as checked-out; blocks staff task creation. | **PASS** | 466 / 89 | 6.22 s |
| **G3** | Missing Information: AC Broken | *"The AC isn't working and it's really hot, please help!"* | Refuses task creation due to missing room; requests room number and guest name; escalates to front desk. | **PASS** *(Recovered from initial API 500)* | 391 / 83 | 5.01 s |

### 4.2 Team Golden Set (Week 4): [`evals/golden.yaml`](../evals/golden.yaml)
The three HW1 cases are now machine-checkable team cases, plus two new ones. Each case declares `must_mention` / `must_not_mention` regexes and either `must_block_task: true` or the exact `expected_tasks`. A case that ends in the model-failure fallback never passes. Runner: [`evals/run_golden.py`](../evals/run_golden.py). Reports, with an interpretation index: [`evals/results/`](../evals/results/).

| ID | Category | Case | Offline (mock) | Live (2026-11-24) |
| :--- | :--- | :--- | :--- | :--- |
| G1 | factual | Georgian pillows + breakfast, room 204 | PASS | provider outage |
| G2 | policy / refusal | Pool at 23:30 + towels from checked-out 305 | PASS | provider outage |
| G3 | uncertainty | Broken AC, no room | PASS | provider outage |
| G4 | edge / typo | *"gamarjoba! wat time is chek out tmrw??"* | **FAIL**: pre-filter has no typo tolerance, so no policy is sent | provider outage |
| G5 | hallucination guard | *"Do you provide a free airport shuttle?"* (not in the guide) | PASS (meaningless: the mock cannot hallucinate) | provider outage, retried: **still unverified** |

* **Offline:** 4/5 = 0.80, above the 0.70 threshold. This verifies the code gates only.
* **Live:** both live attempts on 2026-11-24 failed on infrastructure (HTTP 500/503 "high demand", timeouts, 429s on all 18 calls). They say nothing about model quality. G5, the non-numeric hallucination test, remains **open** and is the first thing to run on a fresh quota.

### 4.3 Week 11 Golden Set Gate (plan)
* **Size and mix:** 10 questions in a **3 / 2 / 2 / 2 / 1** mix:
  * 3 factual (policy answers, EN + KA)
  * 2 policy-violation / refusal
  * 2 uncertainty (missing / invalid / conflicting room)
  * 2 edge (typos, Latin-script Georgian, composite)
  * 1 hallucination guard (amenity not in the guide)

  It grows from the five cases above, in the same `golden.yaml` format.
* **Threshold:** pass rate **≥ 0.70** (at least 7 of 10). Any `must_block_task` violation, i.e. a task dispatched for an unverified room, is reported as a failure regardless of the overall rate.
* **CI gate:** a GitHub Actions workflow runs `pytest` and `python evals/run_golden.py` on every pull request. The runner exits `1` below threshold, and branch protection makes that check **required, so a failing gate blocks merge**.
* **Live vs. offline in CI:** the live gate needs `GEMINI_API_KEY` or `OPENROUTER_API_KEY` as a CI secret. Ten cases at up to 3 calls each is 30 calls, which exceeds the free tier's ~20/day, so the live gate needs a paid or OpenRouter key. Without one, CI runs the mock gate, clearly labelled offline in the report, and a live run is required before each release tag.
* **Status:** planned, not implemented. There is no `.github/workflows/` yet.

### 4.4 Latency Benchmark & SLA Analysis
* **Initial Spec SLA Target:** p95 latency < 2.5 seconds.
* **Empirical Live Measurement (10-request benchmark):**
  * Answered Requests (6): **p50 = 5.33 s, p95 = 8.36 s**.
  * Failed / Rate-Limited Requests (4): Served via immediate local fallback.
* **Evaluation Hygiene:** Benchmark tooling (`bench.py`) was refactored to explicitly separate answered requests from failed fallbacks to prevent artificially deflating the latency score.
* **Roadmap to Target:** The measured p95 latency currently exceeds the 2.5s target due to transatlantic API transit and cloud generation. Weeks 6 (Streaming SSE) and 10 (Local caching of static policy queries) will bring effective guest-facing time-to-first-token under 1.5 seconds.

---

## 5. Token and Cost Economics (From Real Logs)

### 5.1 The Napkin Cost Calculation
Using the verified Course Formula for **Gemini 3.8 Flash** ($0.75 / 1M input tokens, $3.75 / 1M output tokens):

$$\text{Monthly Cost} = \Big(\text{req / day} \times (\text{tokens}_{\text{in}} \times \text{price}_{\text{in}} + \text{tokens}_{\text{out}} \times \text{price}_{\text{out}})\Big) \times 30$$

Projecting boutique hotel volume at **200 requests / day**:

* **Naive Context Architecture (Sending full guide every call):**
  * Average Input: 2,560 tokens | Average Output: 110 tokens
  * Monthly Cost: $\Big(200 \times (2,560 \times 0.00000075 + 110 \times 0.00000375)\Big) \times 30 = \mathbf{\$14.00 \text{ / month}}$
* **Stumaros Trimmed Architecture (Pattern 01: Context as Budget):**
  * Average Input: 440 tokens | Average Output: 105 tokens
  * Monthly Cost: $\Big(200 \times (440 \times 0.00000075 + 105 \times 0.00000375)\Big) \times 30 = \mathbf{\$4.34 \text{ / month}}$
* **Economic Impact:** Pre-filtering delivers a **69% recurring cost reduction** while preventing prompt context dilution.

### 5.2 Georgian Token Penalty
Testing confirmed that Georgian text tokenizes **2.5x to 3.2x heavier** than equivalent English semantics (e.g., Case 1 input tokenized at 463 tokens vs ~170 tokens for equivalent English phrasing). Context budgeting is vital in Georgia to keep bilingual systems within the sub-$5/month operational bracket.

---

## 6. Team Structure, Governance, and Key Decisions

### 6.1 Team Roster and Responsibilities
* **Luka Dumbadze ([@Luka-Dumbadze](https://github.com/Luka-Dumbadze)):** System Architecture, LLM Gateway Integration, Evaluation Pipeline, and Context Pre-filter optimization.
* **Team Governance:** Code reviewed through PRs; releases gated on passing unit tests and golden benchmarks (CI enforcement planned for Week 11, [§4.3](#43-week-11-golden-set-gate-plan)).
* **Team contract ([`docs/team-contract.md`](team-contract.md)): DRAFT, not complete.** The roles are still "idk yet". The decision rule, weekly sync time and no-show rule are unfilled placeholders, and the members table is malformed. Its only commit is the initial template (2026-10-15), so no member has signed the filled-in contract. Due at team lock (end of Week 3), so it is **overdue**. Roster: [`docs/team.md`](team.md). Open question: `hw1/UrjuHub/` and most early commits come from GitHub user UrjuHub, who is not yet listed in the roster or the contract.

### 6.2 Key Operator Decisions & Trade-Offs
1. **Domain Realignment (Boutique Hotel vs. Campus Dorms):** The team aligned the system strictly around boutique hospitality in Georgia, updating specifications rather than forcing mismatched course templates.
2. **Rejection of Model Autonomy for Task Escalation:** An early agent critique suggested having the LLM dynamically decide task priority. This was deliberately **rejected**: safety-critical priorities (water leaks, door locks, AC outages) are enforced deterministically in Python ([ADR 001](decisions/001-room-gate-in-code.md)).
3. **OpenAI Endpoint Portability:** Standardizing on Google AI Studio's `/v1beta/openai/` endpoint enables zero-rewrite migration between Gemini and OpenRouter frontier models ([ADR 003](decisions/003-openai-endpoint-portability.md)).
4. **Georgian word-start matching** in the pre-filter ([ADR 002](decisions/002-georgian-word-start-matching.md)).
5. **Text-only v1 and a never-guess confidence policy** ([ADR 004](decisions/004-multimodal-and-confidence-policy.md), *Proposed*).

All decisions are recorded as ADRs in [`docs/decisions/`](decisions/).