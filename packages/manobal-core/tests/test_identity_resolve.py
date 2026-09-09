"""Zone 2 may request a resolve; it may not remember the answer (§4.9)."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from manobal_core.apps.authz.principal import Principal
from manobal_core.apps.governance.enums import GrantScope
from manobal_core.apps.governance.models import AccessGrant, OfficerProfile, Subject
from manobal_core.identity.resolve import ResolvedPerson, configure_resolve
from manobal_core.scoring.orchestrator import persist_assessment
from manobal_risk.types import Tier as EngineTier

from .scoring_helpers import engine_assessment

pytestmark = pytest.mark.django_db


class FakeResolve:
    def resolve(self, assertion: str) -> ResolvedPerson:
        assert assertion.startswith("mbga1.")
        return ResolvedPerson(
            subject_token="tok_subject_0001",
            service_no="CRPF-1999-000001",
            full_name="Constable Test",
            rank_code="CT",
            mobile_e164="+919800000001",
            unit_code="12BN_A",
            force_code="CAPF",
        )


def test_t4_officer_receives_identity_and_zone2_does_not_store_it(
    subject: Subject, officer: OfficerProfile, officer_principal: Principal
) -> None:
    del officer
    result = persist_assessment(
        engine_assessment(subject.subject_token, tier=EngineTier.T4, acute=True),
        subject,
    )
    assert result.case is not None
    assert AccessGrant.objects.filter(
        case=result.case, scope=GrantScope.IDENTITY, grantee_id="officer-001"
    ).exists()
    configure_resolve(FakeResolve())
    try:
        client = APIClient()
        client.force_authenticate(user=officer_principal)
        response = client.post(f"/v1/officer/cases/{result.case.id}/resolve", {}, format="json")
    finally:
        configure_resolve(None)
    assert response.status_code == 200
    assert response.json()["service_no"] == "CRPF-1999-000001"
    assert response.get("Cache-Control") == "no-store"
    stored = " ".join(str(row) for row in AccessGrant.objects.filter(case=result.case))
    assert "CRPF-1999" not in stored
    assert "Constable Test" not in stored


def test_a_flag_grant_alone_cannot_resolve(
    subject: Subject, officer: OfficerProfile, officer_principal: Principal
) -> None:
    del officer
    result = persist_assessment(
        engine_assessment(subject.subject_token, tier=EngineTier.T2),
        subject,
    )
    assert result.case is not None
    client = APIClient()
    client.force_authenticate(user=officer_principal)
    response = client.post(f"/v1/officer/cases/{result.case.id}/resolve", {}, format="json")
    assert response.status_code == 403
