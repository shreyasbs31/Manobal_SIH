"""Route one case to one officer per channel, then stop (FR-6.1, FR-6.5).

A persisting T2 must not page someone every night. The dedupe key is
``(subject, tier, ruleset, ISO week, channel, recipient)`` so a second scoring
run in the same week is a no-op, and a new week or a new tier is a new
decision. T4 adds SMS beside push, and may add one medical officer — still as
an individual recipient, never a list or a broadcast.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from datetime import datetime, timedelta

from django.db import IntegrityError
from django.utils import timezone

from manobal_core.alerting.bodies import assert_minimised, lock_screen_body
from manobal_core.alerting.transport import AlertTransport, InProcessTransport, apply_send
from manobal_core.apps.governance.enums import (
    AlertChannel,
    AuditAction,
    DeliveryStatus,
    GrantScope,
    LegalBasis,
    PurposeCode,
    Role,
    Tier,
)
from manobal_core.apps.governance.models import (
    MAX_GRANT_DAYS,
    AccessGrant,
    AlertDispatch,
    AuditEvent,
    Case,
    OfficerProfile,
    RiskAssessmentRecord,
)


def dispatch_for_case(
    case: Case,
    *,
    assessment: RiskAssessmentRecord | None = None,
    now: datetime | None = None,
    transport: AlertTransport | None = None,
) -> list[AlertDispatch]:
    """Queue the tier-appropriate channels for ``case``. Idempotent within the week."""
    if case.assigned_officer_id is None:
        return []
    tier = Tier(assessment.tier) if assessment is not None else Tier(case.tier_at_open)
    if tier in {Tier.T0, Tier.T1}:
        return []
    moment = now or timezone.now()
    carrier = transport or InProcessTransport()
    record = assessment or case.assessment
    body = lock_screen_body(tier)
    assert_minimised(body)
    created: list[AlertDispatch] = []
    for recipient_id, role, channel in _plan(case, tier):
        row = _queue(
            case,
            recipient_id=recipient_id,
            role=role,
            channel=channel,
            tier=tier,
            body=body,
            ruleset_version=record.ruleset_version,
            moment=moment,
        )
        if row is None:
            continue
        apply_send(row, carrier.send(row))
        _grant_if_needed(case, recipient_id, role, tier, moment)
        AuditEvent.record(
            actor_id="manobal-alert",
            actor_role=Role.INTEGRATION,
            action=AuditAction.ALERT_DISPATCH,
            subject_token=case.subject_token,
            purpose_code=(
                PurposeCode.ACUTE_RESPONSE if tier is Tier.T4 else PurposeCode.CASE_REVIEW
            ),
            legal_basis=(
                LegalBasis.VITAL_INTEREST if tier is Tier.T4 else LegalBasis.CONSENT
            ),
            outcome="success",
            detail={
                "case_id": case.id,
                "channel": channel,
                "recipient_role": role,
            },
        )
        created.append(row)
    return created


def acknowledge_case_alerts(case: Case, *, actor_id: str, now: datetime | None = None) -> int:
    """The officer has seen the item. Marks their queued/sent rows acknowledged."""
    moment = now or timezone.now()
    return AlertDispatch.objects.filter(
        case=case,
        recipient_id=actor_id,
        acknowledged_at__isnull=True,
    ).update(acknowledged_at=moment, status=DeliveryStatus.ACKNOWLEDGED)


def _plan(case: Case, tier: Tier) -> list[tuple[str, str, str]]:
    officer = case.assigned_officer
    assert officer is not None
    plan: list[tuple[str, str, str]] = []
    if tier is Tier.T2:
        plan.append((officer.actor_id, officer.role, AlertChannel.DIGEST))
    elif tier is Tier.T3:
        plan.append((officer.actor_id, officer.role, AlertChannel.PUSH))
    elif tier is Tier.T4:
        plan.append((officer.actor_id, officer.role, AlertChannel.PUSH))
        plan.append((officer.actor_id, officer.role, AlertChannel.SMS))
        medical = _one_medical_officer(case)
        if medical is not None:
            plan.append((medical.actor_id, medical.role, AlertChannel.PUSH))
    return plan


def _one_medical_officer(case: Case) -> OfficerProfile | None:
    """The single certified medical officer in the unit tree, or nobody.

    One person, not a distribution list. If two are equally eligible the
    actor id breaks the tie so the choice is stable across retries.
    """
    path = case.unit.path
    candidates = [
        profile
        for profile in OfficerProfile.objects.filter(
            force_code=case.unit.force_code,
            role=Role.MEDICAL_OFFICER,
            is_active=True,
        ).select_related("unit")
        if profile.may_receive_cases
        and (path == profile.unit.path or path.startswith(f"{profile.unit.path}/"))
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda profile: profile.actor_id)


def _queue(
    case: Case,
    *,
    recipient_id: str,
    role: str,
    channel: str,
    tier: Tier,
    body: str,
    ruleset_version: str,
    moment: datetime,
) -> AlertDispatch | None:
    key = _dedupe_key(
        subject_token=case.subject_token,
        tier=tier,
        ruleset_version=ruleset_version,
        channel=channel,
        recipient_id=recipient_id,
        moment=moment,
    )
    if AlertDispatch.objects.filter(dedupe_key=key).exists():
        return None
    try:
        return AlertDispatch.objects.create(
            case=case,
            recipient_id=recipient_id,
            recipient_role=role,
            channel=channel,
            tier=tier,
            body=body,
            queued_at=moment,
            dedupe_key=key,
        )
    except IntegrityError:
        return None


def _dedupe_key(
    *,
    subject_token: str,
    tier: Tier,
    ruleset_version: str,
    channel: str,
    recipient_id: str,
    moment: datetime,
) -> str:
    iso = moment.isocalendar()
    week = f"{iso.year}-W{iso.week:02d}"
    material = "|".join((subject_token, str(tier), ruleset_version, week, channel, recipient_id))
    return hashlib.sha256(material.encode()).hexdigest()


def _grant_if_needed(
    case: Case, recipient_id: str, role: str, tier: Tier, moment: datetime
) -> None:
    """A medical officer who is paged must hold a live flag grant to open the case."""
    if role != Role.MEDICAL_OFFICER:
        return
    live = AccessGrant.objects.filter(
        grantee_id=recipient_id,
        subject_token=case.subject_token,
        scope=GrantScope.FLAG,
        revoked_at__isnull=True,
        expires_at__gt=moment,
    ).exists()
    if live:
        return
    AccessGrant.objects.create(
        subject_token=case.subject_token,
        grantee_id=recipient_id,
        grantee_role=role,
        scope=GrantScope.FLAG,
        case=case,
        granted_at=moment,
        expires_at=moment + timedelta(days=MAX_GRANT_DAYS),
        subject_consented=False,
        legal_basis=LegalBasis.VITAL_INTEREST if tier is Tier.T4 else LegalBasis.CONSENT,
        justification=f"T4 escalation page at {tier}.",
    )


def recipients_of(rows: Iterable[AlertDispatch]) -> set[str]:
    return {row.recipient_id for row in rows}
