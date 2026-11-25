# 0005 · The caller's room is never a tool argument

**Date:** Week 5 (Lab 5) · **Decided by:** Luka Dumbadze (team tool and owners table, 2026-11-24); confirmed in PR review

**Context.** The HW2 tools act on or read one guest's stay: `create_service_task`, `my_open_tasks`, `request_late_checkout`. The easy contract is `create_service_task(item, room)`, with the model filling in the room from the conversation. Anything the model can set, a prompt can set: "send towels to room 305" from a guest in 204, or an instruction pasted into a message. We also must not tell a visitor which rooms are occupied.

**Decision.**
- No contract has a room, guest, user or account field.
- The caller's room comes from the session: the `X-Room` header on `POST /act` today (real sign-in in Week 12), or `STUMAROS_ROOM` for the MCP server.
- In both cases `tools.verified_room()` accepts it only if it is an active stay today (decision 0001's rule). Otherwise the caller is a visitor.
- Tools that need the room (`needs_room=True`) are offered only to a verified room and receive it from the server.
- No occupancy lookup tool exists.

**Alternatives.**
- A room argument plus a check that it matches the session: two sources of truth, and a mismatch path to get wrong.
- Detecting "another room" in the text: the model and the prompt have endless phrasings.
- A `check_room` tool for visitors: leaks who is staying where.

**Consequences.**
- "Send towels to room 305" from 204 cannot create a task for 305. The model has no field to put 305 in. This is shown by `tests/test_act.py::test_model_cannot_choose_the_room`, `test_room_tools_get_the_room_from_the_server_not_the_model` and golden `team:a1`.
- Visitors are offered read-only, non-private tools only.
- `logs/tools.jsonl` stores a hash of the room, not the room.
