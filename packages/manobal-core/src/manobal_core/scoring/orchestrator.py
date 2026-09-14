"""Turn an engine result into a stored assessment, and maybe a case.

The engine is stateless and emits a tier. This module is where governance
state meets that tier: the withdrawal-settling policy, the immutable
assessment row, and the case that an officer will see. Nothing here computes
a Welfare Signal Index, and nothing here writes one down.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import cast

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from manobal_core.apps.governance.enums import (
    OFFICER_VISIBLE_TIERS,
    CaseStatus,
    GrantScope,
    LegalBasis,
    PurposeCode,
    Role,
    Tier,
)
from manobal_core.apps.governance.models import (
    MAX_GRANT_DAYS,
    AccessGrant,
    AuditEvent,
    Case,
    ConsentEntry,
    OfficerProfile,
    RiskAssessmentRecord,
    Subject,
)
from manobal_core.apps.governance.tiers import to_engine, to_stored
from manobal_core.scoring.settling import (
    ScoringOutcome,
    SettlingDecision,
    apply_withdrawal_settling,
)
from manobal_risk.types import DOMAIN_CATEGORY, RiskAssessment


@dataclass(frozen=True, slots=True)
class PersistResult:
    """What the orchestrator did. No numeric score."""

    assessment: RiskAssessmentRecord
    settling: SettlingDecision
    case: Case | None
    grant: AccessGrant | None


def persist_assessment(engine: RiskAssessment, subject: Subject) -> PersistResult:
    """Settle, write the assessment, and open a case when an officer must see it."""
    previous = (
        RiskAssessmentRecord.objects.filter(subject_token=subject.subject_token)
        .order_by("-assessed_at", "-id")
        .first()
    )
    last_withdrawal = (
        ConsentEntry.objects.filter(subject_token=subject.subject_token, granted=False)
        .order_by("-recorded_at", "-id")
        .values_list("recorded_at", flat=True)
        .first()
    )
    settling = apply_withdrawal_settling(
        current=_outcome_from_engine(engine),
        previous=_outcome_from_record(previous) if previous else None,
        last_withdrawal_at=last_withdrawal,
        now=engine.assessed_at,
    )
    acted = to_stored(settling.tier)
    case: Case | None = None
    grant: AccessGrant | None = None

    with transaction.atomic():
        record = RiskAssessmentRecord.objects.create(
            subject_token=subject.subject_token,
            assessed_at=engine.assessed_at,
            tier=acted,
            contributing_categories=list(engine.contributing_categories),
            ruleset_version=engine.ruleset_version,
            ruleset_digest=engine.ruleset_sha256,
            domains_present=_covered_names(engine),
            coverage=_participation(engine),
            acute_override=engine.acute_override,
            pre_gate_tier=to_stored(engine.tier_before_hysteresis),
        )
        if previous is not None:
            RiskAssessmentRecord.objects.filter(pk=previous.pk).update(superseded_by=record)

        AuditEvent.record(
            actor_id="manobal-risk",
            actor_role=Role.INTEGRATION,
            action="data.individual_read",
            subject_token=subject.subject_token,
            purpose_code=PurposeCode.WELFARE_ASSESSMENT,
            legal_basis=LegalBasis.CONSENT,
            outcome="success",
            detail={
                "event": "assessment.persisted",
                "tier": acted,
                "engine_tier": to_stored(engine.tier),
                "clamped": settling.clamped,
                "settling_reason": settling.reason.value,
            },
        )

        if not engine.insufficient_coverage and acted in OFFICER_VISIBLE_TIERS:
            case, grant = _open_case(subject, record, acted)

    if case is not None:
        from manobal_core.alerting.dispatch import dispatch_for_case

        dispatch_for_case(case, assessment=record)
        if acted is Tier.T4:
            _authorise_t4_resolution(case, timezone.now())
        if grant is not None:
            from manobal_core.interventions.lookup import propose_for_case

            propose_for_case(case)

    return PersistResult(assessment=record, settling=settling, case=case, grant=grant)


def _open_case(
    subject: Subject, assessment: RiskAssessmentRecord, tier: Tier
) -> tuple[Case, AccessGrant | None]:
    existing = (
        Case.objects.filter(
            subject_token=subject.subject_token,
            status__in={CaseStatus.OPEN, CaseStatus.CONTACTED, CaseStatus.CONTESTED},
        )
        .order_by("-opened_at")
        .first()
    )
    if existing is not None:
        return existing, None

    hours_by_tier = cast(dict[str, int], settings.ALERTING["SLA_HOURS_BY_TIER"])
    hours = hours_by_tier.get(str(tier), 48)
    now = timezone.now()
    officer = _assignable_officer(subject)
    case = Case.objects.create(
        subject_token=subject.subject_token,
        assessment=assessment,
        unit=subject.unit,
        tier_at_open=tier,
        contributing_categories=list(assessment.contributing_categories),
        assigned_officer=officer,
        sla_due_at=now + timedelta(hours=int(hours)),
    )
    grant = None
    if officer is not None:
        grant = AccessGrant.objects.create(
            subject_token=subject.subject_token,
            grantee_id=officer.actor_id,
            grantee_role=officer.role,
            scope=GrantScope.FLAG,
            case=case,
            granted_at=now,
            expires_at=now + timedelta(days=MAX_GRANT_DAYS),
            subject_consented=False,
            legal_basis=(
                LegalBasis.VITAL_INTEREST if tier is Tier.T4 else LegalBasis.CONSENT
            ),
            justification=f"Assigned welfare case at {tier}.",
        )
    return case, grant


def _assignable_officer(subject: Subject) -> OfficerProfile | None:
    """The certified officer with the lightest open caseload in the unit tree."""
    path = subject.unit.path
    candidates = [
        profile
        for profile in OfficerProfile.objects.filter(
            force_code=subject.force_code, is_active=True
        ).select_related("unit")
        if profile.may_receive_cases
        and profile.role == Role.WELFARE_OFFICER
        and (path == profile.unit.path or path.startswith(f"{profile.unit.path}/"))
    ]
    if not candidates:
        return None

    def load(profile: OfficerProfile) -> int:
        return Case.objects.filter(
            assigned_officer=profile,
            status__in={CaseStatus.OPEN, CaseStatus.CONTACTED, CaseStatus.CONTESTED},
        ).count()

    return min(candidates, key=lambda profile: (load(profile), profile.actor_id))


def _authorise_t4_resolution(case: Case, moment: datetime) -> None:
    """T4 is the one path that may resolve a token. The grant is the authorisation."""
    officer = case.assigned_officer
    if officer is None:
        return
    live = AccessGrant.objects.filter(
        case=case,
        grantee_id=officer.actor_id,
        scope=GrantScope.IDENTITY,
        revoked_at__isnull=True,
        expires_at__gt=moment,
    ).exists()
    if live:
        return
    AccessGrant.objects.create(
        subject_token=case.subject_token,
        grantee_id=officer.actor_id,
        grantee_role=officer.role,
        scope=GrantScope.IDENTITY,
        case=case,
        granted_at=moment,
        expires_at=moment + timedelta(days=MAX_GRANT_DAYS),
        subject_consented=False,
        legal_basis=LegalBasis.VITAL_INTEREST,
        justification="T4 acute path: identity resolution authorised.",
    )


def _covered_names(engine: RiskAssessment) -> list[str]:
    return [
        DOMAIN_CATEGORY[domain]
        for domain, covered in engine.domain_coverage
        if covered and domain in DOMAIN_CATEGORY
    ]


def _participation(engine: RiskAssessment) -> float:
    if not engine.domain_coverage:
        return 0.0
    present = sum(1 for _, covered in engine.domain_coverage if covered)
    return present / len(engine.domain_coverage)


def _outcome_from_engine(engine: RiskAssessment) -> ScoringOutcome:
    return ScoringOutcome(
        tier=engine.tier,
        breaching_categories=frozenset(engine.contributing_categories),
        covered_categories=frozenset(_covered_names(engine)),
        acute_override=engine.acute_override,
    )


def _outcome_from_record(record: RiskAssessmentRecord) -> ScoringOutcome:
    return ScoringOutcome(
        tier=to_engine(Tier(record.tier)),
        breaching_categories=frozenset(record.contributing_categories),
        covered_categories=frozenset(record.domains_present),
        acute_override=record.acute_override,
    )
