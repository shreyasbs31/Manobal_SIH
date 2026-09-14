"""Simulated observations so every console has a walkable demo."""

from __future__ import annotations

from contextlib import suppress
from datetime import timedelta

from django.utils import timezone

from manobal_core.apps.biostore.models import PhysiologicalObservation
from manobal_core.apps.governance.models import (
    ConsentTextVersion,
    DataQualityReport,
    OfficerProfile,
    Subject,
    Unit,
    UnitAggregate,
)
from manobal_core.apps.orgstore.models import (
    DutyObservation,
    EngagementObservation,
    LeaveObservation,
)
from manobal_core.apps.psystore.models import CheckinResponse, InstrumentResponse
from manobal_core.apps.voicestore.models import VoiceObservation
from manobal_core.ingest.incidents import record_incident
from manobal_core.journal.service import JournalRefused, list_entries, write_entry


def populate_demo(
    subjects: list[Subject],
    *,
    company: Unit,
    consent_text: ConsentTextVersion,
) -> dict[str, int]:
    """Idempotent fake HRMS / EMA / wearable / incident history for the desks."""
    del consent_text
    today = timezone.localdate()
    now = timezone.now()
    checkins = 0
    for index, subject in enumerate(subjects):
        token = subject.subject_token
        for offset in range(14):
            day = today - timedelta(days=13 - offset)
            mood = _clamp(4 - offset // 5, 1, 5) if index == 0 else _clamp(3 + (index % 2), 1, 5)
            sleep = _clamp(4 - offset // 4, 1, 5) if index == 0 else 3
            fatigue = _clamp(2 + offset // 5, 1, 5) if index == 0 else 2
            CheckinResponse.objects.update_or_create(
                subject_token=token,
                observed_on=day,
                defaults={
                    "mood": mood,
                    "sleep_quality": sleep,
                    "stress": fatigue,
                    "fatigue": fatigue,
                    "connection": 3 if index else 2,
                    "concern_tag": "sleep" if index == 0 and offset > 8 else "",
                },
            )
            checkins += 1
            DutyObservation.objects.update_or_create(
                subject_token=token,
                observed_on=day,
                defaults={
                    "duty_hours": 10.0 if index < 3 else 8.0,
                    "duty_hours_7d": 68.0 if index < 3 else 48.0,
                    "consecutive_duty_days": 6 if index < 3 else 3,
                    "night_duty": index == 0,
                },
            )
        LeaveObservation.objects.update_or_create(
            subject_token=token,
            observed_on=today,
            defaults={"leave_denied_count_90d": 2 if index < 3 else 0, "days_since_last_leave": 40},
        )
        EngagementObservation.objects.update_or_create(
            subject_token=token,
            observed_on=today,
            defaults={"app_sessions": 4 if index == 0 else 1},
        )
        PhysiologicalObservation.objects.update_or_create(
            subject_token=token,
            observed_on=today,
            metric_code="resting_hr_nightly",
            defaults={"value": 78.0 if index == 0 else 64.0, "observed_at": now, "source": "demo"},
        )
    lead = subjects[0]
    if not InstrumentResponse.objects.filter(subject_token=lead.subject_token).exists():
        InstrumentResponse.objects.create(
            subject_token=lead.subject_token,
            instrument_code="pss10",
            instrument_version="1.0",
            language_code="en",
            total_score=18.0,
            duration_seconds=140,
        )
    VoiceObservation.objects.update_or_create(
        subject_token=lead.subject_token,
        captured_on=today,
        defaults={"captured_at": now, "features": {"f0_mean": 118.0}, "language_code": "en"},
    )
    if not list_entries(lead.subject_token):
        with suppress(JournalRefused):
            write_entry(lead, body="Sleep has been thin this week. Writing it down helps.")
    record_incident(
        unit_code=company.code,
        occurred_at=now - timedelta(hours=6),
        category="high_intensity",
        external_id="demo-ops-1",
    )
    DataQualityReport.objects.update_or_create(
        source_system="hrms",
        period_start=today,
        period_end=today,
        defaults={"expected_records": len(subjects), "received_records": len(subjects)},
    )
    OfficerProfile.objects.filter(actor_id="officer-001").update(duty_phone_e164="+919800000001")
    UnitAggregate.objects.filter(unit=company).delete()
    return {"subjects": len(subjects), "checkins": checkins}


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))
