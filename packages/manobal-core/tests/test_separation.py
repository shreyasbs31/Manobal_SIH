"""FR-7.4: after the wait, purge observations. Keep the system's own memory."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from django.utils import timezone

from manobal_core.apps.governance.aggregation import ensure_aggregate
from manobal_core.apps.governance.enums import DataType, SubjectStatus
from manobal_core.apps.governance.models import (
    AuditEvent,
    ConsentEntry,
    ConsentTextVersion,
    Subject,
    UnitAggregate,
)
from manobal_core.apps.orgstore.models import DutyObservation
from manobal_core.erasure.separation import mark_separated, purge_separated
from manobal_core.ingest.contract import HRMS_CONTRACT
from manobal_core.ingest.pipeline import ingest_hrms_batch

from .test_ingest import FakeIdentity, hrms_row

pytestmark = pytest.mark.django_db(databases=["default", "org", "psy", "bio", "voice"])


class TestSeparationPurge:
    def test_the_wait_must_elapse_before_observations_are_purged(
        self, subject: Subject, consent_text: ConsentTextVersion, unit_tree
    ) -> None:
        token = subject.subject_token
        ConsentEntry.objects.create(
            subject_token=token,
            data_type=DataType.ORG,
            granted=True,
            consent_text=consent_text,
        )
        DutyObservation.objects.create(
            subject_token=token, observed_on=date(2026, 9, 8), duty_hours=10.0
        )
        snapshot = ensure_aggregate(unit_tree["company"])
        mark_separated(subject)
        subject.refresh_from_db()
        assert subject.status == SubjectStatus.SEPARATED
        assert purge_separated() == 0
        assert DutyObservation.objects.filter(subject_token=token).exists()

        later = timezone.now() + timedelta(days=31)
        finished = purge_separated(now=later)
        assert finished == 1
        assert DutyObservation.objects.filter(subject_token=token).count() == 0
        assert ConsentEntry.objects.filter(subject_token=token).exists()
        assert AuditEvent.objects.filter(subject_token=token).exists()
        assert UnitAggregate.objects.filter(pk=snapshot.pk).exists()
        assert Subject.objects.filter(pk=token).exists()

    def test_hrms_separated_status_starts_the_clock(
        self, unit_tree, consent_text: ConsentTextVersion
    ) -> None:
        del unit_tree, consent_text
        identity = FakeIdentity()
        ingest_hrms_batch(
            source_system="hrms",
            contract_version=HRMS_CONTRACT,
            records=[hrms_row(employment_status="separated")],
            identity=identity,
        )
        subject = Subject.objects.get(pk="st_000001")
        assert subject.status == SubjectStatus.SEPARATED
        assert subject.separated_at is not None
