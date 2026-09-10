"""FR-7.4: after separation, purge the analytics stores once the statutory wait ends.

The consent ledger, the audit chain and published aggregates stay. Those are the
system's memory of itself. The person's observations do not.
"""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from manobal_core.apps.governance.enums import (
    AuditAction,
    ErasureStatus,
    LegalBasis,
    PurposeCode,
    Role,
    SubjectStatus,
)
from manobal_core.apps.governance.models import (
    AccessGrant,
    AuditEvent,
    ErasureRequest,
    Subject,
)
from manobal_core.erasure.saga import advance_erasure


def mark_separated(subject: Subject, *, now=None) -> Subject:
    """Record separation and close every live window onto this person."""
    moment = now or timezone.now()
    if subject.status == SubjectStatus.SEPARATED and subject.separated_at:
        return subject
    subject.status = SubjectStatus.SEPARATED
    subject.separated_at = moment
    subject.save(update_fields=["status", "separated_at", "updated_at"])
    AccessGrant.objects.filter(
        subject_token=subject.subject_token, revoked_at__isnull=True
    ).update(revoked_at=moment)
    AuditEvent.record(
        actor_id="manobal-ingest",
        actor_role=Role.INTEGRATION,
        action=AuditAction.ADMIN_ACTION,
        subject_token=subject.subject_token,
        purpose_code=PurposeCode.ERASURE,
        legal_basis=LegalBasis.LEGAL_OBLIGATION,
        outcome="success",
        detail={"event": "subject.separated"},
    )
    return subject


def due_for_purge(*, now=None) -> list[Subject]:
    moment = now or timezone.now()
    days = int(settings.PRIVACY["SEPARATION_PURGE_DAYS"])
    cutoff = moment - timedelta(days=days)
    return list(
        Subject.objects.filter(
            status=SubjectStatus.SEPARATED, separated_at__lte=cutoff
        ).order_by("separated_at", "subject_token")
    )


def purge_separated(*, now=None) -> int:
    """Open and advance a full erasure for every subject past the wait."""
    finished = 0
    for subject in due_for_purge(now=now):
        existing = (
            ErasureRequest.objects.filter(
                subject_token=subject.subject_token, data_type__isnull=True
            )
            .order_by("-requested_at", "-id")
            .first()
        )
        if existing is not None and existing.status == ErasureStatus.COMPLETED:
            continue
        request = existing or ErasureRequest.objects.create(
            subject_token=subject.subject_token,
            data_type=None,
            status=ErasureStatus.INTENT_RECORDED,
        )
        done = advance_erasure(request)
        if done.status == ErasureStatus.COMPLETED:
            finished += 1
    return finished
