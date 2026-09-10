"""A medical officer is a T3/T4 consultant. They are never the case assignee."""

from __future__ import annotations

import pytest

from manobal_core.apps.governance.enums import GrantScope
from manobal_core.apps.governance.models import AccessGrant, Case, OfficerProfile, Subject
from manobal_core.scoring.orchestrator import persist_assessment
from manobal_risk.types import Tier as EngineTier

from .scoring_helpers import engine_assessment
from .test_core_api import client_for, medical_officer

pytestmark = pytest.mark.django_db


class TestClinicalReferral:
    def test_a_t2_case_cannot_be_referred(
        self, subject: Subject, officer: OfficerProfile, officer_principal, unit_tree
    ) -> None:
        del officer
        opened = persist_assessment(
            engine_assessment(subject.subject_token, tier=EngineTier.T2), subject
        )
        assert opened.case is not None
        medical_officer(unit_tree)
        response = client_for(officer_principal).post(
            f"/v1/officer/cases/{opened.case.id}/refer-clinical",
            {"medical_actor_id": "medical-001", "rationale": "needs a consult"},
            format="json",
        )
        assert response.status_code == 422
        assert AccessGrant.objects.filter(scope=GrantScope.CLINICAL_REFERRAL).count() == 0

    def test_referral_does_not_reassign_the_case(
        self, subject: Subject, officer: OfficerProfile, officer_principal, unit_tree
    ) -> None:
        opened = persist_assessment(
            engine_assessment(subject.subject_token, tier=EngineTier.T3), subject
        )
        assert opened.case is not None
        assert opened.case.assigned_officer_id == officer.actor_id
        _profile, medical = medical_officer(unit_tree)
        referred = client_for(officer_principal).post(
            f"/v1/officer/cases/{opened.case.id}/refer-clinical",
            {"medical_actor_id": "medical-001", "rationale": "clinical review of a T3"},
            format="json",
        )
        assert referred.status_code == 201
        assert referred.json()["assigned"] is False
        opened.case.refresh_from_db()
        assert opened.case.assigned_officer_id == officer.actor_id
        grant = AccessGrant.objects.get(scope=GrantScope.CLINICAL_REFERRAL)
        assert grant.grantee_id == "medical-001"
        assert grant.case_id == opened.case.id

        empty = client_for(medical).get("/v1/clinical/queue")
        assert empty.status_code == 200
        ids = [row["id"] for row in empty.json()["cases"]]
        assert opened.case.id in ids
        assert Case.objects.get(pk=opened.case.id).assigned_officer_id != "medical-001"
        detail = client_for(medical).get(f"/v1/officer/cases/{opened.case.id}")
        assert detail.status_code == 200
        assert detail.json()["id"] == opened.case.id
        closed = client_for(medical).post(
            f"/v1/officer/cases/{opened.case.id}/decision",
            {"outcome_code": "consulted", "rationale": "clinical note"},
            format="json",
        )
        assert closed.status_code == 403
