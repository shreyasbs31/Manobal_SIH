"""Apply a device capture batch. Token already present; identifiers never are."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

from django.db import IntegrityError
from django.utils import timezone

from manobal_core.apps.biostore.models import PhysiologicalObservation
from manobal_core.apps.governance.enums import DataType
from manobal_core.apps.governance.models import CaptureReceipt, ConsentEntry, Subject
from manobal_core.apps.psystore.models import CheckinResponse
from manobal_core.apps.voicestore.models import VoiceObservation

_STALE_DAYS = 14


def ingest_capture_batch(
    *,
    subject_token: str,
    client_batch_id: str,
    items: list[dict[str, Any]],
) -> CaptureReceipt:
    """Idempotent on ``client_batch_id``. Drops unconsented and stale items."""
    existing = CaptureReceipt.objects.filter(client_batch_id=client_batch_id).first()
    if existing is not None:
        return existing
    consent = ConsentEntry.current_for(subject_token)
    cutoff = timezone.now() - timedelta(days=_STALE_DAYS)
    accepted = 0
    unconsented = 0
    stale = 0
    for item in items:
        kind = str(item.get("kind") or "")
        observed = _when(item)
        if observed is not None and observed < cutoff:
            stale += 1
            continue
        if kind == "bio" and consent.get(DataType.BIOMETRIC):
            _write_bio(subject_token, item, observed)
            accepted += 1
        elif kind == "voice" and consent.get(DataType.VOICE_FEATURES):
            _write_voice(subject_token, item, observed)
            accepted += 1
        elif kind == "checkin" and consent.get(DataType.SELF_REPORT):
            _write_checkin(subject_token, item, observed)
            accepted += 1
        elif kind == "journal" and consent.get(DataType.JOURNAL):
            if _write_journal(subject_token, item):
                accepted += 1
            else:
                unconsented += 1
        elif kind == "instrument" and consent.get(DataType.SELF_REPORT):
            if _write_instrument(subject_token, item):
                accepted += 1
            else:
                unconsented += 1
        else:
            unconsented += 1
    try:
        return CaptureReceipt.objects.create(
            subject_token=subject_token,
            client_batch_id=client_batch_id,
            item_count=len(items),
            accepted_count=accepted,
            rejected_unconsented=unconsented,
            rejected_stale=stale,
        )
    except IntegrityError:
        return CaptureReceipt.objects.get(client_batch_id=client_batch_id)


def _when(item: dict[str, Any]) -> datetime | None:
    raw = item.get("observed_at") or item.get("captured_at")
    if not raw:
        return None
    parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _day(item: dict[str, Any], observed: datetime | None) -> date:
    if item.get("observed_on"):
        return date.fromisoformat(str(item["observed_on"]))
    if observed is not None:
        return observed.date()
    return timezone.localdate()


def _write_bio(token: str, item: dict[str, Any], observed: datetime | None) -> None:
    PhysiologicalObservation.objects.update_or_create(
        subject_token=token,
        observed_on=_day(item, observed),
        metric_code=str(item.get("metric_code") or ""),
        defaults={
            "value": float(item.get("value") or 0),
            "observed_at": observed or timezone.now(),
            "source": str(item.get("source") or "wearable"),
        },
    )


def _write_voice(token: str, item: dict[str, Any], observed: datetime | None) -> None:
    features = item.get("features") if isinstance(item.get("features"), dict) else {}
    embedding = item.get("embedding") if isinstance(item.get("embedding"), list) else []
    VoiceObservation.objects.update_or_create(
        subject_token=token,
        captured_on=_day(item, observed),
        defaults={
            "captured_at": observed or timezone.now(),
            "features": features,
            "embedding": embedding,
            "language_code": str(item.get("language_code") or "en"),
        },
    )


def _write_checkin(token: str, item: dict[str, Any], observed: datetime | None) -> None:
    CheckinResponse.objects.update_or_create(
        subject_token=token,
        observed_on=_day(item, observed),
        defaults={
            "mood": item.get("mood"),
            "sleep_quality": item.get("sleep_quality"),
            "stress": item.get("stress"),
            "fatigue": item.get("fatigue"),
            "connection": item.get("connection"),
        },
    )


def _write_journal(token: str, item: dict[str, Any]) -> bool:
    from manobal_core.journal.service import JournalRefused, write_entry

    subject = Subject.objects.filter(subject_token=token).first()
    if subject is None:
        return False
    try:
        write_entry(
            subject,
            body=str(item.get("body") or ""),
            crisis_accepted=bool(item.get("crisis_accepted")),
        )
    except JournalRefused:
        return False
    return True


def _write_instrument(token: str, item: dict[str, Any]) -> bool:
    from manobal_core.instruments.submit import InstrumentRefused, submit_instrument

    subject = Subject.objects.filter(subject_token=token).first()
    if subject is None:
        return False
    answers = item.get("answers")
    if not isinstance(answers, list):
        return False
    try:
        parsed = [int(value) for value in answers]
        duration = item.get("duration_seconds")
        submit_instrument(
            subject,
            code=str(item.get("code") or ""),
            language=str(item.get("language") or "en"),
            answers=parsed,
            duration_seconds=None if duration in (None, "") else int(duration),
        )
    except (TypeError, ValueError, InstrumentRefused):
        return False
    return True
