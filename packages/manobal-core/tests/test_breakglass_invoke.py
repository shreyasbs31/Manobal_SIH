"""WDEC may break glass. Zone 2 must forget the name the moment it is shown."""

from __future__ import annotations

import pytest

from manobal_core.apps.governance.models import AccessGrant, OfficerProfile, Subject
from manobal_core.identity.breakglass import ResolvedPerson, configure_breakglass
from manobal_core.scoring.orchestrator import persist_assessment
from manobal_risk.types import Tier as EngineTier

from .scoring_helpers import engine_assessment
from .test_core_api import client_for, wdec_principal

pytestmark = pytest.mark.django_db


class FakeBreakGlass:
    def break_glass(self, assertion: str) -> ResolvedPerson:
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


class TestBreakGlassInvoke:
    def test_a_second_approver_is_required(
        self, subject: Subject, officer: OfficerProfile
    ) -> None:
        del officer
        opened = persist_assessment(
            engine_assessment(subject.subject_token, tier=EngineTier.T4, acute=True),
            subject,
        )
        assert opened.case is not None
        configure_breakglass(FakeBreakGlass())
        try:
            response = client_for(wdec_principal()).post(
                "/v1/wdec/break-glass",
                {"case_id": opened.case.id, "justification": "emergency"},
                format="json",
            )
        finally:
            configure_breakglass(None)
        assert response.status_code == 422

    def test_the_caller_cannot_approve_themselves(
        self, subject: Subject, officer: OfficerProfile
    ) -> None:
        del officer
        opened = persist_assessment(
            engine_assessment(subject.subject_token, tier=EngineTier.T4, acute=True),
            subject,
        )
        assert opened.case is not None
        configure_breakglass(FakeBreakGlass())
        try:
            response = client_for(wdec_principal()).post(
                "/v1/wdec/break-glass",
                {
                    "case_id": opened.case.id,
                    "justification": "emergency",
                    "second_approver_id": "wdec-001",
                },
                format="json",
            )
        finally:
            configure_breakglass(None)
        assert response.status_code == 422

    def test_identity_is_returned_and_not_stored(
        self, subject: Subject, officer: OfficerProfile
    ) -> None:
        del officer
        opened = persist_assessment(
            engine_assessment(subject.subject_token, tier=EngineTier.T4, acute=True),
            subject,
        )
        assert opened.case is not None
        configure_breakglass(FakeBreakGlass())
        try:
            response = client_for(wdec_principal()).post(
                "/v1/wdec/break-glass",
                {
                    "case_id": opened.case.id,
                    "justification": "missing person, welfare concern",
                    "second_approver_id": "wdec-chair",
                },
                format="json",
            )
        finally:
            configure_breakglass(None)
        assert response.status_code == 200
        assert response.json()["service_no"] == "CRPF-1999-000001"
        assert response["Cache-Control"] == "no-store"
        stored = " ".join(str(row) for row in AccessGrant.objects.filter(case=opened.case))
        assert "CRPF-1999" not in stored
        assert "Constable Test" not in stored

    def test_the_daily_ceiling_is_two(
        self, subject: Subject, officer: OfficerProfile
    ) -> None:
        del officer
        opened = persist_assessment(
            engine_assessment(subject.subject_token, tier=EngineTier.T4, acute=True),
            subject,
        )
        assert opened.case is not None
        configure_breakglass(FakeBreakGlass())
        client = client_for(wdec_principal())
        payload = {
            "case_id": opened.case.id,
            "justification": "emergency",
            "second_approver_id": "wdec-chair",
        }
        try:
            first = client.post("/v1/wdec/break-glass", payload, format="json")
            payload["second_approver_id"] = "wdec-chair-2"
            second = client.post("/v1/wdec/break-glass", payload, format="json")
            payload["second_approver_id"] = "wdec-chair-3"
            third = client.post("/v1/wdec/break-glass", payload, format="json")
        finally:
            configure_breakglass(None)
        assert first.status_code == 200
        assert second.status_code == 200
        assert third.status_code == 429
        assert third.json()["code"] == "MB-4290"

    def test_a_failed_resolve_revokes_the_grant(
        self, subject: Subject, officer: OfficerProfile
    ) -> None:
        del officer

        class Boom:
            def break_glass(self, assertion: str) -> ResolvedPerson:
                del assertion
                raise RuntimeError("zone 3 unavailable")

        opened = persist_assessment(
            engine_assessment(subject.subject_token, tier=EngineTier.T4, acute=True),
            subject,
        )
        assert opened.case is not None
        configure_breakglass(Boom())
        try:
            response = client_for(wdec_principal()).post(
                "/v1/wdec/break-glass",
                {
                    "case_id": opened.case.id,
                    "justification": "emergency",
                    "second_approver_id": "wdec-chair",
                },
                format="json",
            )
        finally:
            configure_breakglass(None)
        assert response.status_code == 500
        leftover = AccessGrant.objects.filter(case=opened.case, break_glass=True)
        assert leftover.exists()
        assert all(row.revoked_at is not None for row in leftover)
