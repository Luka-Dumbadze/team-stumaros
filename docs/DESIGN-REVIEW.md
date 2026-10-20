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
* **Pre-Execution Gate:** If a guest request omits a room number, references an expired stay, or names a conflicting room, deterministic code halts model task generation and prompts the user for clarification.
* **Context Budget Gate:** The complete hotel guide (~2,560 tokens) is never dumped into the prompt. Keyword-anchored pre-filtering extracts at most 3 relevant policy sections, capping prompt input to under 500 tokens.
* **Deterministic Guardrails:** The LLM's role is restricted to natural-language drafting and intent extraction. Code handles priority escalation (e.g., water leaks are automatically forced to `urgent`) and unverified price/time rejection.

---

## 3. Risks, Safety Threats, and Mitigations

| Threat | Impact | Concrete Mitigation Implemented |
| :--- | :--- | :--- |
| **Ungrounded Financial Liability** | Model invents free services (e.g., free airport shuttle, complimentary breakfast). | Code-level grounding gate scans generated replies against policy context. Discrepant prices or times trigger an immediate fallback: *"Let me connect you with the front desk."* |
| **Georgian Substring Collision** | In Georgian, pool (`აუზ`) is a substring of breakfast (`საუზმე`), causing wrong policy injection. | Shifted from raw substring matching to word-boundary/prefix-based matching in `prefilter.py`, backed by regression tests. |
| **Reasoning Token Quota Exhaustion** | Gemini default "thinking" tokens consume output budget, truncating JSON and triggering 25s timeouts. | Hardcoded `reasoning_effort="none"` in the API client adapter, pinned by automated unit tests. |
| **Unauthorized Task Injection** | Malicious users fabricate work orders for rooms they do not occupy. | Deterministic verification matches room state against active reservation dates in `active_rooms.json` before creating staff tasks. |
| **Service Quota Denial of Service** | Free-tier limits (20 req/day) cause cascading 500 errors. | Graceful degradation: after retries, system returns a safe front-desk escalation message while logging failure metrics. |

---

## 4. Evaluation Plan and Empirical Telemetry

### 4.1 The Golden Evaluation Set
The system is evaluated against three core golden scenarios reflecting edge cases and bilingual operational realities:

| ID | Scenario | Input | Expected Output | Live Result (Gemini 3.8 Flash) | Tokens (In / Out) | Latency |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **G1** | Georgian: Pillows & Breakfast | *"გამარჯობა, ოთახში 204 ბალიშები გვჭირდება და საუზმე რომელ საათზეა?"* | Answers breakfast hours (07:00–10:30); dispatches normal housekeeping task for Room 204 within 30 min. | **PASS** | 463 / 145 | 5.35 s |
| **G2** | Policy Violation: Pool at 23:30 | *"Can I access the swimming pool now? Room 305."* | Notes pool closes at 22:00; flags Room 305 as checked-out; blocks staff task creation. | **PASS** | 466 / 89 | 6.22 s |
| **G3** | Missing Information: AC Broken | *"Our AC is blowing hot air, please fix it immediately."* | Refuses task creation due to missing room; requests room number and guest name; escalates to front desk. | **PASS** *(Recovered from initial API 500)* | 391 / 83 | 5.01 s |

### 4.2 Latency Benchmark & SLA Analysis
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
* **Luka Dumbadze (`dumbadze.luka24@gmail.com`):** System Architecture, LLM Gateway Integration, Evaluation Pipeline, and Context Pre-filter optimization.
* **Team Governance:** Code reviewed through PRs; releases gated on passing unit tests and golden benchmarks.

### 6.2 Key Operator Decisions & Trade-Offs
1. **Domain Realignment (Boutique Hotel vs. Campus Dorms):** The team aligned the system strictly around boutique hospitality in Georgia, updating specifications rather than forcing mismatched course templates.
2. **Rejection of Model Autonomy for Task Escalation:** An early agent critique suggested having the LLM dynamically decide task priority. This was deliberately **rejected**: safety-critical priorities (water leaks, door locks, AC outages) are enforced deterministically in Python.
3. **OpenAI Endpoint Portability:** Standardizing on Google AI Studio's `/v1beta/openai/` endpoint enables zero-rewrite migration between Gemini and OpenRouter frontier models.