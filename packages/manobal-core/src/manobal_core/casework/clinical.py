"""Refer a T3/T4 case to a medical officer. They are never the assignee."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from manobal_core.apps.governance.enums import MEDICAL_OFFICER_TIERS, GrantScope, LegalBasis, Role
from manobal_core.apps.governance.models import MAX_GRANT_DAYS, AccessGrant, Case, OfficerProfile


class ClinicalRefused(ValueError):  # noqa: N818
    """The case is not clinical, or the target is not a medical officer."""


def refer_clinical(case: Case, *, medical_actor_id: str, rationale: str) -> AccessGrant:
    """Open a time-boxed clinical grant. Does not reassign the welfare case."""
    if case.tier_at_open not in MEDICAL_OFFICER_TIERS:
        raise ClinicalRefused("clinical referral is only for T3 and T4")
    if case.assigned_officer_id == medical_actor_id:
        raise ClinicalRefused("a medical officer is not a case assignee")
    profile = OfficerProfile.objects.filter(actor_id=medical_actor_id).first()
    if profile is None or profile.role != Role.MEDICAL_OFFICER:
        raise ClinicalRefused("referral target must be a medical officer")
    if not profile.may_receive_cases:
        raise ClinicalRefused("medical officer is not currently certified")
    reason = rationale.strip()
    if not reason:
        raise ClinicalRefused("rationale is required")
    now = timezone.now()
    return AccessGrant.objects.create(
        subject_token=case.subject_token,
        grantee_id=profile.actor_id,
        grantee_role=Role.MEDICAL_OFFICER,
        scope=GrantScope.CLINICAL_REFERRAL,
        case=case,
        granted_at=now,
        expires_at=now + timedelta(days=MAX_GRANT_DAYS),
        subject_consented=False,
        legal_basis=(
            LegalBasis.VITAL_INTEREST if case.tier_at_open == "T4" else LegalBasis.CONSENT
        ),
        justification=reason[:1000],
    )


def clinical_queue(medical_actor_id: str) -> list[Case]:
    live = AccessGrant.objects.filter(
        grantee_id=medical_actor_id,
        scope=GrantScope.CLINICAL_REFERRAL,
        revoked_at__isnull=True,
        expires_at__gt=timezone.now(),
    ).values_list("case_id", flat=True)
    return list(
        Case.objects.filter(id__in=live, tier_at_open__in=MEDICAL_OFFICER_TIERS)
        .select_related("unit", "assessment")
        .order_by("sla_due_at", "id")
    )
