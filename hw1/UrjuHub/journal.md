# Pattern Journal - Stumaros

**W1   Context as Budget**  
Applied in our spec's context list for Stumaros: we intentionally cut historical guest preference analytics and full CRM profiles from version zero, keeping only `inquiries.json`, `hotel_operations.json`, and the server timestamp. I delegated a first draft of the context list to Cursor; it initially added "full past guest chat history across all stays," which we rejected because our core feature scope only handles active stay-lifecycle chapters. Verified by re-reading each acceptance criterion against the trimmed context list.

**W2   Spec Before Code**  
Wrote spec v0 for Stumaros before writing any implementation code. Delegated a critique of our spec to Claude Code; it flagged that our success criterion regarding "fast routing" was unmeasurable, so we rewrote it to specify "under 5 seconds response time." Verified the rewrite by checking that every success criterion now contains a concrete metric (time, cost, or test pass rate).

**W3   Uncertainty-Aware UX**  
Applied in our acceptance criteria for handling unrecognized or ambiguous guest messages. Delegated the edge-case handling logic to our AI assistant to ensure the system doesn't hallucinate hotel data when an incoming message falls outside hospitality operations. Verified by running Test 2 in our golden questions, confirming it triggers a polite refusal boundary instead of generating false operational tasks.

**W4   Grounded Generation**  
Applied when connecting our FastAPI backend to local JSON data instead of allowing open-ended model hallucinations. Delegated the prompt structure to enforce strict retrieval grounding against `hotel_operations.json` for staff rosters and room statuses. Verified by tracking token usage logs in `logs/usage.jsonl` and checking that model responses correctly reflect only the data present in the local repo files.
