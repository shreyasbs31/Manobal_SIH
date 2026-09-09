"""Device captures are idempotent and honour consent."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from django.utils import timezone

from manobal_core.apps.biostore.models import PhysiologicalObservation
from manobal_core.apps.governance.enums import DataType
from manobal_core.apps.governance.models import ConsentEntry, ConsentTextVersion, Subject
from manobal_core.ingest.captures import ingest_capture_batch

pytestmark = pytest.mark.django_db(databases=["default", "psy", "bio", "voice"])


def test_unconsented_bio_is_rejected(
    subject: Subject, consent_text: ConsentTextVersion
) -> None:
    del consent_text
    receipt = ingest_capture_batch(
        subject_token=subject.subject_token,
        client_batch_id="batch-1",
        items=[
            {
                "kind": "bio",
                "metric_code": "resting_hr_nightly",
                "value": 68,
                "observed_on": "2026-09-08",
                "observed_at": timezone.now().isoformat(),
            }
        ],
    )
    assert receipt.accepted_count == 0
    assert receipt.rejected_unconsented == 1
    assert PhysiologicalObservation.objects.count() == 0


def test_consented_bio_is_written_once(
    subject: Subject, consent_text: ConsentTextVersion
) -> None:
    ConsentEntry.objects.create(
        subject_token=subject.subject_token,
        data_type=DataType.BIOMETRIC,
        granted=True,
        consent_text=consent_text,
    )
    item = {
        "kind": "bio",
        "metric_code": "resting_hr_nightly",
        "value": 68,
        "observed_on": "2026-09-08",
        "observed_at": timezone.now().isoformat(),
    }
    first = ingest_capture_batch(
        subject_token=subject.subject_token, client_batch_id="batch-2", items=[item]
    )
    second = ingest_capture_batch(
        subject_token=subject.subject_token, client_batch_id="batch-2", items=[item]
    )
    assert first.id == second.id
    assert PhysiologicalObservation.objects.filter(subject_token=subject.subject_token).count() == 1


def test_stale_items_are_dropped(subject: Subject, consent_text: ConsentTextVersion) -> None:
    ConsentEntry.objects.create(
        subject_token=subject.subject_token,
        data_type=DataType.BIOMETRIC,
        granted=True,
        consent_text=consent_text,
    )
    old = datetime.now(tz=UTC) - timedelta(days=21)
    receipt = ingest_capture_batch(
        subject_token=subject.subject_token,
        client_batch_id="batch-3",
        items=[
            {
                "kind": "bio",
                "metric_code": "resting_hr_nightly",
                "value": 90,
                "observed_at": old.isoformat(),
            }
        ],
    )
    assert receipt.rejected_stale == 1
    assert PhysiologicalObservation.objects.count() == 0
