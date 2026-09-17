from __future__ import annotations

import pytest
from app.ai.gateway import local_brief_verify, run, strip_dashes
from app.ai.prompts import TASK_FILES, load_prompt
from app.privacy.rights import KILLSWITCHES, set_killswitch


def test_every_task_prompt_is_signed() -> None:
    for task in TASK_FILES:
        prompt = load_prompt(task)
        assert prompt.signature
        assert prompt.text


def test_dashes_become_commas() -> None:
    raw = "Rest first\u2014then sleep\u2013then food."
    assert "\u2014" not in strip_dashes(raw)
    assert "\u2013" not in strip_dashes(raw)
    assert strip_dashes(raw) == "Rest first, then sleep, then food."


def test_brief_verify_rejects_unsupported_sentence() -> None:
    fields = {"tier": "T3", "domain": "workload", "onset": "20 days", "lever": "REST_48H"}
    ok = local_brief_verify("Tier is T3 [tier]. Domain is workload [domain].", fields)
    assert ok["pass"] is True
    bad = local_brief_verify("This unit will collapse next week.", fields)
    assert bad["pass"] is False
    assert bad["unsupported"]


@pytest.mark.asyncio
async def test_killswitches_skip_agent_copilot_and_briefs() -> None:
    set_killswitch("agent", True, "wdec")
    set_killswitch("copilot", True, "wdec")
    set_killswitch("briefs", True, "wdec")
    try:
        companion = await run("companion_turn", {"text": "hello"}, "en")
        copilot = await run("command_copilot", {"question": "What is the T2 share?"}, "en")
        brief = await run("case_brief", {"fields": {"tier": "T3"}}, "en")
        assert companion.skipped and companion.provider == "killswitch"
        assert copilot.skipped
        assert brief.skipped
    finally:
        set_killswitch("agent", False, "wdec")
        set_killswitch("copilot", False, "wdec")
        set_killswitch("briefs", False, "wdec")
        for name in ("agent", "copilot", "briefs"):
            KILLSWITCHES[name] = False


@pytest.mark.asyncio
async def test_case_brief_enforces_brief_verify() -> None:
    result = await run(
        "case_brief",
        {
            "fields": {
                "tier": "T3",
                "domain": "workload",
                "onset": "about 20 days",
                "lever": "REST_48H",
            }
        },
        "en",
    )
    assert result.verified is True
    assert "REST_48H" in result.text
