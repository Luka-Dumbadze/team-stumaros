# ADR 004 · No multimodal input in v1; explicit uncertainty-aware confidence policy

- **Status:** Proposed (drafted Week 4 with Claude Code; accepted when [@Luka-Dumbadze](https://github.com/Luka-Dumbadze) approves the PR that adds it)
- **Owner:** [@Luka-Dumbadze](https://github.com/Luka-Dumbadze)
- **Code it describes:** `src/pipeline.py` (`apply_guardrails`, `triage`), `src/prefilter.py`, `src/llm.py` (`SYSTEM_PROMPT`). **Evals:** `evals/golden.yaml` G2–G5

## Part A · Multimodal input (Week 3 pattern)

### Decision
**StumarOS v1 is text-only.** It accepts no images, voice notes or documents: no OCR of event posters, menus, room photos or guest ID/passport photos. If a guest sends a photo, the channel layer replies that images are not processed, and the front desk handles it.

### Why
1. **Latency budget is already blown.** Text-only p95 is **8.36 s** against a 2.5 s target (HW1 benchmark, `hw1/Luka-Dumbadze/golden.md`). An image adds upload time, vision tokens and longer generation, so the gap would grow.
2. **Cost and quota.** The free Gemini tier allows ~20 requests/day and failed calls count against it. Image tokens would push the ~$4–5/month napkin estimate up for no v1 use case.
3. **ID photos are high-risk personal data.** Passport/ID images would put names, dates of birth and document numbers into model prompts and `logs/`. That contradicts our rule that guest names never leave the server (`src/prefilter.py`, context budget). It also needs consent and retention rules we don't have.
4. **No grounding path.** Our grounding checks compare reply text against `hotel_guide.json`. Nothing deterministic can verify what a model "saw" in a photo.

### Revisit when
- p95 is within budget, and
- one concrete, staff-side use case is chosen. The likeliest is **check-in ID capture at the front desk**, run on the staff device (not in guest chat), with the extracted fields shown to staff for confirmation and the image never stored.

That would need its own ADR, golden cases and a privacy note.

## Part B · Confidence policy (Uncertainty-Aware UX)

### Decision
StumarOS **never guesses** when a fact it needs is missing, ambiguous or ungrounded. It routes to a clarification question or to the front desk instead.

"Confidence" is defined by **deterministic signals computed in code**, not by a model's self-reported confidence score. We don't ask the model for a confidence number, and we don't trust one.

| # | Signal (computed in code) | System behaviour | Enforced by | Covered by |
|---|---|---|---|---|
| 1 | Room **missing**, **unknown**, **not checked in**, **outside stay dates**, or payload and message name **different rooms** | Emit **no task**; `room_validated: false`; reply asks for **room number + booking name**. Policy questions in the same message are still answered. | Code: `room_gate` in `apply_guardrails` ([ADR 001](001-room-gate-in-code.md)) | Tests; golden G2, G3 |
| 2 | **No guide section** matches a question | Say the information is **not available** and **offer the front desk**. Never answer from general knowledge. | Prompt rule 1 + code appends the escalation if the reply lacks "front desk" | Tests; golden G4, G5 |
| 3 | Reply contains a **time/price/number** not in the sent policy text, the room or the guest message | **Replace the reply** with "I don't have that information; I can ask the front desk…" | Code: number check in `apply_guardrails` | `test_invented_time_replaces_reply` |
| 4 | Model output **unparseable or invalid** after 1 corrective retry, or **3 calls** exhausted (5xx/429/timeout) | Safe fallback reply, no tasks, `model_failed` event | Code: `call_with_budget` | Tests; the 2026-11-24 live run (all cases fell back) |
| 5 | Model **cites a section that was not sent** | Logged as a `grounding:` event | Code (log only, **reply not changed**) | — |
| 6 | Message intent is **unclear** | Ask what the guest needs; no task | Prompt only | — |
| 7 | **Non-numeric** unsupported claim ("yes, we have a free shuttle") | Should be refused per rule 2 | **Prompt only: known gap** | Golden G5 (live result in `evals/results/`) |

### Consequences and open gaps
- **Over-asking beats over-promising.** A guest who forgets the room number gets one extra round-trip. A wrong dispatch or an invented amenity costs staff time and trust.
- **Signal 7 is the weakest link.** The code cannot catch an invented amenity that contains no number. Golden case G5 tracks it. Candidate fixes: a claim-vs-section check, or a small allow-list of amenities the reply may affirm.
- **Signal 5 only logs.** Tighten it to replace the reply if live runs show unsent citations.
- **Signal 4's fallback over-promises.** It says the message was "flagged for the front desk", but nothing notifies staff yet. The Week 5+ `POST /chat` service must surface `model_failed` to a staff queue, or the wording must change.
- **Signal 2 has a pre-filter blind spot.** A question the guide *does* answer but that is misspelt (G4: "chek out") matches no section and is escalated instead of answered. That's safe, but unhelpful ([ADR 002](002-georgian-word-start-matching.md)).
