"""Narrative welfare notes. No WSI, no thresholds, no comparison to a unit."""

from __future__ import annotations

from typing import Any

from manobal_core.scoring.explain import why_flagged

_FIELD_LABEL = {
    "mood": "Mood",
    "sleep_quality": "Sleep",
    "stress": "Stress",
    "fatigue": "Fatigue",
    "connection": "Connection",
}

# Lower is worse for these Likert items.
_LOWER_IS_WORSE = frozenset({"mood", "sleep_quality", "connection"})

_DIRECTION_COPY: dict[tuple[str, str], str] = {
    ("mood", "falling"): "Mood has been lower than earlier in this stretch.",
    ("mood", "rising"): "Mood has been lifting compared with earlier this stretch.",
    ("mood", "steady"): "Mood has been steady across recent check-ins.",
    ("sleep_quality", "falling"): "Sleep has been thinner than earlier in this stretch.",
    ("sleep_quality", "rising"): "Sleep has been recovering compared with earlier this stretch.",
    ("sleep_quality", "steady"): "Sleep has been steady across recent check-ins.",
    ("stress", "rising"): "Stress has been higher than earlier in this stretch.",
    ("stress", "falling"): "Stress has been easing compared with earlier this stretch.",
    ("stress", "steady"): "Stress has been steady across recent check-ins.",
    ("fatigue", "rising"): "Fatigue has been heavier than earlier in this stretch.",
    ("fatigue", "falling"): "Fatigue has been easing compared with earlier this stretch.",
    ("fatigue", "steady"): "Fatigue has been steady across recent check-ins.",
    ("connection", "falling"): "Connection has felt more distant than earlier in this stretch.",
    ("connection", "rising"): "Connection has felt closer compared with earlier this stretch.",
    ("connection", "steady"): "Connection has been steady across recent check-ins.",
}

_OPENERS: dict[str, str] = {
    "sleep_and_recovery": "Ask about sleep over the last week, not last night.",
    "workload_and_duty": "Ask which days ran long, not how they 'feel overall'.",
    "self_reported_wellbeing": "Start from what they wrote in the check-in, not from a score.",
    "leave_and_time_off": "Ask whether leave that was needed actually happened.",
    "immediate_safety_indicator": "Make contact now. Do not wait for the next parade.",
    "voice_check_in": "Keep the conversation about rest and load. Do not mention voice features.",
    "app_engagement": "Ask what got in the way of using the private tools.",
    "work_pattern_changes": "Ask what changed in the posting, not how they compare to the unit.",
}

SETTLED_MESSAGE = (
    "This has been a settled, thin stretch. A picture based on change will not "
    "flag it. Talk, a questionnaire, or asking for help is how this reaches welfare."
)

ENGINE_NOTE = (
    "This picture names change from your own pattern, not how distressed you are. "
    "A settled, thin stretch will not raise a flag on its own."
)


def clean_series(values: list[int | None] | tuple[int | None, ...]) -> list[int]:
    return [value for value in values if isinstance(value, int) and 1 <= value <= 5]


def direction(chrono: list[int]) -> str:
    """Oldest-first Likert series → rising / falling / steady / unknown."""
    if len(chrono) < 3:
        return "unknown"
    first = chrono[:3]
    last = chrono[-3:]
    delta = (sum(last) / 3) - (sum(first) / 3)
    if delta >= 0.7:
        return "rising"
    if delta <= -0.7:
        return "falling"
    return "steady"


def settled_low(chrono: list[int], *, ceiling: int = 2, days: int = 5) -> bool:
    """True when a stretch is both low and no longer moving. ADR 0003."""
    if len(chrono) < days:
        return False
    recent = chrono[-days:]
    return all(value <= ceiling for value in recent) and (max(recent) - min(recent) <= 1)


def checkin_streak(dates: list[str]) -> int:
    """Consecutive calendar days ending at the most recent observation."""
    if not dates:
        return 0
    ordered = sorted({day for day in dates if day})
    streak = 1
    for index in range(len(ordered) - 1, 0, -1):
        newer = _ordinal(ordered[index])
        older = _ordinal(ordered[index - 1])
        if newer is None or older is None or newer - older != 1:
            break
        streak += 1
    return streak


