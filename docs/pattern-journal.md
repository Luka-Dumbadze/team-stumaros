# Pattern Journal · Luka Dumbadze

*One entry per teaching week, 2 to 3 sentences. Graded inside HW1 (W1-4), HW2 (W5-7), and the Repository Review (W10-14). Honest beats polished.*

Format per entry:
**W# · [Pattern name]** · Where I applied it · What I delegated to AI · How I verified it

---

**W1 · Context as Budget** · Applied to the context list and session memory constraints in `docs/spec.md` and `AGENTS.md`. I delegated an initial context list to the model; it proposed retaining full guest stay history and live PMS sync, which I cut to keep token costs within our $5.30/month napkin estimate. Verified by enforcing a strict 4-turn (8-message) memory cap and confirming that only `hotel_guide.json` and `active_rooms.json` enter the prompt.

**W2 · Spec Before Code** · Wrote `docs/spec.md` and `AGENTS.md` contracts before writing a single line of backend code. Delegated a critique of our success criteria to Claude Code; it caught that auditing our "≤3 model calls" rule was impossible without adding `request_id` to logs, but also attempted scope creep by proposing an LLM-as-a-judge system. Verified by rejecting the LLM judge in favor of deterministic regex fixtures, adding `request_id` across both documents, and ensuring all 24 golden scenarios have explicit distributions.

**W3 · Uncertainty-Aware UX** ·

**W4 · Grounded Generation** ·