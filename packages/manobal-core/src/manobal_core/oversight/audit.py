"""WDEC audit browser. Tokens are pseudonymous; names never appear."""

from __future__ import annotations

from datetime import datetime

from manobal_core.apps.governance.models import AuditEvent

MAX_LIMIT = 100
SAFE_DETAIL_KEYS = frozenset(
    {
        "event",
        "tier",
        "case_id",
        "count",
        "unit",
        "reason",
        "data_type",
        "granted",
        "action",
        "status",
        "suppressed",
        "receipt_id",
        "accepted",
        "crisis",
        "batch",
        "batch_id",
    }
)


def list_audit(
    *,
    action: str = "",
    after: datetime | None = None,
    before: datetime | None = None,
    limit: int = 50,
) -> list[dict[str, object]]:
    capped = min(max(limit, 1), MAX_LIMIT)
    rows = AuditEvent.objects.all().order_by("-occurred_at", "-id")
    if action:
        rows = rows.filter(action=action)
    if after is not None:
        rows = rows.filter(occurred_at__gte=after)
    if before is not None:
        rows = rows.filter(occurred_at__lte=before)
    return [_public(row) for row in rows[:capped]]


def _public(row: AuditEvent) -> dict[str, object]:
    detail = row.detail if isinstance(row.detail, dict) else {}
    return {
        "id": row.id,
        "occurred_at": row.occurred_at.isoformat(),
        "actor_role": row.actor_role,
        "action": row.action,
        "purpose_code": row.purpose_code,
        "outcome": row.outcome,
        "subject_token": row.subject_token,
        "detail": {key: detail[key] for key in SAFE_DETAIL_KEYS if key in detail},
    }
