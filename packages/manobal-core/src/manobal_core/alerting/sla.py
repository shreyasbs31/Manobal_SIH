"""Re-surface open non-T4 cases after their SLA expires (FR-6.3)."""

from __future__ import annotations

from datetime import datetime

from django.utils import timezone

from manobal_core.alerting.dispatch import dispatch_for_case
from manobal_core.apps.governance.enums import CaseStatus, Tier
from manobal_core.apps.governance.models import AlertDispatch, Case

OPEN = {CaseStatus.OPEN, CaseStatus.CONTACTED, CaseStatus.CONTESTED}


def resurface_sla_breaches(*, now: datetime | None = None) -> list[AlertDispatch]:
    """Dispatch a second alert for open T2/T3 cases past ``sla_due_at``."""
    moment = now or timezone.now()
    cases = Case.objects.filter(
        status__in=OPEN,
        sla_due_at__lt=moment,
        tier_at_open__in={Tier.T2, Tier.T3},
    ).select_related("assessment", "assigned_officer", "unit")
    created: list[AlertDispatch] = []
    for case in cases:
        created.extend(dispatch_for_case(case, now=moment, reason="sla"))
    return created
