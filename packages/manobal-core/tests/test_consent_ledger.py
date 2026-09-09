"""Consent ledger semantics (SDD §5.2, §6.4.1, §7.9, FR-1.2, FR-7.2).

The behaviour under test is mostly about what the system refuses to infer.
Silence is not consent, a grant for one data type says nothing about another,
and a withdrawal is a new fact rather than an erasure of the old one.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.db import connections
from django.db.utils import IntegrityError
from django.utils import timezone

from manobal_core.apps.governance.enums import DataType, ErasureStatus
from manobal_core.apps.governance.models import (
    ConsentEntry,
    ConsentTextVersion,
    ErasureRequest,
)

pytestmark = pytest.mark.django_db

TOKEN = "tok_consent_0001"


def _grant(text: ConsentTextVersion, data_type: str, *, granted: bool, ago_days: int = 0) -> None:
    ConsentEntry.objects.create(
        subject_token=TOKEN,
        data_type=data_type,
        granted=granted,
        consent_text=text,
        recorded_at=timezone.now() - timedelta(days=ago_days),
    )


class TestGranularity:
    """FR-1.2: each data type is independently grantable. There is no bundle."""

    def test_no_answer_means_no_consent(self, consent_text: ConsentTextVersion) -> None:
        state = ConsentEntry.current_for(TOKEN)
        assert set(state) == set(DataType.values)
        assert not any(state.values())

    def test_granting_one_type_grants_only_that_type(
        self, consent_text: ConsentTextVersion
    ) -> None:
        _grant(consent_text, DataType.SELF_REPORT, granted=True)
        state = ConsentEntry.current_for(TOKEN)
        assert state[DataType.SELF_REPORT] is True
        assert state[DataType.BIOMETRIC] is False
        assert state[DataType.VOICE_FEATURES] is False

    def test_a_data_type_added_later_is_not_retroactively_consented(
        self, consent_text: ConsentTextVersion
    ) -> None:
        """Someone who enrolled before voice existed has not agreed to voice."""
        for data_type in (DataType.ORG, DataType.SELF_REPORT, DataType.BIOMETRIC):
            _grant(consent_text, data_type, granted=True, ago_days=400)
        assert ConsentEntry.current_for(TOKEN)[DataType.VOICE_FEATURES] is False


class TestWithdrawal:
    def test_the_latest_entry_wins(self, consent_text: ConsentTextVersion) -> None:
        _grant(consent_text, DataType.BIOMETRIC, granted=True, ago_days=10)
        _grant(consent_text, DataType.BIOMETRIC, granted=False, ago_days=1)
        assert ConsentEntry.current_for(TOKEN)[DataType.BIOMETRIC] is False

    def test_consent_can_be_regranted_after_withdrawal(
        self, consent_text: ConsentTextVersion
    ) -> None:
        """Withdrawal is not a one-way door. Someone who opts out during a
        difficult posting must be able to opt back in later without an appeal."""
        _grant(consent_text, DataType.SELF_REPORT, granted=True, ago_days=30)
        _grant(consent_text, DataType.SELF_REPORT, granted=False, ago_days=20)
        _grant(consent_text, DataType.SELF_REPORT, granted=True, ago_days=1)
        assert ConsentEntry.current_for(TOKEN)[DataType.SELF_REPORT] is True

    def test_the_history_survives_the_withdrawal(self, consent_text: ConsentTextVersion) -> None:
        """§7.3 needs "were we permitted on 14 March?" to remain answerable."""
        _grant(consent_text, DataType.BIOMETRIC, granted=True, ago_days=10)
        _grant(consent_text, DataType.BIOMETRIC, granted=False, ago_days=1)
        assert ConsentEntry.objects.filter(subject_token=TOKEN).count() == 2


class TestLedgerIsAppendOnly:
    def test_the_orm_refuses_to_edit_an_entry(self, consent_text: ConsentTextVersion) -> None:
        _grant(consent_text, DataType.ORG, granted=True)
        entry = ConsentEntry.objects.get(subject_token=TOKEN)
        entry.granted = False
        with pytest.raises(ValueError, match="append-only"):
            entry.save()

    def test_the_orm_refuses_to_delete_an_entry(self, consent_text: ConsentTextVersion) -> None:
        _grant(consent_text, DataType.ORG, granted=True)
        entry = ConsentEntry.objects.get(subject_token=TOKEN)
        with pytest.raises(ValueError, match="cannot be deleted"):
            entry.delete()

    def test_the_database_rejects_a_rewrite(self, consent_text: ConsentTextVersion) -> None:
        _grant(consent_text, DataType.ORG, granted=True)
        with (
            pytest.raises(IntegrityError, match="append-only"),
            connections["default"].cursor() as cursor,
        ):
            cursor.execute("UPDATE consent_entry SET granted = false")


class TestConsentTextIsPinned:
    """§7.9: a person agreed to a specific wording, not to "the consent text"."""

    def test_an_entry_records_which_wording_was_shown(
        self, consent_text: ConsentTextVersion
    ) -> None:
        _grant(consent_text, DataType.ORG, granted=True)
        entry = ConsentEntry.objects.get(subject_token=TOKEN)
        assert entry.consent_text.version == "1.0.0"
        assert entry.consent_text.language_code == "en"

    def test_a_referenced_wording_cannot_be_deleted(self, consent_text: ConsentTextVersion) -> None:
        """PROTECT, not CASCADE. Removing the wording would leave a grant whose
        terms nobody can reconstruct, which is worse than keeping dead text."""
        from django.db.models import ProtectedError

        _grant(consent_text, DataType.ORG, granted=True)
        with pytest.raises(ProtectedError):
            consent_text.delete()


class TestErasureSaga:
    """§5.4: a withdrawal interrupted by a crash must be visibly incomplete."""

    def test_intent_is_recorded_before_any_purging(self) -> None:
        request = ErasureRequest.objects.create(subject_token=TOKEN)
        assert request.status == ErasureStatus.INTENT_RECORDED
        assert request.completed_at is None

    def test_partial_progress_is_durable(self) -> None:
        request = ErasureRequest.objects.create(
            subject_token=TOKEN,
            status=ErasureStatus.IN_PROGRESS,
            store_progress={"psy_store": "completed", "org_store": "pending"},
        )
        request.refresh_from_db()
        assert request.store_progress["psy_store"] == "completed"
        assert request.store_progress["org_store"] == "pending"

    def test_a_completed_erasure_carries_a_signed_receipt(self) -> None:
        """FR-7.2. The person gets proof, not an assurance."""
        request = ErasureRequest.objects.create(
            subject_token=TOKEN,
            status=ErasureStatus.COMPLETED,
            completed_at=timezone.now(),
            receipt_id="rcpt_0001",
            receipt_signature="ed25519:...",
        )
        assert request.receipt_id
        assert request.receipt_signature

    def test_published_aggregates_are_retained_by_default(self) -> None:
        """§7.9. Retracting an anonymised statistic can re-identify the person
        who left, which is the opposite of what erasure is for."""
        assert ErasureRequest.objects.create(subject_token=TOKEN).retain_aggregates is True
