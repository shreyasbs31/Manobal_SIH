"""Critical-incident ingest and the 72-hour extra check-in window (UC-16)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from django.db import IntegrityError
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from manobal_core.apps.governance.models import Subject, Unit, UnitIncident

WINDOW_HOURS = 72


class IncidentRefused(ValueError):  # noqa: N818
    """The payload could not be recorded."""


def record_incident(
    *,
    unit_code: str,
    occurred_at: datetime | str,
    category: str,
    source_system: str = "ops",
    external_id: str = "",
    window_hours: int = WINDOW_HOURS,
) -> UnitIncident:
    """Idempotent on ``(source_system, external_id)`` when an external id is given."""
    unit = Unit.objects.filter(code=unit_code).first()
    if unit is None:
        raise IncidentRefused("unknown unit")
    kind = category.strip()
    if not kind:
        raise IncidentRefused("category is required")
    moment = _when(occurred_at)
    hours = window_hours if window_hours > 0 else WINDOW_HOURS
    if external_id:
        existing = UnitIncident.objects.filter(
            source_system=source_system, external_id=external_id
        ).first()
        if existing is not None:
            return existing
    try:
        return UnitIncident.objects.create(
            unit=unit,
            occurred_at=moment,
            category=kind[:64],
            source_system=source_system[:32],
            external_id=external_id[:64],
            window_hours=hours,
        )
    except IntegrityError:
        return UnitIncident.objects.get(source_system=source_system, external_id=external_id)


def offer_checkin_for(subject: Subject, *, now: datetime | None = None) -> dict[str, Any]:
    """Whether this person's unit is inside an incident check-in window."""
    moment = now or timezone.now()
    rows = UnitIncident.objects.filter(unit=subject.unit).order_by("-occurred_at")
    for row in rows:
        ends = row.occurred_at + timedelta(hours=int(row.window_hours))
        if row.occurred_at <= moment <= ends:
            return {
                "offer_checkin": True,
                "incident_category": row.category,
                "window_ends_at": ends.isoformat(),
            }
    return {"offer_checkin": False}


def _when(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = parse_datetime(str(value).replace("Z", "+00:00"))
    if parsed is None:
        raise IncidentRefused("occurred_at must be an ISO timestamp")
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed
