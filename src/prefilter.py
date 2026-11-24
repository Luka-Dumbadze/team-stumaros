"""Pattern 01 · Context as Budget: deterministic pre-filtering before anything reaches the model."""
from __future__ import annotations

import json
import math
import re
from datetime import date
from pathlib import Path

# Root data/ (read-only, see AGENTS.md). Promoted from hw1/Luka-Dumbadze/src/data/, valid stays on 2026-10-15.
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MAX_SECTIONS = 3
MAX_MESSAGE_CHARS = 1000

# "room 204", "rm 204", "#204", "ოთახი 204-ში", "ნომერი 204".
_ROOM_RE = re.compile(r"(?:\broom|\brm\.?|#|ოთახ\w*|ნომერ\w*)\s*(?:no\.?|number|#)?\s*(\d{3,4})\b", re.IGNORECASE)
_GEORGIAN_RE = re.compile(r"[Ⴀ-ჿᲐ-Ჿ]")


def load_guide(path: Path = DATA_DIR / "hotel_guide.json") -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["sections"]


def load_rooms(path: Path = DATA_DIR / "active_rooms.json") -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_rooms(message: str) -> list[str]:
    """All distinct room numbers mentioned with a room keyword, in order of appearance."""
    seen: list[str] = []
    for m in _ROOM_RE.finditer(message):
        if m.group(1) not in seen:
            seen.append(m.group(1))
    return seen


def resolve_room(payload_room: str | None, message: str) -> tuple[str | None, str | None]:
    """Pick the room to validate. Returns (room, problem). Conflicting sources -> no room."""
    mentioned = extract_rooms(message)
    payload_room = payload_room.strip() if payload_room else None
    candidates = ([payload_room] if payload_room else []) + [r for r in mentioned if r != payload_room]
    if len(candidates) > 1:
        return None, "conflicting_rooms"
    return (candidates[0], None) if candidates else (None, None)


def validate_room(room: str | None, rooms: list[dict], today: date) -> tuple[dict | None, str]:
    """Root AGENTS.md rule: valid only if status == checked_in and check_in <= today <= check_out."""
    if room is None:
        return None, "missing"
    record = next((r for r in rooms if r["room"] == room), None)
    if record is None:
        return None, "unknown"
    if record["status"] != "checked_in":
        return record, "not_checked_in"
    if not (date.fromisoformat(record["check_in"]) <= today <= date.fromisoformat(record["check_out"])):
        return record, "outside_stay_dates"
    return record, "valid"


def _keyword_hits(keyword: str, text: str) -> int:
    if keyword.isascii():
        pattern = rf"\b{re.escape(keyword)}(?:s|es|ing|ed)?\b"
        return len(re.findall(pattern, text, re.IGNORECASE))
    # Georgian stems match at word start only: suffixes like -ში/-ები are fine, but a plain substring
    # match made "აუზ" (pool) fire inside "საუზმე" (breakfast). Found by golden case 1.
    return len(re.findall(rf"\b{re.escape(keyword)}", text))


def select_sections(message: str, sections: list[dict], limit: int = MAX_SECTIONS) -> list[dict]:
    """Keep only sections whose keywords occur in the message; most hits first, guide order on ties."""
    scored = []
    for index, section in enumerate(sections):
        hits = sum(_keyword_hits(k, message) for k in section["keywords"])
        if hits:
            scored.append((-hits, index, section))
    scored.sort(key=lambda s: (s[0], s[1]))
    return [s[2] for s in scored[:limit]]


def estimate_tokens(text: str) -> int:
    """Rough estimate: ~4 chars/token for Latin text; Georgian script costs ~3x more per char."""
    georgian = len(_GEORGIAN_RE.findall(text))
    other = len(text) - georgian
    return math.ceil(other / 4 + georgian * 3 / 4)


def truncate_message(message: str) -> str:
    return message[:MAX_MESSAGE_CHARS]
