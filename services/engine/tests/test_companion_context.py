from __future__ import annotations

import pytest
from app.ai.pipeline import run_pipeline
from app.ai.remembers import RememberItem, add_item, context_for, set_opt_in
from app.ai.tools import ALLOWED_TOOLS, dispatch_tool


def test_tools_are_the_five_named_and_cannot_open_cases() -> None:
    assert ALLOWED_TOOLS == (
        "record_checkin",
        "suggest_toolkit_item",
        "offer_human_contact",
        "open_leave_planner",
        "open_safety_plan",
    )
    assert dispatch_tool("record_checkin", {"mood": 2})["ok"] is True
    with pytest.raises(PermissionError):
        dispatch_tool("open_case", {"case_id": "MB-4091"})
    with pytest.raises(PermissionError):
        dispatch_tool("write_assessment", {})


def test_remembers_omitted_when_opt_in_off() -> None:
    token = "st_364aifljnxnxpqzk"
    set_opt_in(token, False)
    with pytest.raises(PermissionError):
        add_item(token, RememberItem(group="helps", text="walking after duty"))
    assert context_for(token) == []
    set_opt_in(token, True)
    add_item(token, RememberItem(group="helps", text="walking after duty"))
    assert "walking after duty" in context_for(token)[0]


async def test_hindi_companion_uses_aap() -> None:
    result = await run_pipeline("Raat ki duty ke baad neend kam thi.", lang="hi", mode="checkin")
    assert result.model_reached is True
    assert result.reply
    assert "aap" in result.reply.lower()