def personnel_briefing(
    checkins: list[dict[str, Any]],
    *,
    tier: str | None = None,
    categories: list[str] | None = None,
    offer_checkin: bool = False,
) -> dict[str, Any]:
    """Personnel-facing notes from their own check-ins. Likert values stay private."""
    chrono = sorted(checkins, key=lambda row: str(row.get("observed_on") or ""))
    notes: list[dict[str, str]] = []
    sleep_settled = False
    for field in ("sleep_quality", "mood", "stress", "fatigue", "connection"):
        series = clean_series([_as_int(row.get(field)) for row in chrono])
        trend = direction(series)
        text = _DIRECTION_COPY.get((field, trend))
        if not text:
            continue
        note = {"field": field, "direction": trend, "text": text}
        if field == "sleep_quality" and settled_low(series):
            sleep_settled = True
            note["text"] = (
                "Sleep has been in a settled, thin stretch - not a sudden dip."
            )
        notes.append(note)
    lede = notes[0]["text"] if notes else "Save today's check-in to start a private picture."
    why = why_flagged(categories or [])
    actions = _personnel_actions(tier, sleep_settled, offer_checkin)
    dates = [str(row.get("observed_on") or "") for row in chrono]
    return {
        "lede": lede,
        "notes": notes,
        "why": why,
        "settled_low": sleep_settled,
        "settled_message": SETTLED_MESSAGE if sleep_settled else "",
        "engine_note": ENGINE_NOTE,
        "streak": checkin_streak(dates),
        "next": actions,
    }


def officer_briefing(
    *,
    tier: str,
    categories: list[str],
    recommendations: list[dict[str, Any]] | None = None,
    sleep_series: list[int] | None = None,
) -> dict[str, Any]:
    """Officer-facing briefing. Category names and suggested questions. No Likert."""
    names = [name for name in categories if name]
    why = why_flagged(names)
    headline = _officer_headline(tier, names)
    openers = [_OPENERS[name] for name in names if name in _OPENERS]
    if not openers:
        openers = ["Ask what changed this week. Do not mention a score."]
    settled = settled_low(sleep_series or [])
    recs = recommendations or []
    return {
        "headline": headline,
        "why": why,
        "openers": openers,
        "settled_note": SETTLED_MESSAGE if settled else "",
        "next_step": recs[0]["rationale"] if recs else "",
    }


def officer_headline(tier: str, categories: list[str]) -> str:
    return _officer_headline(tier, [name for name in categories if name])


def unit_briefing(
    *,
    suppressed: bool,
    elevated_band: str = "",
    dominant_category: str = "",
    trend_direction: str = "",
) -> str:
    if suppressed:
        return (
            "This figure is withheld. The unit is too small or too unstable to "
            "publish a band without identifying people."
        )
    category = dominant_category.replace("_", " ") if dominant_category else "no single category"
    trend = {
        "up": "The elevated band has moved up since the last window.",
        "down": "The elevated band has moved down since the last window.",
        "stable": "The elevated band is unchanged since the last window.",
    }.get(trend_direction, "There is not yet a published trend.")
    band = elevated_band or "unpublished"
    return (
        f"The unit elevated band is {band}. The named load is {category}. {trend} "
        "No person, token, or count below the k-threshold appears here."
    )


def _officer_headline(tier: str, names: list[str]) -> str:
    if tier == "T4":
        return "Urgent support. Make contact now."
    if not names:
        return "A welfare conversation is due. Categories are not yet named."
    lead = names[0].replace("_", " ")
    if len(names) == 1:
        return f"{lead} moved away from this person's usual pattern."
    return f"{lead} and {len(names) - 1} more area(s) moved away from their usual pattern."


def _personnel_actions(
    tier: str | None, settled_low_sleep: bool, offer_checkin: bool
) -> list[dict[str, str]]:
    actions = [
        {
            "id": "checkin",
            "title": "Check in today",
            "detail": "Five 1-5 items. This is not a diagnosis.",
            "href": "checkin",
        },
        {
            "id": "talk",
            "title": "Talk",
            "detail": "Hold to speak. Crisis words stay on this device.",
            "href": "talk",
        },
    ]
    if offer_checkin:
        actions.insert(
            0,
            {
                "id": "incident",
                "title": "Optional extra check-in",
                "detail": "Offered after a unit incident. Not itself a flag.",
                "href": "checkin",
            },
        )
    if settled_low_sleep or tier in {"T2", "T3", "T4"}:
        actions.append(
            {
                "id": "help",
                "title": "Need help now",
                "detail": "Helplines without a record, or SOS to notify an officer.",
                "href": "help",
            },
        )
    return actions


def _as_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _ordinal(day: str) -> int | None:
    parts = day.split("-")
    if len(parts) != 3:
        return None
    try:
        year, month, date = int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        return None
    from datetime import date as date_cls

    return date_cls(year, month, date).toordinal()
