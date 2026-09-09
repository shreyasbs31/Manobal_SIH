"""T4 that nobody picked up becomes a call to the next officer (NFR-P6).

Fifteen minutes is the whole SLA. After that the original recipient still holds
the case — we do not reassign — but one more person is told, by voice, that an
urgent item is waiting. The body is still the lock-screen sentence. Escalation
is one individual, never a broadcast, and it is recorded on the row that timed
out so the WDEC can see the chain.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone

from manobal_core.alerting.bodies import assert_minimised, lock_screen_body
from manobal_core.alerting.transport import InProcessTransport, apply_send
from manobal_core.apps.governance.enums import (
    AlertChannel,
    AuditAction,
    CaseStatus,
    DeliveryStatus,
    LegalBasis,
    PurposeCode,
    Role,
    Tier,
)
from manobal_core.apps.governance.models import AlertDispatch, AuditEvent, Case, OfficerProfile


def escalate_unacknowledged(*, now: datetime | None = None) -> list[AlertDispatch]:
    """Create one voice follow-up per timed-out T4 push. Returns what was queued."""
    moment = now or timezone.now()
    raw_sla = settings.ALERTING["ACUTE_DISPATCH_SLA_MINUTES"]
    if not isinstance(raw_sla, int):
        raise TypeError("ACUTE_DISPATCH_SLA_MINUTES must be an int")
    sla = timedelta(minutes=raw_sla)
    cutoff = moment - sla
    stale = (
        AlertDispatch.objects.filter(
            tier=Tier.T4,
            channel=AlertChannel.PUSH,
            acknowledged_at__isnull=True,
            escalated_to__isnull=True,
            sent_at__lte=cutoff,
            status__in={DeliveryStatus.SENT, DeliveryStatus.DELIVERED},
        )
        .select_related("case", "case__unit", "case__assigned_officer")
        .order_by("sent_at", "id")
    )
    created: list[AlertDispatch] = []
    for source in stale:
        follow = _escalate_one(source, moment)
        if follow is not None:
            created.append(follow)
    return created


def _escalate_one(source: AlertDispatch, moment: datetime) -> AlertDispatch | None:
    case = source.case
    if case.status not in {CaseStatus.OPEN, CaseStatus.CONTACTED, CaseStatus.CONTESTED}:
        return None
    nxt = _next_officer(case, exclude=source.recipient_id)
    if nxt is None:
        return None
    body = lock_screen_body(Tier.T4)
    assert_minimised(body)
    follow = AlertDispatch.objects.create(
        case=case,
        recipient_id=nxt.actor_id,
        recipient_role=nxt.role,
        channel=AlertChannel.VOICE,
        tier=Tier.T4,
        body=body,
        queued_at=moment,
        dedupe_key=f"esc:{source.pk}:{nxt.actor_id}",
    )
    apply_send(follow, InProcessTransport().send(follow))
    AlertDispatch.objects.filter(pk=source.pk).update(escalated_to=follow)
    AuditEvent.record(
        actor_id="manobal-alert",
        actor_role=Role.INTEGRATION,
        action=AuditAction.ALERT_DISPATCH,
        subject_token=case.subject_token,
        purpose_code=PurposeCode.ACUTE_RESPONSE,
        legal_basis=LegalBasis.VITAL_INTEREST,
        outcome="success",
        detail={"case_id": case.id, "channel": AlertChannel.VOICE, "escalated_from": source.pk},
    )
    return follow


def _next_officer(case: Case, *, exclude: str) -> OfficerProfile | None:
    path = case.unit.path
    candidates = [
        profile
        for profile in OfficerProfile.objects.filter(
            force_code=case.unit.force_code,
            role=Role.WELFARE_OFFICER,
            is_active=True,
        ).select_related("unit")
        if profile.may_receive_cases
        and profile.actor_id != exclude
        and (path == profile.unit.path or path.startswith(f"{profile.unit.path}/"))
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda profile: profile.actor_id)
