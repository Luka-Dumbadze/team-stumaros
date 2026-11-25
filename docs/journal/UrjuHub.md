# Pattern Journal · Giorgi Urjumelashvili (@UrjuHub)

Project: **Stumaros** (AI-native Guest OS for boutique hotels and resorts)  
Team: `team-stumaros`

## Week 1 · Context as Budget
W1 · Context as Budget · Applied to guest stay context, property rules, and WhatsApp/OTA/social inquiry history passed into Stumaros assistant prompts so only active stay data and relevant hotel policies are included. Delegated initial prompt-trimming ideas and token budget estimates to AI, then cut verbose conversation history and unrelated property sections to keep per-request token usage low and predictable. Verified by inspecting assembled prompt payloads on sample guest inquiries and checking token counts/costs against our budget assumptions.

## Week 2 · Spec Before Code
W2 · Spec Before Code · Defined Stumaros inquiry handling contracts, stay-lifecycle chapter structure, and fallback/escalation behavior in docs before writing application logic. Delegated edge-case brainstorming and contract draft checks to AI, while explicitly trimming over-engineered extras that did not serve core guest-to-staff workflows. Verified each workflow requirement against documented inputs, outputs, and error/clarification cases before implementing code.

## Week 3 · Uncertainty-Aware UX
W3 · Uncertainty-Aware UX · Applied to ambiguous or incomplete guest messages in Stumaros (such as missing room numbers, unclear dates, or mixed requests across channels) so the system asks a concise clarifying question or routes to staff instead of guessing. Delegated ambiguity scenarios and clarification wording drafts to AI, then refined them to keep guest replies polite, brief, and non-intrusive. Verified by testing ambiguous vs. complete guest inputs and confirming uncertain cases do not trigger wrong room or staff actions.

## Week 4 · Grounded Generation
W4 · Grounded Generation · Applied to policy, amenity, check-in/out, and stay-chapter responses in Stumaros so answers stay anchored to verified hotel documentation and actual guest stay records. Delegated test case generation for policy lookups and ungrounded/missing-policy queries to AI, then tightened guardrails so unknown details trigger handoff/clarification rather than fabricated answers. Verified responses against source policy/stay data on both normal and edge-case guest queries.
