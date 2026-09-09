"""Assemble a ``SubjectHistory`` from the five analytics stores.

The engine is a pure function. This module is the only place that is allowed
to turn store rows into observations, and it drops any domain the person has
not consented to before the engine sees it.
"""

from __future__ import annotations

from datetime import date

from django.utils import timezone

from manobal_core.apps.biostore.models import PhysiologicalObservation
from manobal_core.apps.governance.enums import DataType, Tier
from manobal_core.apps.governance.models import ConsentEntry, RiskAssessmentRecord
from manobal_core.apps.orgstore.models import (
    DutyObservation,
    EngagementObservation,
    LeaveObservation,
)
from manobal_core.apps.psystore.models import AcuteSignal, CheckinResponse, InstrumentResponse
from manobal_core.apps.voicestore.models import VoiceObservation
from manobal_risk.types import AcuteTrigger, AcuteTriggerKind, Domain, Observation, SubjectHistory
from manobal_risk.types import Tier as EngineTier

_ORG_DOMAINS = frozenset({Domain.WORKLOAD, Domain.LEAVE, Domain.ORGANISATIONAL})
_INSTRUMENT_TO_INDICATOR = {
    "pss10": "pss10_total",
    "phq9": "phq9_total",
    "gad7": "gad7_total",
}


def consented_domains(subject_token: str) -> frozenset[Domain]:
    state = ConsentEntry.current_for(subject_token)
    domains: set[Domain] = set()
    if state.get(DataType.ORG):
        domains.update(_ORG_DOMAINS)
    if state.get(DataType.SELF_REPORT):
        domains.add(Domain.SELF_REPORT)
        domains.add(Domain.ENGAGEMENT)
    if state.get(DataType.BIOMETRIC):
        domains.add(Domain.PHYSIOLOGICAL)
    if state.get(DataType.VOICE_FEATURES):
        domains.add(Domain.VOCAL_ACOUSTIC)
    return frozenset(domains)


def assemble_history(subject_token: str, *, as_of: date | None = None) -> SubjectHistory:
    """Load consented observations for ``subject_token`` as of ``as_of``."""
    day = as_of or timezone.localdate()
    domains = consented_domains(subject_token)
    observations: list[Observation] = []
    if Domain.WORKLOAD in domains:
        observations.extend(_duty(subject_token, day))
    if Domain.LEAVE in domains:
        observations.extend(_leave(subject_token, day))
    if Domain.SELF_REPORT in domains:
        observations.extend(_self_report(subject_token, day))
    if Domain.PHYSIOLOGICAL in domains:
        observations.extend(_bio(subject_token, day))
    if Domain.VOCAL_ACOUSTIC in domains:
        observations.extend(_voice(subject_token, day))
    if Domain.ENGAGEMENT in domains:
        observations.extend(_engagement(subject_token, day))
    return SubjectHistory(
        subject_token=subject_token,
        as_of=day,
        observations=tuple(observations),
        consented_domains=domains,
        acute_triggers=_acute(subject_token),
        previous_tier=_previous_tier(subject_token),
    )


def _duty(token: str, day: date) -> list[Observation]:
    rows = DutyObservation.objects.filter(subject_token=token, observed_on__lte=day)
    out: list[Observation] = []
    for row in rows:
        if row.duty_hours_7d is not None:
            out.append(Observation("duty_hours_7d", row.observed_on, float(row.duty_hours_7d)))
        if row.consecutive_duty_days:
            out.append(
                Observation(
                    "consecutive_duty_days",
                    row.observed_on,
                    float(row.consecutive_duty_days),
                )
            )
    return out


def _leave(token: str, day: date) -> list[Observation]:
    rows = LeaveObservation.objects.filter(subject_token=token, observed_on__lte=day)
    return [
        Observation("leave_rejection_count", row.observed_on, float(row.leave_denied_count_90d))
        for row in rows
    ]


def _self_report(token: str, day: date) -> list[Observation]:
    out: list[Observation] = []
    for row in InstrumentResponse.objects.filter(subject_token=token, completed_at__date__lte=day):
        code = _INSTRUMENT_TO_INDICATOR.get(row.instrument_code.lower())
        if code:
            out.append(Observation(code, row.completed_at.date(), float(row.total_score)))
    checkins = CheckinResponse.objects.filter(subject_token=token, observed_on__lte=day)
    for checkin in checkins:
        if checkin.mood is not None:
            out.append(Observation("ema_mood", checkin.observed_on, float(checkin.mood)))
        if checkin.stress is not None:
            out.append(Observation("ema_fatigue", checkin.observed_on, float(checkin.stress)))
        if checkin.sleep_quality is not None:
            out.append(
                Observation(
                    "ema_sleep_quality",
                    checkin.observed_on,
                    float(checkin.sleep_quality),
                )
            )
    return out


def _bio(token: str, day: date) -> list[Observation]:
    rows = PhysiologicalObservation.objects.filter(subject_token=token, observed_on__lte=day)
    return [Observation(row.metric_code, row.observed_on, float(row.value)) for row in rows]


def _voice(token: str, day: date) -> list[Observation]:
    out: list[Observation] = []
    for row in VoiceObservation.objects.filter(subject_token=token, captured_on__lte=day):
        if not isinstance(row.features, dict):
            continue
        for code, value in row.features.items():
            if isinstance(value, (int, float)):
                out.append(Observation(str(code), row.captured_on, float(value)))
    return out


def _engagement(token: str, day: date) -> list[Observation]:
    rows = EngagementObservation.objects.filter(subject_token=token, observed_on__lte=day)
    return [
        Observation("app_session_count_14d", row.observed_on, float(row.app_sessions))
        for row in rows
    ]


def _acute(token: str) -> tuple[AcuteTrigger, ...]:
    out: list[AcuteTrigger] = []
    for row in AcuteSignal.objects.filter(subject_token=token):
        try:
            kind = AcuteTriggerKind(row.signal_code)
        except ValueError:
            continue
        out.append(AcuteTrigger(kind=kind, occurred_at=row.detected_at, source=row.source))
    return tuple(out)


def _previous_tier(token: str) -> EngineTier:
    record = (
        RiskAssessmentRecord.objects.filter(subject_token=token)
        .order_by("-assessed_at", "-id")
        .first()
    )
    if record is None:
        return EngineTier.T0
    stored = Tier(record.tier)
    return EngineTier[stored]
