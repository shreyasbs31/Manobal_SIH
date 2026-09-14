"""The Zone 2 HTTP surface: who may call it, and what they may learn.

Role checks are the front door; predicates are the room-by-room lock. These
tests exercise both, and they pin the quiet properties that matter more than
the happy path: an unauthenticated caller gets 401, the wrong role gets 403,
a commander never sees a subject token, and a medical officer is not shown a T2.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from manobal_core.apps.authz.principal import Principal
from manobal_core.apps.governance.aggregation import ensure_aggregate
from manobal_core.apps.governance.enums import (
    DataType,
    GrantScope,
    LegalBasis,
    Role,
    Tier,
)
from manobal_core.apps.governance.models import (
    AccessGrant,
    AuditAnchor,
    Case,
    ConsentEntry,
    ConsentTextVersion,
    ErasureRequest,
    OfficerProfile,
    RiskAssessmentRecord,
    Subject,
    Unit,
)
from manobal_core.scoring.orchestrator import persist_assessment
from manobal_risk.types import Tier as EngineTier

from .scoring_helpers import engine_assessment, make_subjects

pytestmark = pytest.mark.django_db


def client_for(principal: Principal | None) -> APIClient:
    client = APIClient()
    if principal is not None:
        client.force_authenticate(user=principal)
    return client


def personnel_of(subject: Subject) -> Principal:
    return Principal(
        actor_id=subject.subject_token,
        role=Role.PERSONNEL,
        force_code=subject.force_code,
        unit_code=subject.unit_id,
        subject_token=subject.subject_token,
    )


def commander_of(unit: Unit) -> Principal:
    return Principal(
        actor_id="commander-001",
        role=Role.COMMANDER,
        force_code=unit.force_code,
        unit_code=unit.code,
        auth_methods=frozenset({"pwd", "otp"}),
    )


def wdec_principal() -> Principal:
    return Principal(
        actor_id="wdec-001",
        role=Role.WDEC_AUDITOR,
        force_code="CAPF",
        auth_methods=frozenset({"pwd", "otp"}),
    )


def medical_officer(unit_tree: dict[str, Unit]) -> tuple[OfficerProfile, Principal]:
    profile = OfficerProfile.objects.create(
        actor_id="medical-001",
        role=Role.MEDICAL_OFFICER,
        unit=unit_tree["battalion"],
        force_code="CAPF",
        training_valid_until=timezone.localdate() + timedelta(days=180),
    )
    principal = Principal(
        actor_id=profile.actor_id,
        role=Role.MEDICAL_OFFICER,
        force_code="CAPF",
        unit_code=unit_tree["battalion"].code,
        auth_methods=frozenset({"pwd", "otp"}),
    )
    return profile, principal


class TestAuthGates:
    def test_an_unauthenticated_caller_is_rejected(self) -> None:
        response = client_for(None).get("/v1/me/consent")
        assert response.status_code == 401
        assert response["Content-Type"] == "application/problem+json"
        assert response.json()["code"] == "MB-4010"

    def test_the_wrong_role_cannot_use_an_officer_endpoint(
        self, subject: Subject
    ) -> None:
        response = client_for(personnel_of(subject)).get("/v1/officer/queue")
        assert response.status_code == 403
        assert response.json()["code"] == "MB-4031"

    def test_a_commander_cannot_read_a_case(
        self, subject: Subject, officer: OfficerProfile, unit_tree: dict[str, Unit]
    ) -> None:
        del officer
        opened = persist_assessment(
            engine_assessment(subject.subject_token, tier=EngineTier.T2),
            subject,
        )
        assert opened.case is not None
        response = client_for(commander_of(unit_tree["battalion"])).get(
            f"/v1/officer/cases/{opened.case.id}"
        )
        assert response.status_code == 403
        assert response.json()["code"] == "MB-4031"


class TestConsentAndSelfAssessment:
    def test_personnel_can_grant_and_read_their_own_consent(
        self, subject: Subject, consent_text: ConsentTextVersion
    ) -> None:
        del consent_text
        client = client_for(personnel_of(subject))
        created = client.post(
            "/v1/me/consent",
            {"data_type": DataType.SELF_REPORT, "granted": True},
            format="json",
        )
        assert created.status_code == 201
        assert created.json()["granted"] is True
        listing = client.get("/v1/me/consent")
        assert listing.status_code == 200
        assert listing.json()["consents"][DataType.SELF_REPORT] is True
        assert listing.json()["subject_token"] == subject.subject_token

    def test_withdrawal_appends_the_ledger_and_records_erasure_intent(
        self, subject: Subject, consent_text: ConsentTextVersion
    ) -> None:
        del consent_text
        client = client_for(personnel_of(subject))
        client.post(
            "/v1/me/consent",
            {"data_type": DataType.BIOMETRIC, "granted": True},
            format="json",
        )
        withdrawn = client.post(
            "/v1/me/consent",
            {"data_type": DataType.BIOMETRIC, "granted": False},
            format="json",
        )
        assert withdrawn.status_code == 201
        assert ConsentEntry.objects.filter(
            subject_token=subject.subject_token, data_type=DataType.BIOMETRIC
        ).count() == 2
        assert ErasureRequest.objects.filter(
            subject_token=subject.subject_token, data_type=DataType.BIOMETRIC
        ).exists()

    def test_personnel_see_their_tier_and_category_names_only(
        self, subject: Subject, officer: OfficerProfile
    ) -> None:
        del officer
        persist_assessment(
            engine_assessment(subject.subject_token, tier=EngineTier.T2),
            subject,
        )
        response = client_for(personnel_of(subject)).get("/v1/me/assessment")
        assert response.status_code == 200
        body = response.json()
        assert body["tier"] == Tier.T2
        assert "workload_and_duty" in body["contributing_categories"]
        assert "wsi" not in body
        assert "score" not in body
        assert "coverage" not in body


class TestOfficerCasework:
    def test_the_assigned_officer_sees_the_queue_and_the_flag(
        self, subject: Subject, officer: OfficerProfile, officer_principal: Principal
    ) -> None:
        del officer
        opened = persist_assessment(
            engine_assessment(subject.subject_token, tier=EngineTier.T2),
            subject,
        )
        assert opened.case is not None
        client = client_for(officer_principal)
        queue = client.get("/v1/officer/queue")
        assert queue.status_code == 200
        assert len(queue.json()["cases"]) == 1
        assert queue.json()["cases"][0]["tier"] == Tier.T2
        assert queue.json()["cases"][0]["headline"]
        assert "wsi" not in queue.json()["cases"][0]["headline"].lower()
        detail = client.get(f"/v1/officer/cases/{opened.case.id}")
        assert detail.status_code == 200
        assert detail.json()["subject_token"] == subject.subject_token
        assert "wsi" not in detail.json()
        briefing = detail.json()["briefing"]
        assert briefing["headline"]
        assert briefing["openers"]
        assert "wsi" not in str(briefing).lower()
        assert "tok_" not in str(briefing)

    def test_contact_then_decision_closes_the_case_and_revokes_the_grant(
        self, subject: Subject, officer: OfficerProfile, officer_principal: Principal
    ) -> None:
        del officer
        opened = persist_assessment(
            engine_assessment(subject.subject_token, tier=EngineTier.T2),
            subject,
        )
        assert opened.case is not None
        client = client_for(officer_principal)
        contacted = client.post(f"/v1/officer/cases/{opened.case.id}/contact", {}, format="json")
        assert contacted.status_code == 200
        assert contacted.json()["status"] == "contacted"
        decided = client.post(
            f"/v1/officer/cases/{opened.case.id}/decision",
            {
                "outcome_code": "supported",
                "rationale": "Spoke with the individual; no further action.",
                "status": "no_action",
            },
            format="json",
        )
        assert decided.status_code == 200
        assert decided.json()["status"] == "no_action"
        assert decided.json()["officer_rationale"]
        case = Case.objects.get(pk=opened.case.id)
        assert case.closed_at is not None
        assert not AccessGrant.objects.filter(case=case, revoked_at__isnull=True).exists()

    def test_a_decision_without_a_rationale_is_rejected(
        self, subject: Subject, officer: OfficerProfile, officer_principal: Principal
    ) -> None:
        del officer
        opened = persist_assessment(
            engine_assessment(subject.subject_token, tier=EngineTier.T2),
            subject,
        )
        assert opened.case is not None
        response = client_for(officer_principal).post(
            f"/v1/officer/cases/{opened.case.id}/decision",
            {"outcome_code": "supported"},
            format="json",
        )
        assert response.status_code == 422
        assert response.json()["code"] == "MB-4220"

    def test_a_medical_officer_cannot_see_a_t2_case(
        self, subject: Subject, officer: OfficerProfile, unit_tree: dict[str, Unit]
    ) -> None:
        del officer
        opened = persist_assessment(
            engine_assessment(subject.subject_token, tier=EngineTier.T2),
            subject,
        )
        assert opened.case is not None
        _profile, medical = medical_officer(unit_tree)
        AccessGrant.objects.create(
            subject_token=subject.subject_token,
            grantee_id=medical.actor_id,
            grantee_role=Role.MEDICAL_OFFICER,
            scope=GrantScope.FLAG,
            case=opened.case,
            expires_at=timezone.now() + timedelta(days=7),
            legal_basis=LegalBasis.CONSENT,
            justification="Escalation review of an assigned case.",
        )
        client = client_for(medical)
        queue = client.get("/v1/officer/queue")
        assert queue.status_code == 200
        assert queue.json()["cases"] == []
        detail = client.get(f"/v1/officer/cases/{opened.case.id}")
        assert detail.status_code == 403
        assert detail.json()["code"] == "MB-4032"


class TestCommanderAggregates:
    def test_a_small_unit_returns_suppressed_without_counts(
        self, unit_tree: dict[str, Unit]
    ) -> None:
        response = client_for(commander_of(unit_tree["battalion"])).get(
            "/v1/commander/aggregates", {"unit": unit_tree["company"].code}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["suppressed"] is True
        assert "headcount" not in body
        assert "elevated_band" not in body
        assert "subject_token" not in body
        dumped = str(body)
        assert "tok_" not in dumped
        assert "wsi" not in dumped

    def test_a_stable_unit_returns_bands_never_tokens(
        self, unit_tree: dict[str, Unit]
    ) -> None:
        people = make_subjects(unit_tree["company"], 12, established=True)
        for person in people[:3]:
            RiskAssessmentRecord.objects.create(
                subject_token=person.subject_token,
                assessed_at=timezone.now(),
                tier=Tier.T2,
                contributing_categories=["sleep_and_recovery"],
                ruleset_version="1.0.0-test",
                ruleset_digest="c" * 64,
                domains_present=["sleep_and_recovery"],
                coverage=1.0,
                pre_gate_tier=Tier.T2,
            )
        # Warm the stored rollup so the request is a read of a decided outcome.
        ensure_aggregate(unit_tree["company"])
        response = client_for(commander_of(unit_tree["battalion"])).get(
            "/v1/commander/aggregates", {"unit": unit_tree["company"].code}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["suppressed"] is False
        assert body["elevated_band"] == "1-4"
        assert "subject_token" not in body
        assert "score" not in body

    def test_a_sibling_unit_is_outside_scope(self, unit_tree: dict[str, Unit]) -> None:
        response = client_for(commander_of(unit_tree["battalion"])).get(
            "/v1/commander/aggregates", {"unit": unit_tree["sibling"].code}
        )
        assert response.status_code == 403
        assert response.json()["code"] == "MB-4032"


class TestWdecOversight:
    def test_unreviewed_break_glass_grants_omit_the_token(
        self, subject: Subject, officer: OfficerProfile
    ) -> None:
        AccessGrant.objects.create(
            subject_token=subject.subject_token,
            grantee_id=officer.actor_id,
            grantee_role=Role.WELFARE_OFFICER,
            scope=GrantScope.IDENTITY,
            expires_at=timezone.now() + timedelta(days=1),
            legal_basis=LegalBasis.VITAL_INTEREST,
            justification="Emergency welfare contact after an acute alert.",
            break_glass=True,
        )
        response = client_for(wdec_principal()).get("/v1/wdec/break-glass")
        assert response.status_code == 200
        grants = response.json()["grants"]
        assert len(grants) == 1
        assert "subject_token" not in grants[0]
        assert subject.subject_token not in response.content.decode()
        assert grants[0]["justification"]

    def test_anchors_are_hashes_and_counts_only(self) -> None:
        AuditAnchor.objects.create(
            head_event_id=1,
            head_hash="d" * 64,
            event_count=12,
            published_to="file:/tmp/manobal-anchors.jsonl",
        )
        response = client_for(wdec_principal()).get("/v1/wdec/anchors")
        assert response.status_code == 200
        anchor = response.json()["anchors"][0]
        assert set(anchor) == {"anchored_at", "head_hash", "event_count", "published_to"}
        assert anchor["head_hash"] == "d" * 64
        assert "subject_token" not in response.json()
