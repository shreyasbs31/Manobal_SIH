"""Personnel journal write and read. Officers have no function here."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from django.utils import timezone

from manobal_core.alerting.acute import raise_acute
from manobal_core.apps.governance.enums import DataType
from manobal_core.apps.governance.models import ConsentEntry, Subject
from manobal_core.apps.psystore.models import JournalEntry
from manobal_core.journal.crypto import JournalCryptoError, decrypt_body, encrypt_body

MAX_BODY_CHARS = 8_000
LIST_LIMIT = 20


class JournalRefused(ValueError):  # noqa: N818
    """Consent missing, or the body is empty / too long."""


@dataclass(frozen=True, slots=True)
class JournalRecord:
    id: int
    created_at: datetime
    body: str
    crisis_referred: bool


def write_entry(
    subject: Subject,
    *,
    body: str,
    crisis_accepted: bool = False,
) -> JournalRecord:
    text = body.strip()
    if not text:
        raise JournalRefused("journal body is required")
    if len(text) > MAX_BODY_CHARS:
        raise JournalRefused("journal body exceeds the length ceiling")
    if not ConsentEntry.current_for(subject.subject_token).get(DataType.JOURNAL):
        raise JournalRefused("journal consent is required")
    ciphertext, nonce, key_id = encrypt_body(subject.subject_token, text)
    referred = timezone.now() if crisis_accepted else None
    row = JournalEntry.objects.create(
        subject_token=subject.subject_token,
        ciphertext=ciphertext,
        nonce=nonce,
        key_id=key_id,
        crisis_referred_at=referred,
    )
    if crisis_accepted:
        raise_acute(
            subject,
            signal_code="explicit_sos",
            source="device_triage",
            self_initiated=True,
        )
    return _record(row, text)


def list_entries(subject_token: str) -> list[JournalRecord]:
    rows = JournalEntry.objects.filter(subject_token=subject_token).order_by(
        "-created_at", "-id"
    )[:LIST_LIMIT]
    out: list[JournalRecord] = []
    for row in rows:
        try:
            plaintext = decrypt_body(
                subject_token, bytes(row.ciphertext), bytes(row.nonce), row.key_id
            )
        except JournalCryptoError:
            continue
        out.append(_record(row, plaintext))
    return out


def _record(row: JournalEntry, body: str) -> JournalRecord:
    return JournalRecord(
        id=row.id,
        created_at=row.created_at,
        body=body,
        crisis_referred=row.crisis_referred_at is not None,
    )
