"""Intervention lookup and dual-approval of a ruleset (§4.5, §10.5)."""

from __future__ import annotations

import pytest

from manobal_core.apps.governance.enums import Role
from manobal_core.apps.governance.models import (
    InterventionRecommendation,
    RulesetProposal,
    RulesetVersion,
    Subject,
)
from manobal_core.interventions.lookup import propose_for_case
from manobal_core.ruleset.registry import approve_proposal, register_proposal
from manobal_core.scoring.orchestrator import persist_assessment
from manobal_risk.types import Tier as EngineTier

from .scoring_helpers import engine_assessment

pytestmark = pytest.mark.django_db


def test_a_new_case_receives_catalogue_recommendations(
    subject: Subject, officer
) -> None:
    del officer
    result = persist_assessment(
        engine_assessment(subject.subject_token, tier=EngineTier.T2),
        subject,
    )
    assert result.case is not None
    codes = set(
        InterventionRecommendation.objects.filter(case=result.case).values_list("code", flat=True)
    )
    assert codes
    assert "rest_day_review" in codes or "welfare_check_in" in codes
    again = propose_for_case(result.case)
    assert again == []


def test_a_ruleset_is_not_registered_until_both_approvers_sign() -> None:
    proposal = register_proposal(
        version="1.0.1-test",
        digest="b" * 64,
        signature="sig",
        signing_key_id="ruleset-dev",
        proposed_by="wdec-001",
        shadow_report={"flag_rate_delta": 0.01},
    )
    approve_proposal(proposal, actor_id="medical-001", role=Role.MEDICAL_OFFICER)
    proposal.refresh_from_db()
    assert proposal.status == "pending"
    assert RulesetVersion.objects.filter(version="1.0.1-test").count() == 0
    approve_proposal(proposal, actor_id="wdec-001", role=Role.WDEC_AUDITOR)
    proposal.refresh_from_db()
    assert proposal.status == "registered"
    version = RulesetVersion.objects.get(version="1.0.1-test")
    assert version.approved_by_clinical == "medical-001"
    assert version.approved_by_wdec == "wdec-001"
    assert RulesetProposal.objects.filter(pk=proposal.pk).exists()
