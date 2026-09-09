"""Withdrawal must actually delete, store by store, and survive a crash (FR-7.2).

Recording intent is not erasure. The saga purges the named stores, skips the
ones already done, leaves the consent ledger and the audit chain alone, and
hands the person a signed receipt when every store is finished.
"""

from __future__ import annotations

from datetime import date

import pytest
from django.utils import timezone

from manobal_core.apps.biostore.models import PhysiologicalObservation
from manobal_core.apps.governance.enums import DataType, ErasureStatus
from manobal_core.apps.governance.models import (
    AuditEvent,
    ConsentEntry,
    ConsentTextVersion,
    ErasureRequest,
    Subject,
)
from manobal_core.apps.orgstore.models import DutyObservation
from manobal_core.apps.psystore.models import CheckinResponse, JournalEntry
from manobal_core.apps.voicestore.models import VoiceObservation
from manobal_core.erasure.saga import advance_erasure, resume_pending

pytestmark = pytest.mark.django_db(databases=["default", "org", "psy", "bio", "voice"])


def _seed_signals(token: str) -> None:
    DutyObservation.objects.create(
        subject_token=token, observed_on=date(2026, 9, 8), duty_hours=10.0
    )
    CheckinResponse.objects.create(subject_token=token, observed_on=date(2026, 9, 8), mood=2)
    JournalEntry.objects.create(
        subject_token=token, ciphertext=b"secret", key_id="k1", nonce=b"n1"
    )
    PhysiologicalObservation.objects.create(
        subject_token=token,
        observed_on=date(2026, 9, 8),
        metric_code="resting_hr_nightly",
        value=72.0,
    )
    VoiceObservation.objects.create(
        subject_token=token,
        captured_on=date(2026, 9, 8),
        features={"voice_f0_variability": 1.2},
    )


class TestErasureSaga:
    def test_a_biometric_withdrawal_purges_only_bio_store(
        self, subject: Subject
    ) -> None:
        token = subject.subject_token
        _seed_signals(token)
        request = ErasureRequest.objects.create(
            subject_token=token, data_type=DataType.BIOMETRIC
        )
        done = advance_erasure(request)
        assert done.status == ErasureStatus.COMPLETED
        assert done.receipt_id
        assert done.receipt_signature
        assert PhysiologicalObservation.objects.filter(subject_token=token).count() == 0
        assert DutyObservation.objects.filter(subject_token=token).count() == 1
        assert CheckinResponse.objects.filter(subject_token=token).count() == 1
        assert JournalEntry.objects.filter(subject_token=token).count() == 1

    def test_a_full_erasure_purges_every_signal_store_and_keeps_the_ledger(
        self, subject: Subject, consent_text: ConsentTextVersion
    ) -> None:
        token = subject.subject_token
        _seed_signals(token)
        ConsentEntry.objects.create(
            subject_token=token,
            data_type=DataType.BIOMETRIC,
            granted=False,
            consent_text=consent_text,
        )
        request = ErasureRequest.objects.create(subject_token=token, data_type=None)
        done = advance_erasure(request)
        assert done.status == ErasureStatus.COMPLETED
        assert DutyObservation.objects.filter(subject_token=token).count() == 0
        assert CheckinResponse.objects.filter(subject_token=token).count() == 0
        assert JournalEntry.objects.filter(subject_token=token).count() == 0
        assert PhysiologicalObservation.objects.filter(subject_token=token).count() == 0
        assert VoiceObservation.objects.filter(subject_token=token).count() == 0
        assert ConsentEntry.objects.filter(subject_token=token).count() == 1
        assert (
            AuditEvent.objects.filter(action="erasure.complete", subject_token=token).count()
            == 1
        )
        assert Subject.objects.filter(pk=token).exists()

    def test_a_crash_is_resumable(
        self, subject: Subject, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        token = subject.subject_token
        _seed_signals(token)
        request = ErasureRequest.objects.create(subject_token=token, data_type=None)

        from manobal_core.erasure import stores as store_mod

        original = store_mod.PURGERS[store_mod.PSY]

        def boom(erasure: ErasureRequest) -> None:
            del erasure
            raise RuntimeError("psy store unavailable")

        monkeypatch.setitem(store_mod.PURGERS, store_mod.PSY, boom)
        with pytest.raises(RuntimeError, match="unavailable"):
            advance_erasure(request)
        request.refresh_from_db()
        assert request.status == ErasureStatus.FAILED
        assert request.store_progress["org_store"] == "completed"
        assert request.store_progress["psy_store"] != "completed"
        assert DutyObservation.objects.filter(subject_token=token).count() == 0
        assert CheckinResponse.objects.filter(subject_token=token).count() == 1

        monkeypatch.setitem(store_mod.PURGERS, store_mod.PSY, original)
        request.status = ErasureStatus.IN_PROGRESS
        request.save(update_fields=["status"])
        done = advance_erasure(request)
        assert done.status == ErasureStatus.COMPLETED
        assert CheckinResponse.objects.filter(subject_token=token).count() == 0

    def test_resume_pending_picks_up_intent_and_failed_rows(
        self, subject: Subject
    ) -> None:
        token = subject.subject_token
        _seed_signals(token)
        ErasureRequest.objects.create(subject_token=token, data_type=DataType.ORG)
        finished = resume_pending()
        assert finished == 1
        assert DutyObservation.objects.filter(subject_token=token).count() == 0
        row = ErasureRequest.objects.get(subject_token=token)
        assert row.status == ErasureStatus.COMPLETED
        assert timezone.now() >= row.completed_at
