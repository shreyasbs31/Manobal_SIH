"""Load a person's own check-ins for briefing. Likert only, no WSI."""

from __future__ import annotations

from typing import Any

from manobal_core.apps.psystore.models import CheckinResponse


def checkin_rows(subject_token: str, *, limit: int = 14) -> list[dict[str, Any]]:
    rows = list(
        CheckinResponse.objects.filter(subject_token=subject_token).order_by("-observed_on")[:limit]
    )
    rows.reverse()
    return [
        {
            "observed_on": row.observed_on.isoformat(),
            "mood": row.mood,
            "sleep_quality": row.sleep_quality,
            "stress": row.stress,
            "fatigue": row.fatigue,
            "connection": row.connection,
        }
        for row in rows
    ]


def sleep_series(subject_token: str, *, limit: int = 14) -> list[int]:
    """Likert sleep values for settled-low detection. Never returned over HTTP."""
    rows = CheckinResponse.objects.filter(subject_token=subject_token).order_by("observed_on")[
        :limit
    ]
    return [
        row.sleep_quality
        for row in rows
        if isinstance(row.sleep_quality, int) and not isinstance(row.sleep_quality, bool)
    ]
