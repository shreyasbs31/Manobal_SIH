from __future__ import annotations

from typing import Any, Literal

ToolName = Literal[
    "record_checkin",
    "suggest_toolkit_item",
    "offer_human_contact",
    "open_leave_planner",
    "open_safety_plan",
]

ALLOWED_TOOLS: tuple[ToolName, ...] = (
    "record_checkin",
    "suggest_toolkit_item",
    "offer_human_contact",
    "open_leave_planner",
    "open_safety_plan",
)

BLOCKED_TOOLS = frozenset({"open_case", "write_assessment", "set_tier"})


def dispatch_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name in BLOCKED_TOOLS:
        raise PermissionError("tools cannot write assessments or cases")
    if name not in ALLOWED_TOOLS:
        raise KeyError(name)
    return {"tool": name, "arguments": arguments, "ok": True}
