"""Advance one erasure request, store by store, and resume after a crash."""

from __future__ import annotations

import logging
from collections.abc import Callable

from django.utils import timezone

from manobal_core.apps.governance.enums import (
    AuditAction,
    ErasureStatus,
    LegalBasis,
    PurposeCode,
    Role,
)
from manobal_core.apps.governance.models import AuditEvent, ErasureRequest
from manobal_core.erasure.receipt import issue_receipt
from manobal_core.erasure.stores import PURGERS, revoke_live_grants, stores_for

logger = logging.getLogger(__name__)


def advance_erasure(request: ErasureRequest) -> ErasureRequest:
    """Purge remaining stores for ``request``. Safe to call again after a crash."""
    if request.status == ErasureStatus.COMPLETED:
        return request
    targets = stores_for(request.data_type)
    progress = dict(request.store_progress)
    for store in targets:
        progress.setdefault(store, "pending")
    request.status = ErasureStatus.IN_PROGRESS
    request.attempts = request.attempts + 1
    request.store_progress = progress
    request.last_error = ""
    request.save(update_fields=["status", "attempts", "store_progress", "last_error"])

    for store in targets:
        if progress.get(store) == "completed":
            continue
        purger = cast_purger(PURGERS[store])
        try:
            purger(request)
        except Exception as exc:
            request.status = ErasureStatus.FAILED
            request.last_error = str(exc)
            request.store_progress = progress
            request.save(update_fields=["status", "last_error", "store_progress"])
            raise
        progress[store] = "completed"
        request.store_progress = dict(progress)
        request.save(update_fields=["store_progress"])

    revoke_live_grants(request)
    receipt_id, signature = issue_receipt(request)
    request.status = ErasureStatus.COMPLETED
    request.completed_at = timezone.now()
    request.receipt_id = receipt_id
    request.receipt_signature = signature
    request.save(
        update_fields=[
            "status",
            "completed_at",
            "receipt_id",
            "receipt_signature",
            "store_progress",
        ]
    )
    AuditEvent.record(
        actor_id="manobal-erasure",
        actor_role=Role.INTEGRATION,
        action=AuditAction.ERASURE_COMPLETE,
        subject_token=request.subject_token,
        purpose_code=PurposeCode.ERASURE,
        legal_basis=LegalBasis.SUBJECT_REQUEST,
        outcome="success",
        detail={"receipt_id": receipt_id, "data_type": request.data_type},
    )
    return request


def resume_pending() -> int:
    """Advance every request that is not yet complete. Returns how many finished."""
    pending = ErasureRequest.objects.filter(
        status__in={ErasureStatus.INTENT_RECORDED, ErasureStatus.IN_PROGRESS, ErasureStatus.FAILED}
    ).order_by("requested_at", "id")
    finished = 0
    for request in pending:
        try:
            done = advance_erasure(request)
        except Exception:
            logger.exception("erasure resume failed", extra={"erasure_id": request.id})
            continue
        if done.status == ErasureStatus.COMPLETED:
            finished += 1
    return finished


def cast_purger(fn: object) -> Callable[[ErasureRequest], None]:
    if not callable(fn):
        raise TypeError("store purger is not callable")
    return fn
