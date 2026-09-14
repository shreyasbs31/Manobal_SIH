"""Narrative notes name change, not a welfare score."""

from __future__ import annotations

from manobal_core.insights.briefing import (
    ENGINE_NOTE,
    SETTLED_MESSAGE,
    checkin_streak,
    direction,
    officer_briefing,
    personnel_briefing,
    settled_low,
    unit_briefing,
)


def test_direction_reads_oldest_to_newest() -> None:
    assert direction([4, 4, 4, 2, 2, 1]) == "falling"
    assert direction([1, 2, 2, 4, 4, 5]) == "rising"
    assert direction([3, 3, 3, 3, 3]) == "steady"
    assert direction([4, 3]) == "unknown"


def test_settled_low_is_the_plateau_the_engine_cannot_see() -> None:
    assert settled_low([2, 2, 1, 2, 1]) is True
    assert settled_low([4, 4, 4, 4, 4]) is False
    assert settled_low([5, 4, 2, 1, 1]) is False


def _checkin(
    day: str, sleep: int, mood: int, stress: int, fatigue: int, connection: int
) -> dict[str, object]:
    return {
        "observed_on": day,
        "sleep_quality": sleep,
        "mood": mood,
        "stress": stress,
        "fatigue": fatigue,
        "connection": connection,
    }


def test_personnel_briefing_never_mentions_a_score() -> None:
    rows = [
        _checkin("2026-09-08", 4, 4, 2, 2, 4),
        _checkin("2026-09-09", 3, 3, 3, 3, 3),
        _checkin("2026-09-10", 2, 3, 3, 3, 3),
        _checkin("2026-09-11", 2, 2, 4, 4, 2),
        _checkin("2026-09-12", 1, 2, 4, 4, 2),
    ]
    body = personnel_briefing(rows, tier="T2", categories=["sleep_and_recovery"])
    blob = str(body).lower()
    assert "wsi" not in blob
    assert "score" not in blob
    assert body["notes"]
    assert body["engine_note"] == ENGINE_NOTE
    assert "Sleep" in body["lede"] or "sleep" in body["lede"].lower()
    assert any(item["id"] == "talk" for item in body["next"])
    assert checkin_streak([row["observed_on"] for row in rows]) == 5


def test_settled_sleep_points_at_the_non_scoring_path() -> None:
    rows = [_checkin(f"2026-09-{day:02d}", 2, 3, 3, 3, 3) for day in range(8, 14)]
    body = personnel_briefing(rows, tier="T0")
    assert body["settled_low"] is True
    assert body["settled_message"] == SETTLED_MESSAGE
    assert any(item["id"] == "help" for item in body["next"])


def test_officer_briefing_uses_questions_not_numbers() -> None:
    body = officer_briefing(
        tier="T3",
        categories=["sleep_and_recovery", "workload_and_duty"],
        recommendations=[{"rationale": "Offer a sleep-hygiene conversation."}],
    )
    blob = str(body).lower()
    assert "wsi" not in blob
    assert "tok_" not in blob
    assert "Ask about sleep" in body["openers"][0]
    assert "sleep and recovery" in body["headline"]


def test_unit_briefing_names_a_band_not_a_person() -> None:
    text = unit_briefing(
        suppressed=False,
        elevated_band="1-4",
        dominant_category="sleep_and_recovery",
        trend_direction="up",
    )
    assert "1-4" in text
    assert "tok_" not in text
    assert "sleep and recovery" in text
    withheld = unit_briefing(suppressed=True)
    assert "withheld" in withheld.lower()
