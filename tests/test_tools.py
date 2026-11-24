"""The tools, the registry and the caller's room."""
import pytest

from src import tools
from src.contracts import LookupPolicy


def test_lookup_returns_the_guide_text_unchanged():
    out = tools.lookup_policy(LookupPolicy(section="checkout"))
    assert out.section == "checkout" and "check-out is by 11:00" in out.text


def test_missing_section_is_an_expected_failure_that_says_what_to_do(monkeypatch):
    monkeypatch.setattr(tools.prefilter, "load_guide", lambda: [])
    with pytest.raises(tools.ToolFailure, match="front desk"):
        tools.lookup_policy(LookupPolicy(section="pool"))


@pytest.mark.parametrize("claimed, expected", [
    ("204", "204"), (" 204 ", "204"),          # checked in, inside the stay
    ("305", None), ("112", None), ("501", None),  # checked out, reserved, stay over
    ("999", None), ("", None), (None, None), ("204' OR 1=1 --", None),
])
def test_only_an_active_stay_counts_as_a_caller(claimed, expected):
    assert tools.verified_room(claimed) == expected


def test_room_is_logged_as_a_hash():
    assert tools.room_key("204") != "204" and len(tools.room_key("204")) == 12


def test_no_tool_deletes_anything():
    assert not any(w in name for name in tools.TOOLS for w in ("delete", "cancel", "remove", "update"))


def test_visitor_is_offered_only_tools_that_need_no_room():
    assert set(tools.tools_for(None)) == {n for n, t in tools.TOOLS.items() if not t.needs_room}
    assert "lookup_policy" in tools.tools_for(None)


def test_no_occupancy_lookup_exists():
    # Telling a visitor which rooms are occupied leaks guest data (docs/tool-contracts.md).
    assert not any(w in name for name in tools.TOOLS for w in ("check_room", "occupan", "guest"))


def test_schema_comes_from_the_contract():
    s = tools.TOOLS["lookup_policy"].schema()["function"]
    assert s["parameters"]["additionalProperties"] is False
    assert "pool" in s["parameters"]["properties"]["section"]["enum"]
    assert s["description"].startswith("Read one section of the hotel guide")
