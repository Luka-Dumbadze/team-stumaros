# Spec v0 · StumarOS

*One page. Rough is fine, empty is not. This grows into your Week 4 Design Review.*

## Problem
Front-desk staff at boutique hotels are overwhelmed by repetitive guest inquiries and service requests scattered across WhatsApp, causing delayed responses during peak check-in hours. Meanwhile, guests face long waits for basic hotel information and amenity requests, leading to frustration and negative online reviews.

## Users
Front-desk managers and solo shift receptionists at boutique hotels (15–60 rooms) who manage guest WhatsApp messages on a shared front-desk phone while checking in arrivals. Secondary: Hotel guests messaging for services before and during their stay.

## Success criteria
*Evaluated across 3 runs of a 24-scenario golden set in /evals using `gemini-3.8-flash` (Google AI Studio; `google/gemini-3.8-flash` via OpenRouter, decision 0003). Until the 24-scenario harness exists, the 5-question Week 4 set in `evals/golden.yaml` stands in (DESIGN-REVIEW §4). Mix: ≥8 answerable policy questions, ≥4 unanswerable questions, ≥6 valid-room requests, ≥4 invalid-room requests (spanning unknown room, status != "checked_in", and date outside stay), and ≥2 composite requests. Each scenario fixture defines `expected_facts`, `forbidden_claims`, and `expected_tasks`. Each fact and claim is a list of case-insensitive regex variants (e.g. `10:30|10\.30|half past ten`); text checks pass on any variant match.*

1. **Latency & Execution Budget:**
   - Wall-clock end-to-end `POST /chat` latency: p95 ≤ 3,000 ms, max ≤ 6,000 ms per request (eval harness wall-clock, retries included).
   - 100% of requests make ≤ 3 model calls, audited by matching `request_id` in `logs/usage.jsonl`.

2. **Grounded Policy Retrieval:**
   - ≥ 90% of answerable questions contain all `expected_facts`.
   - 100% of unanswerable questions state info is unavailable and offer front-desk escalation (their `expected_facts` include standard refusal/escalation patterns, e.g. `front desk|reception` and `not available|unavailable`).
   - 0% forbidden claims (zero occurrences of any labeled `forbidden_claims` in the reply).

3. **Task Dispatch & Room Gate:**
   - Valid room requests: 100% emit tasks matching `expected_tasks` and pass `app/schemas.py` validation (`room`, `department`, `priority`, `task`) with 0 missing and 0 extra tasks.
   - Invalid or missing room: `tasks: []`, `room_validated: false`, and reply explicitly prompts for room verification.
   - Composite requests (valid room): reply satisfies policy retrieval facts AND tasks match `expected_tasks`.
   - Composite requests (invalid room): reply satisfies policy retrieval facts, prompts for room verification, and emits `tasks: []`.

## Core feature (Weeks 2 to 4 scope)
An AI-powered messaging agent that intercepts guest inquiries via a web-chat interface (simulating WhatsApp), answers operational questions grounded strictly in hotel property guides, and outputs structured action tickets (room number, department, task summary) whenever a guest requests room service, amenities, or maintenance.

## Context list
- `hotel_guide.json` (amenities, breakfast hours, pool/gym rules, parking, check-in/out policies, Wi-Fi info) · in the repo
- `active_rooms.json` (room numbers, guest first names, check-in/out dates for validation) · in-memory mock dataset
- Current timestamp & date · computed server-side
- Last 4 turns (up to 8 messages total) · session memory
- Nothing else. Live PMS bi-directional sync, payment processing, and external booking engine APIs come later.

## Acceptance criteria
1. "What time does breakfast end tomorrow?" returns the exact schedule from `hotel_guide.json` without inventing outside services.
2. "Can we get 2 extra pillows in room 204?" confirms the request to the guest and outputs a validated JSON task object (`{"room": "204", "department": "housekeeping", "priority": "normal", "task": "2 extra pillows"}`).
3. Any service request referencing a room that is unknown, not currently checked-in, or outside active stay dates politely asks the guest to verify their details instead of generating a task.

## Napkin math
Gemini 3.8 Flash at $0.75 / $3.75 per 1M tokens (in / out, promotional; verify before shipping). Medians come from the 9 successful HW1 live answers (463 in / 89 out). They are replaced by `logs/usage.jsonl` medians (`evals/usage_summary.py`) after the next live run. These match DESIGN-REVIEW §5.
- **Per request:** 463 × $0.75 + 89 × $3.75 per 1M ≈ **$0.00068**.
- **Monthly at 200 req/day:** 200 × 30 × $0.00068 ≈ **$4.09/month**.
- **Georgian:** 463 in / 145 out (output ≈ 1.6x English) ≈ $5.35/month for all-Georgian traffic.
- **Long-context alternative** (whole guide + room list, ≈ 2,560 in): ≈ $13.50/month, 3.3x the pre-filtered prompt.

## Risks and safety
- Hallucinated amenities (e.g., promising a non-existent airport shuttle) create angry front-desk confrontations. Mitigation: Strict prompt constraint to refuse unlisted services.
- Ambiguous service parsing creates duplicate or misrouted staff tasks. Mitigation: No extra confirmation turn; the server validates the room against `active_rooms.json` and checks required task fields (`room`, `department`, `priority`, `task`) against `app/schemas.py` before emitting task JSON.
- Misuse: Non-guests or pranksters submitting fake room service requests. Mitigation: Server-side code enforces validation against `active_rooms.json` (room status and stay dates) before task emission, rather than relying on prompt compliance alone.

## Out of scope (for now)
Direct PMS bi-directional sync (Opera/Cloudbeds), credit card payments, voice calls/telephony, automated door-lock integration, multilingual translation beyond English (planned W6+).