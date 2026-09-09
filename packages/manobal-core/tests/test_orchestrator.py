"""The scoring orchestrator: settle, persist, open a case (FR-3.3, §4.5).

The engine emits a tier. This module is where that tier meets governance:
withdrawal settling, an immutable assessment row, and — only at T2 and above,
and only when coverage is enough — a case and a fourteen-day grant.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from manobal_core.apps.governance.enums import CaseStatus, DataType, LegalBasis, Tier
from manobal_core.apps.governance.models import (
    MAX_GRANT_DAYS,
    Case,
    ConsentEntry,
    ConsentTextVersion,
    OfficerProfile,
    RiskAssessmentRecord,
    Subject,
)
from manobal_core.scoring.orchestrator import persist_assessment
from manobal_core.scoring.settling import SettlingReason
from manobal_risk.types import Domain
from manobal_risk.types import Tier as EngineTier

from .scoring_helpers import engine_assessment

pytestmark = pytest.mark.django_db

WORKLOAD = "workload_and_duty"
LEAVE = "leave_and_time_off"
SLEEP = "sleep_and_recovery"
MOOD = "self_reported_wellbeing"

FOUR_DOMAINS = frozenset(
    {Domain.WORKLOAD, Domain.LEAVE, Domain.PHYSIOLOGICAL, Domain.SELF_REPORT}
)
TWO_DOMAINS = frozenset({Domain.WORKLOAD, Domain.LEAVE})


class TestPersistAndCase:
    def test_a_t1_assessment_is_stored_and_opens_no_case(
        self, subject: Subject, officer: OfficerProfile
    ) -> None:
        del officer
        result = persist_assessment(
            engine_assessment(subject.subject_token, tier=EngineTier.T1, categories=(WORKLOAD,)),
            subject,
        )
        assert result.assessment.tier == Tier.T1
        assert result.case is None
        assert result.grant is None
        assert Case.objects.count() == 0

    def test_a_t2_assessment_opens_a_case_and_a_fourteen_day_grant(
        self, subject: Subject, officer: OfficerProfile
    ) -> None:
        result = persist_assessment(
            engine_assessment(subject.subject_token, tier=EngineTier.T2),
            subject,
        )
        assert result.case is not None
        assert result.grant is not None
        assert result.case.assigned_officer_id == officer.actor_id
        assert result.case.tier_at_open == Tier.T2
        assert result.grant.legal_basis == LegalBasis.CONSENT
        span = result.grant.expires_at - result.grant.granted_at
        assert span <= timedelta(days=MAX_GRANT_DAYS)
        assert span >= timedelta(days=MAX_GRANT_DAYS) - timedelta(seconds=2)

    def test_a_second_elevated_run_does_not_open_another_case(
        self, subject: Subject, officer: OfficerProfile
    ) -> None:
        del officer
        first = persist_assessment(
            engine_assessment(subject.subject_token, tier=EngineTier.T2),
            subject,
        )
        later = timezone.now() + timedelta(hours=1)
        second = persist_assessment(
            engine_assessment(subject.subject_token, tier=EngineTier.T3, assessed_at=later),
            subject,
        )
        assert Case.objects.count() == 1
        assert second.case is not None
        assert first.case is not None
        assert second.case.pk == first.case.pk
        assert second.grant is None
        first.assessment.refresh_from_db()
        assert first.assessment.superseded_by_id == second.assessment.pk

    def test_t4_uses_vital_interest_as_the_grant_basis(
        self, subject: Subject, officer: OfficerProfile
    ) -> None:
        del officer
        result = persist_assessment(
            engine_assessment(
                subject.subject_token,
                tier=EngineTier.T4,
                acute=True,
                categories=(SLEEP,),
            ),
            subject,
        )
        assert result.grant is not None
        assert result.grant.legal_basis == LegalBasis.VITAL_INTEREST
        assert result.assessment.acute_override is True

    def test_insufficient_coverage_persists_and_opens_no_case(
        self, subject: Subject, officer: OfficerProfile
    ) -> None:
        del officer
        result = persist_assessment(
            engine_assessment(
                subject.subject_token,
                tier=EngineTier.T3,
                insufficient=True,
            ),
            subject,
        )
        assert result.assessment.tier == Tier.T3
        assert result.case is None
        assert Case.objects.filter(status=CaseStatus.OPEN).count() == 0

    def test_the_stored_row_has_no_score_fields(
        self, subject: Subject, officer: OfficerProfile
    ) -> None:
        del officer
        result = persist_assessment(
            engine_assessment(subject.subject_token, tier=EngineTier.T2),
            subject,
        )
        names = {field.name for field in result.assessment._meta.get_fields()}
        assert "wsi" not in names
        assert "score" not in names


class TestWithdrawalSettling:
    def test_a_coverage_only_rise_is_clamped_and_opens_no_case(
        self, subject: Subject, officer: OfficerProfile, consent_text: ConsentTextVersion
    ) -> None:
        del officer
        persist_assessment(
            engine_assessment(
                subject.subject_token,
                tier=EngineTier.T1,
                categories=(WORKLOAD, LEAVE),
                covered=FOUR_DOMAINS,
            ),
            subject,
        )
        ConsentEntry.objects.create(
            subject_token=subject.subject_token,
            data_type=DataType.BIOMETRIC,
            granted=False,
            consent_text=consent_text,
        )
        later = timezone.now() + timedelta(minutes=5)
        result = persist_assessment(
            engine_assessment(
                subject.subject_token,
                tier=EngineTier.T3,
                categories=(WORKLOAD, LEAVE),
                covered=TWO_DOMAINS,
                assessed_at=later,
            ),
            subject,
        )
        assert result.settling.clamped is True
        assert result.settling.reason is SettlingReason.COVERAGE_ONLY_INCREASE
        assert result.assessment.tier == Tier.T1
        assert result.assessment.pre_gate_tier == Tier.T3
        assert result.case is None
        assert RiskAssessmentRecord.objects.filter(
            subject_token=subject.subject_token, tier=Tier.T3
        ).count() == 0
