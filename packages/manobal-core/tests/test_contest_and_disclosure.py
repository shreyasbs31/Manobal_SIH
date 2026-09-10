"""A person may contest a flag and answer a disclosure. Neither rewrites the score."""

from __future__ import annotations

import pytest
from django.utils import timezone

from manobal_core.apps.governance.enums import CaseStatus, DataType
from manobal_core.apps.governance.models import (
    ConsentEntry,
    ConsentTextVersion,
    DisclosureRequest,
    OfficerProfile,
    RiskAssessmentRecord,
    Subject,
)
from manobal_core.scoring.orchestrator import persist_assessment
from manobal_risk.types import Tier as EngineTier

from .scoring_helpers import engine_assessment
from .test_core_api import client_for, personnel_of

pytestmark = pytest.mark.django_db


def _open_case(subject: Subject, officer: OfficerProfile, *, tier: EngineTier = EngineTier.T2):
    del officer
    opened = persist_assessment(engine_assessment(subject.subject_token, tier=tier), subject)
    assert opened.case is not None
    return opened


class TestContest:
    def test_personnel_may_contest_their_own_open_case(
        self, subject: Subject, officer: OfficerProfile
    ) -> None:
        opened = _open_case(subject, officer)
        before = RiskAssessmentRecord.objects.get(pk=opened.assessment.id)
        response = client_for(personnel_of(subject)).post(
            f"/v1/me/cases/{opened.case.id}/contest",
            {"note": "this flag does not describe my situation"},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["status"] == CaseStatus.CONTESTED
        opened.case.refresh_from_db()
        assert opened.case.contest_note.startswith("this flag")
        after = RiskAssessmentRecord.objects.get(pk=opened.assessment.id)
        assert after.tier == before.tier
        assert after.contributing_categories == before.contributing_categories
        assert after.assessed_at == before.assessed_at

    def test_a_closed_case_cannot_be_contested(
        self, subject: Subject, officer: OfficerProfile
    ) -> None:
        opened = _open_case(subject, officer)
        opened.case.status = CaseStatus.RESOLVED
        opened.case.closed_at = timezone.now()
        opened.case.save(update_fields=["status", "closed_at"])
        response = client_for(personnel_of(subject)).post(
            f"/v1/me/cases/{opened.case.id}/contest",
            {"note": "too late"},
            format="json",
        )
        assert response.status_code == 422


class TestDisclosure:
    def test_an_unanswered_request_grants_nothing(
        self, subject: Subject, officer: OfficerProfile, officer_principal
    ) -> None:
        opened = _open_case(subject, officer)
        asked = client_for(officer_principal).post(
            f"/v1/officer/cases/{opened.case.id}/disclosure",
            {"category": "workload_and_duty", "rationale": "need the recent pattern"},
            format="json",
        )
        assert asked.status_code == 201
        assert asked.json()["granted"] is None
        row = DisclosureRequest.objects.get()
        assert row.granted is None
        trend = client_for(officer_principal).get(
            f"/v1/officer/cases/{opened.case.id}/trend",
            {"category": "workload_and_duty"},
        )
        assert trend.status_code == 403
        assert trend.json()["code"] == "MB-4032"

    def test_a_refusal_is_not_a_scoring_input(
        self,
        subject: Subject,
        officer: OfficerProfile,
        officer_principal,
        consent_text: ConsentTextVersion,
    ) -> None:
        ConsentEntry.objects.create(
            subject_token=subject.subject_token,
            data_type=DataType.ORG,
            granted=True,
            consent_text=consent_text,
        )
        opened = _open_case(subject, officer)
        asked = client_for(officer_principal).post(
            f"/v1/officer/cases/{opened.case.id}/disclosure",
            {"category": "workload_and_duty", "rationale": "need the recent pattern"},
            format="json",
        )
        before = RiskAssessmentRecord.objects.get(pk=opened.assessment.id)
        refused = client_for(personnel_of(subject)).post(
            f"/v1/me/disclosures/{asked.json()['id']}",
            {"granted": False},
            format="json",
        )
        assert refused.status_code == 200
        assert refused.json()["granted"] is False
        after = RiskAssessmentRecord.objects.get(pk=opened.assessment.id)
        assert after.tier == before.tier
        assert after.contributing_categories == before.contributing_categories
        trend = client_for(officer_principal).get(
            f"/v1/officer/cases/{opened.case.id}/trend",
            {"category": "workload_and_duty"},
        )
        assert trend.status_code == 403

    def test_a_grant_returns_presence_never_a_score(
        self, subject: Subject, officer: OfficerProfile, officer_principal
    ) -> None:
        opened = _open_case(subject, officer)
        asked = client_for(officer_principal).post(
            f"/v1/officer/cases/{opened.case.id}/disclosure",
            {"category": "workload_and_duty", "rationale": "need the recent pattern"},
            format="json",
        )
        client_for(personnel_of(subject)).post(
            f"/v1/me/disclosures/{asked.json()['id']}",
            {"granted": True},
            format="json",
        )
        trend = client_for(officer_principal).get(
            f"/v1/officer/cases/{opened.case.id}/trend",
            {"category": "workload_and_duty"},
        )
        assert trend.status_code == 200
        point = trend.json()["points"][0]
        assert set(point) == {"assessed_at", "tier_visible", "present"}
        assert point["present"] is True
        assert "score" not in trend.json()
        assert "wsi" not in trend.json()
