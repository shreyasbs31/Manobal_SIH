"""Personnel-facing meanings for contributing categories. No scores, no WSI."""

from __future__ import annotations

# FR-3.7 / UC-23. These sentences name the domain only. They must not contain a
# number, a threshold, or a comparison to anyone else.
_MEANING: dict[str, str] = {
    "workload_and_duty": (
        "Your duty hours or consecutive duty days moved away from your usual pattern."
    ),
    "leave_and_time_off": (
        "Leave that was asked for or refused looked different from your usual pattern."
    ),
    "work_pattern_changes": "Your posting or work pattern changed relative to your own baseline.",
    "sleep_and_recovery": "Sleep or recovery readings moved away from your usual pattern.",
    "self_reported_wellbeing": (
        "Your own check-ins or questionnaires moved away from your usual pattern."
    ),
    "voice_check_in": "Voice measurements taken on your device moved away from your usual pattern.",
    "app_engagement": "How often you used the app moved away from your usual pattern.",
    "immediate_safety_indicator": (
        "A safety signal was raised. This is not a diagnosis."
    ),
}

_FALLBACK = "This area moved away from your usual pattern. No number is stored."


def why_flagged(categories: list[str] | tuple[str, ...]) -> list[dict[str, str]]:
    """Return category meanings. Empty when there is nothing to explain."""
    return [
        {"category": name, "meaning": _MEANING.get(name, _FALLBACK)}
        for name in categories
        if name
    ]
