"""Nightly scoring and the beat schedule exist and do not persist a score."""

from __future__ import annotations

from datetime import date

import pytest

from manobal_core.apps.governance.enums import DataType
from manobal_core.apps.governance.models import (
    ConsentEntry,
    ConsentTextVersion,
    RiskAssessmentRecord,
    Subject,
)
from manobal_core.apps.orgstore.models import DutyObservation
from manobal_core.celery import app as celery_app
from manobal_core.scoring.features import assemble_history
from manobal_core.scoring.nightly import score_subject
from manobal_risk.types import Domain

pytestmark = pytest.mark.django_db(databases=["default", "org", "psy", "bio", "voice"])


def test_assemble_history_honours_consent(
    subject: Subject, consent_text: ConsentTextVersion
) -> None:
    DutyObservation.objects.create(
        subject_token=subject.subject_token,
        observed_on=date(2026, 9, 8),
        duty_hours_7d=40.0,
        consecutive_duty_days=5,
    )
    history = assemble_history(subject.subject_token, as_of=date(2026, 9, 8))
    assert history.consented_domains == frozenset()
    assert history.observations == ()

    ConsentEntry.objects.create(
        subject_token=subject.subject_token,
        data_type=DataType.ORG,
        granted=True,
        consent_text=consent_text,
    )
    history = assemble_history(subject.subject_token, as_of=date(2026, 9, 8))
    assert Domain.WORKLOAD in history.consented_domains
    assert any(obs.indicator_code == "duty_hours_7d" for obs in history.observations)


def test_score_subject_persists_a_tier_never_a_score(
    subject: Subject, officer, consent_text: ConsentTextVersion
) -> None:
    del officer
    ConsentEntry.objects.create(
        subject_token=subject.subject_token,
        data_type=DataType.ORG,
        granted=True,
        consent_text=consent_text,
    )
    DutyObservation.objects.create(
        subject_token=subject.subject_token,
        observed_on=date(2026, 9, 8),
        duty_hours_7d=40.0,
        consecutive_duty_days=5,
    )
    score_subject(subject)
    record = RiskAssessmentRecord.objects.get(subject_token=subject.subject_token)
    names = {field.name for field in record._meta.get_fields()}
    assert "wsi" not in names
    assert record.tier


def test_beat_schedule_covers_scoring_escalation_and_erasure() -> None:
    names = set(celery_app.conf.beat_schedule)
    assert "nightly-score" in names
    assert "escalate-unacked-t4" in names
    assert "resume-erasures" in names
    assert "purge-separated" in names
