"""The journal is ciphertext, never scored, and never an officer surface."""

from __future__ import annotations

import inspect

import pytest

from manobal_core.apps.governance.enums import DataType
from manobal_core.apps.governance.models import (
    ConsentEntry,
    ConsentTextVersion,
    JournalKey,
    Subject,
)
from manobal_core.apps.psystore.models import JournalEntry
from manobal_core.journal.crypto import JournalCryptoError, decrypt_body, destroy_keys
from manobal_core.journal.service import JournalRefused, list_entries, write_entry
from manobal_core.scoring import features as features_mod
from manobal_core.scoring.features import assemble_history

from .test_core_api import client_for, personnel_of


@pytest.mark.django_db(databases=["default", "psy"])
class TestJournalService:
    def test_journal_consent_is_required(
        self, subject: Subject, consent_text: ConsentTextVersion
    ) -> None:
        del consent_text
        with pytest.raises(JournalRefused, match="consent"):
            write_entry(subject, body="a private sentence")

    def test_plaintext_is_not_stored(
        self, subject: Subject, consent_text: ConsentTextVersion
    ) -> None:
        ConsentEntry.objects.create(
            subject_token=subject.subject_token,
            data_type=DataType.JOURNAL,
            granted=True,
            consent_text=consent_text,
        )
        write_entry(subject, body="a private sentence")
        row = JournalEntry.objects.get(subject_token=subject.subject_token)
        assert bytes(row.ciphertext) != b"a private sentence"
        assert b"private" not in bytes(row.ciphertext)
        opened = decrypt_body(
            subject.subject_token, bytes(row.ciphertext), bytes(row.nonce), row.key_id
        )
        assert opened == "a private sentence"

    def test_destroying_the_key_makes_the_backup_mute(
        self, subject: Subject, consent_text: ConsentTextVersion
    ) -> None:
        ConsentEntry.objects.create(
            subject_token=subject.subject_token,
            data_type=DataType.JOURNAL,
            granted=True,
            consent_text=consent_text,
        )
        write_entry(subject, body="a private sentence")
        row = JournalEntry.objects.get(subject_token=subject.subject_token)
        destroy_keys(subject.subject_token)
        assert JournalKey.objects.get(subject_token=subject.subject_token).destroyed_at
        with pytest.raises(JournalCryptoError):
            decrypt_body(
                subject.subject_token, bytes(row.ciphertext), bytes(row.nonce), row.key_id
            )
        assert list_entries(subject.subject_token) == []

    def test_the_engine_has_no_read_path_to_the_journal(
        self, subject: Subject, consent_text: ConsentTextVersion
    ) -> None:
        ConsentEntry.objects.create(
            subject_token=subject.subject_token,
            data_type=DataType.JOURNAL,
            granted=True,
            consent_text=consent_text,
        )
        write_entry(subject, body="a private sentence")
        assert "JournalEntry" not in inspect.getsource(features_mod)
        history = assemble_history(subject.subject_token)
        rendered = repr(history)
        assert "private sentence" not in rendered


@pytest.mark.django_db(databases=["default", "psy"])
class TestJournalHttp:
    def test_personnel_can_write_and_read_their_own_journal(
        self, subject: Subject, consent_text: ConsentTextVersion
    ) -> None:
        ConsentEntry.objects.create(
            subject_token=subject.subject_token,
            data_type=DataType.JOURNAL,
            granted=True,
            consent_text=consent_text,
        )
        client = client_for(personnel_of(subject))
        created = client.post("/v1/me/journal", {"body": "a private sentence"}, format="json")
        assert created.status_code == 201
        assert created.json()["body"] == "a private sentence"
        listing = client.get("/v1/me/journal")
        assert listing.status_code == 200
        assert listing.json()["entries"][0]["body"] == "a private sentence"

    def test_an_officer_cannot_read_the_journal(
        self, subject: Subject, officer_principal
    ) -> None:
        del subject
        response = client_for(officer_principal).get("/v1/me/journal")
        assert response.status_code == 403
