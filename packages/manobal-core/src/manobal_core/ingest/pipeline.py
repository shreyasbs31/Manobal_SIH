"""Apply one HRMS extract: tokenise, drop identifiers, store derived features.

Order is load-bearing. Tokenisation runs before any Zone 2 insert, including
quarantine, because a failed row still contains a service number. After the
enclave answers, that number is forgotten: the stored payload is the allow-list
from :mod:`.contract`, and nothing else.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from typing import Any

from django.db import transaction
from django.db.models import Sum

from manobal_core.apps.governance.enums import AuditAction, LegalBasis, PurposeCode, Role
from manobal_core.apps.governance.models import (
    AuditEvent,
    IngestBatch,
    QuarantinedRecord,
    Subject,
    Unit,
)
from manobal_core.apps.orgstore.models import DutyObservation, LeaveObservation
from manobal_core.ingest.contract import (
    identity_person,
    strip_identifiers,
    validate_envelope,
    validate_features,
)
from manobal_core.ingest.identity import TokeniseClient
from manobal_core.ingest.quality import record_hrms_quality
from manobal_core.ingest.transfer import apply_posting_change


def ingest_hrms_batch(
    *,
    source_system: str,
    contract_version: str,
    records: list[dict[str, Any]],
    identity: TokeniseClient,
) -> IngestBatch:
    """Ingest one extract. Returns the batch row describing what happened."""
    digest = _digest(source_system, contract_version, records)
    reason = validate_envelope(contract_version)
    if reason is not None:
        return IngestBatch.objects.create(
            source_system=source_system,
            contract_version=contract_version,
            payload_digest=digest,
            record_count=len(records),
            status="rejected",
            error_summary=reason,
        )

    people = [person for record in records if (person := identity_person(record))]
    tokens = identity.tokenise(people) if people else {}

    with transaction.atomic():
        batch = IngestBatch.objects.create(
            source_system=source_system,
            contract_version=contract_version,
            payload_digest=digest,
            record_count=len(records),
            status="validated",
        )
        accepted = 0
        quarantined = 0
        for record in records:
            person = identity_person(record)
            service_no = str(record.get("service_no") or "")
            token = tokens.get(service_no) if person is not None else None
            payload = strip_identifiers(record)
            feature_reason = validate_features(payload)
            if token is None:
                _quarantine(batch, None, "not_tokenised", payload)
                quarantined += 1
                continue
            if feature_reason is not None:
                _quarantine(batch, token, feature_reason, payload)
                quarantined += 1
                continue
            _apply_row(token, payload, batch.id)
            accepted += 1

        batch.accepted_count = accepted
        batch.quarantined_count = quarantined
        batch.status = "applied"
        batch.save(update_fields=["accepted_count", "quarantined_count", "status"])
        record_hrms_quality(batch)

    AuditEvent.record(
        actor_id="ingest-worker",
        actor_role=Role.INTEGRATION,
        action=AuditAction.IDENTITY_TOKENISE,
        purpose_code=PurposeCode.DATA_INGESTION,
        legal_basis=LegalBasis.EMPLOYMENT,
        outcome="success",
        detail={"batch_id": batch.id, "tokenised": len(tokens)},
    )
    return batch


def _apply_row(token: str, payload: dict[str, Any], batch_id: int) -> None:
    unit = _unit_of(payload)
    existing = Subject.objects.filter(subject_token=token).first()
    employment = str(payload.get("employment_status") or "").lower()
    apply_posting_change(existing, new_unit=unit, employment_status=employment)
    subject, _ = Subject.objects.update_or_create(
        subject_token=token,
        defaults={
            "unit": unit,
            "force_code": str(payload.get("force_code") or unit.force_code),
            "rank_band": str(payload.get("rank_band") or "unknown"),
            "service_years_bucket": str(payload.get("service_years_bucket") or "unknown"),
        },
    )
    if employment == "separated":
        from manobal_core.erasure.separation import mark_separated

        mark_separated(subject)
    observed = date.fromisoformat(str(payload["observed_on"]))
    hours = _optional_float(payload.get("duty_hours"))
    DutyObservation.objects.update_or_create(
        subject_token=token,
        observed_on=observed,
        defaults={
            "duty_hours": hours,
            "duty_hours_7d": hours,
            "night_duty": bool(payload.get("night_duty")),
            "consecutive_duty_days": int(payload.get("consecutive_duty_days") or 0),
            "high_alert_posting": bool(payload.get("high_alert_posting")),
            "location_changes_30d": int(payload.get("location_changes_30d") or 0),
            "source_batch_id": batch_id,
        },
    )
    _refresh_duty_window(token, observed)
    LeaveObservation.objects.update_or_create(
        subject_token=token,
        observed_on=observed,
        defaults={
            "days_since_last_leave": _optional_int(payload.get("days_since_last_leave")),
            "leave_denied_count_90d": int(payload.get("leave_denied_count_90d") or 0),
            "leave_deferred_days": int(payload.get("leave_deferred_days") or 0),
            "pending_leave_application": bool(payload.get("pending_leave_application")),
            "home_distance_band": str(payload.get("home_distance_band") or ""),
            "source_batch_id": batch_id,
        },
    )


def _unit_of(payload: dict[str, Any]) -> Unit:
    code = str(payload.get("unit_code") or "")
    unit = Unit.objects.filter(code=code).first()
    if unit is not None:
        return unit
    path = str(payload.get("unit_path") or code)
    force = str(payload.get("force_code") or "")
    return Unit.objects.create(
        code=code or "UNKNOWN",
        name=code or "Unknown unit",
        force_code=force,
        depth=path.count("/"),
        path=path,
    )


def _quarantine(
    batch: IngestBatch, token: str | None, reason: str, payload: dict[str, Any]
) -> None:
    QuarantinedRecord.objects.create(
        batch=batch,
        subject_token=token,
        reason_code=reason,
        reason_detail=reason,
        payload=payload,
    )


def _digest(source: str, version: str, records: list[dict[str, Any]]) -> str:
    encoded = json.dumps(
        {"source": source, "version": version, "records": records},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(encoded.encode()).hexdigest()


def _refresh_duty_window(token: str, observed: date) -> None:
    """Recompute every trailing window that includes ``observed``.

    A day's ``duty_hours_7d`` is the sum of hours on that day and the six
    before it. Ingesting ``observed`` therefore changes the window for
    ``observed`` itself and for any later day within six days — a late
    backfill must not leave those later totals stale.
    """
    latest = observed + timedelta(days=6)
    affected = DutyObservation.objects.filter(
        subject_token=token,
        observed_on__gte=observed,
        observed_on__lte=latest,
    ).values_list("observed_on", flat=True)
    for day in affected:
        start = day - timedelta(days=6)
        total = DutyObservation.objects.filter(
            subject_token=token,
            observed_on__gte=start,
            observed_on__lte=day,
        ).aggregate(total=Sum("duty_hours"))["total"]
        DutyObservation.objects.filter(subject_token=token, observed_on=day).update(
            duty_hours_7d=total
        )


def _optional_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise TypeError(f"duty hours must be numeric, not {type(value).__name__}")
    return float(value)


def _optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise TypeError(f"count must be an integer, not {type(value).__name__}")
    return int(value)
