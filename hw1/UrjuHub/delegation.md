# Delegation Log - Stumaros

## Overview
This log records our team's experience delegating feature implementation and spec critique tasks to our AI coding assistant (Gemini/Cursor) while building Stumaros, following the course guidelines for honest tool usage.

## What We Delegated
1. **Spec Critique:** We asked our AI agent to review our initial draft of `spec.md` and `AGENTS.md` to identify ambiguities and evaluate whether our success criteria were genuinely measurable.
2. **Initial Code Scaffold:** We delegated the creation of the core routing script in `src/` to parse incoming JSON messages and match them against mock hotel operation rules.

## What Came Back Wrong / Flawed
* **Over-engineered Architecture on First Pass:** When generating the initial Python code for message routing, the AI attempted to introduce a full asynchronous event-driven message broker and external database ORM. This completely violated our "Context as Budget" pattern and added unnecessary complexity for a simple Week 2-4 scope.
* **Vague Success Metrics:** During the spec review, the AI's initial critique suggested vague metrics like "ensure fast and pleasant guest replies," which failed our course rule that success criteria must have hard numbers.

## How We Caught and Fixed It
* **Refining the Code:** We rejected the heavy database ORM and message broker. We prompted the AI instead: *"Simplify this to a lightweight FastAPI endpoint reading directly from local JSON files (`inquiries.json` and `hotel_operations.json`) without external dependencies."* We manually reviewed the code diff to ensure it matched our strict scope.
* **Fixing the Spec:** We overrode the AI's vague phrasing and manually locked our success criteria down to strict, measurable boundaries (e.g., *under 5 seconds response time* and *cost under $0.005 per interaction*). 

## Takeaway
Directing an AI agent requires strict constraints. Letting the AI steer architecture leads to bloat; using the AI strictly for code scaffolding while maintaining human oversight of scope and context keeps the project lean and compliant with course standards.gi
