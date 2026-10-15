# Golden Test Questions - Stumaros

## Test 1: Ingestion and Task Dispatch for Room Service
* **Input:** A guest inquiry message sent via WhatsApp: "Can someone bring extra towels and a bottle of sparkling water to Room 304 immediately?"
* **Expected Behavior:** The AI categorizes the message into the active stay-lifecycle chapter, generates a polite guest-facing confirmation response, and routes a structured task to the housekeeping/concierge staff roster within 3 seconds.
* **Actual Result:** Successfully categorized as an immediate service request, generated a confirmation text, and outputted a task object assigned to room 304 with correct metadata.
* **Pass / Fail:** Pass

## Test 2: Handling Ambiguous or Unrelated Queries (Refusal Boundary)
* **Input:** A message from an unknown channel trying to use the system for general advice: "Can you write me a python script to calculate my crypto portfolio profits?"
* **Expected Behavior:** The AI recognizes that the request falls completely outside hotel operations and stay-lifecycle chapters, triggering a polite refusal boundary instead of attempting to answer or inventing data.
* **Actual Result:** Returned a polite refusal statement restricting responses strictly to hospitality and stay operations, logging no operational tasks.
* **Pass / Fail:** Pass

## Test 3: System Logging and Usage Accounting
* **Input:** A standard inquiry regarding hotel check-out time: "What time is checkout and can I get a late checkout?"
* **Expected Behavior:** The model successfully answers the query based on `hotel_operations.json` data and appends a usage log recording prompt tokens, completion tokens, and latency to the local usage tracker.
* **Actual Result:** Answered accurately with checkout rules, and successfully appended a new line of telemetry data to `logs/usage.jsonl`.
* **Pass / Fail:** Pass
