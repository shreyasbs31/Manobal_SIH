"""Map a synthetic corpus into the five analytics stores.

Identifying files are never read. Observation rows carry a token and a code.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from django.utils import timezone

from manobal_core.apps.biostore.models import PhysiologicalObservation
from manobal_core.apps.governance.enums import DataType
from manobal_core.apps.governance.models import ConsentEntry, ConsentTextVersion, Subject, Unit
from manobal_core.apps.orgstore.models import (
    DutyObservation,
    EngagementObservation,
    LeaveObservation,
)
from manobal_core.apps.psystore.models import CheckinResponse, InstrumentResponse
from manobal_core.apps.voicestore.models import VoiceObservation

_DUTY = frozenset({"duty_hours_7d", "consecutive_duty_days"})
_LEAVE = frozenset({"leave_rejection_count", "leave_denied_count_90d"})
_INSTRUMENT = {
    "phq9_total": "phq9",
    "pss10_total": "pss10",
    "gad7_total": "gad7",
}
_CHECKIN = {
    "ema_mood": "mood",
    "ema_fatigue": "stress",
    "ema_sleep_quality": "sleep_quality",
}
_ENGAGE = frozenset({"app_session_count_14d"})


class ObservationLike(Protocol):
    subject_token: str
    indicator_code: str
    observed_on: date
    value: float


@dataclass(frozen=True, slots=True)
class LoadReceipt:
    subjects: int
    observations: int


def load_observation_rows(
    rows: Iterable[ObservationLike],
    *,
    unit: Unit,
    consent_text: ConsentTextVersion | None = None,
) -> LoadReceipt:
    """Write tokenised observations. ``rows`` expose the ObservationRow fields."""
    grouped: dict[tuple[str, date], list[tuple[str, float]]] = defaultdict(list)
    tokens: set[str] = set()
    count = 0
    for row in rows:
        token = str(row.subject_token)
        code = str(row.indicator_code)
        day = row.observed_on
        value = float(row.value)
        if not isinstance(day, date):
            continue
        grouped[(token, day)].append((code, value))
        tokens.add(token)
        count += 1
    for token in tokens:
        Subject.objects.get_or_create(
            subject_token=token,
            defaults={
                "unit": unit,
                "force_code": unit.force_code,
                "rank_band": "constable",
                "service_years_bucket": "5-9",
            },
        )
        if consent_text is not None:
            _ensure_org_and_self(token, consent_text)
    for (token, day), items in grouped.items():
        _apply_day(token, day, items)
    return LoadReceipt(subjects=len(tokens), observations=count)


def _ensure_org_and_self(token: str, text: ConsentTextVersion) -> None:
    for data_type in (
        DataType.ORG,
        DataType.SELF_REPORT,
        DataType.BIOMETRIC,
        DataType.VOICE_FEATURES,
    ):
        if ConsentEntry.objects.filter(subject_token=token, data_type=data_type).exists():
            continue
        ConsentEntry.objects.create(
            subject_token=token,
            data_type=data_type,
            granted=True,
            consent_text=text,
        )


def _apply_day(token: str, day: date, items: list[tuple[str, float]]) -> None:
    duty: dict[str, float] = {}
    leave: dict[str, float] = {}
    checkin: dict[str, int] = {}
    voice: dict[str, float] = {}
    sessions: float | None = None
    for code, value in items:
        if code in _DUTY:
            duty[code] = value
        elif code in _LEAVE:
            leave[code] = value
        elif code in _INSTRUMENT:
            completed = timezone.make_aware(datetime.combine(day, datetime.min.time()))
            InstrumentResponse.objects.update_or_create(
                subject_token=token,
                instrument_code=_INSTRUMENT[code],
                completed_at=completed,
                defaults={
                    "instrument_version": "synth",
                    "total_score": value,
                    "subscales": {},
                },
            )
        elif code in _CHECKIN:
            checkin[_CHECKIN[code]] = round(value)
        elif code in _ENGAGE:
            sessions = value
        elif code.startswith("voice_"):
            voice[code] = value
        else:
            PhysiologicalObservation.objects.update_or_create(
                subject_token=token,
                observed_on=day,
                metric_code=code,
                defaults={"value": value, "source": "synth"},
            )
    if duty:
        DutyObservation.objects.update_or_create(
            subject_token=token,
            observed_on=day,
            defaults={
                "duty_hours_7d": duty.get("duty_hours_7d"),
                "consecutive_duty_days": int(duty.get("consecutive_duty_days") or 0),
            },
        )
    if leave:
        LeaveObservation.objects.update_or_create(
            subject_token=token,
            observed_on=day,
            defaults={
                "leave_denied_count_90d": int(
                    leave.get("leave_denied_count_90d") or leave.get("leave_rejection_count") or 0
                )
            },
        )
    if checkin:
        CheckinResponse.objects.update_or_create(
            subject_token=token,
            observed_on=day,
            defaults=checkin,
        )
    if voice:
        VoiceObservation.objects.update_or_create(
            subject_token=token,
            captured_on=day,
            defaults={"features": voice},
        )
    if sessions is not None:
        EngagementObservation.objects.update_or_create(
            subject_token=token,
            observed_on=day,
            defaults={"app_sessions": int(sessions)},
        )
