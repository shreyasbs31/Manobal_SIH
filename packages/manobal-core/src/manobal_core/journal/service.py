"""Personnel journal write and read. Officers have no function here."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.utils import timezone

from manobal_core.alerting.acute import raise_acute
from manobal_core.apps.governance.enums import DataType, Tier
from manobal_core.apps.governance.models import ConsentEntry, RiskAssessmentRecord, Subject
from manobal_core.apps.psystore.models import JournalEntry
from manobal_core.journal.crypto import JournalCryptoError, decrypt_body, encrypt_body

JOURNAL_PAUSED_TIERS = frozenset({Tier.T3, Tier.T4})

MAX_BODY_CHARS = 8_000
LIST_LIMIT = 20
SESSION_RETAIN_HOURS = 24


class JournalRefused(ValueError):  # noqa: N818
    """Consent missing, or the body is empty / too long."""


@dataclass(frozen=True, slots=True)
class JournalRecord:
    id: int
    created_at: datetime
    body: str
    crisis_referred: bool
    expires_at: datetime | None


def write_entry(
    subject: Subject,
    *,
    body: str,
    crisis_accepted: bool = False,
    retain: bool = True,
) -> JournalRecord:
    text = body.strip()
    if not text:
        raise JournalRefused("journal body is required")
    if len(text) > MAX_BODY_CHARS:
        raise JournalRefused("journal body exceeds the length ceiling")
    if not ConsentEntry.current_for(subject.subject_token).get(DataType.JOURNAL):
        raise JournalRefused("journal consent is required")
    if _journal_paused(subject.subject_token):
        raise JournalRefused("journal is paused at T3 or T4")
    ciphertext, nonce, key_id = encrypt_body(subject.subject_token, text)
    referred = timezone.now() if crisis_accepted else None
    expires = None if retain else timezone.now() + timedelta(hours=SESSION_RETAIN_HOURS)
    row = JournalEntry.objects.create(
        subject_token=subject.subject_token,
        ciphertext=ciphertext,
        nonce=nonce,
        key_id=key_id,
        crisis_referred_at=referred,
        expires_at=expires,
    )
    if crisis_accepted:
        raise_acute(
            subject,
            signal_code="explicit_sos",
            source="device_triage",
            self_initiated=True,
        )
    return _record(row, text)


def delete_entry(subject_token: str, entry_id: int) -> None:
    """Remove one of the person's own entries. Officers have no path here."""
    deleted, _ = JournalEntry.objects.filter(subject_token=subject_token, pk=entry_id).delete()
    if not deleted:
        raise JournalRefused("unknown journal entry")


def journal_is_paused(subject_token: str) -> bool:
    return _journal_paused(subject_token)


def _journal_paused(subject_token: str) -> bool:
    latest = (
        RiskAssessmentRecord.objects.filter(subject_token=subject_token)
        .order_by("-assessed_at", "-id")
        .first()
    )
    return latest is not None and latest.tier in JOURNAL_PAUSED_TIERS


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
        expires_at=row.expires_at,
    )
