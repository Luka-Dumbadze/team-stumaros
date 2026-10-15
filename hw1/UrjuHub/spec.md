# Spec v0 - Stumaros

## Problem
Boutique hotels and resorts are overwhelmed by fragmented guest inquiries scattered across WhatsApp, OTAs, and social media channels, leading to slow response times and missed requests. Staff waste hours manually juggling these communication silos instead of focusing on direct guest hospitality and operational execution.

## Users
Front-desk managers, concierge staff, and operations teams at independent boutique hotels and resorts who manage high volumes of multi-channel guest communication and struggle to keep guest profiles and operational tasks synchronized.

## Success criteria
1. The AI assistant successfully resolves or routes incoming guest inquiries from WhatsApp, OTAs, and social channels in under 5 seconds.
2. The cost per automated interaction stays under $0.005 on the default model.
3. In baseline testing, at least 9 out of 10 golden test questions pass successfully.

## Core feature (Weeks 2 to 4 scope)
An AI-powered messaging router that ingests fragmented guest inquiries from a mock multi-channel stream (WhatsApp/social logs), categorizes them into stay-lifecycle chapters, and outputs an automated response alongside a structured operational task for hotel staff.

## Context list
- `inquiries.json` (guest ID, channel, message text, timestamp, current stay chapter) – located in the repo.
- `hotel_operations.json` (staff roster, room status, service catalog) – located in the repo.
- Current server timestamp – computed server-side.
- Nothing else. Historical guest preferences and advanced analytics come in later versions.

## Acceptance criteria
1. A guest inquiry regarding room service sent via WhatsApp returns a correctly categorized response and assigns the task to the F&B staff list.
2. An ambiguous or unrelated message from an unknown channel triggers a polite refusal message instead of inventing hotel data.
3. Every model execution logs prompt tokens, completion tokens, and latency to a local usage file.

## Napkin math
500 req/day × (4,500 input tokens × $0.75 + 150 output tokens × $3.75) / 1,000,000 × 30 days = $55.69 /month on gemini-3.8-flash.

## Risks and safety
- **Risk 1:** Outdated operational data causes the AI to assign tasks to off-duty staff. -> Mitigation: Fetch real-time status from `hotel_operations.json` on every request.
- **Risk 2:** High traffic volume causes latency spikes during check-in windows. -> Mitigation: Implement response caching for frequently asked hotel FAQs.
- **Misuse:** A user attempts to use the Stumaros chatbot for non-hotel or general AI chat queries. -> Mitigation: Enforce system prompt boundaries that restrict responses strictly to hospitality and stay operations.

## Out of scope (for now)
Real-time two-way WhatsApp Business API integration (mocked locally for v0), automated payment processing, physical room key generation, and multi-language translation for non-English inquiries (planned for W6+).
