"""Closing the Phase 0 SDD gaps: transfer, incidents, rights, SLA, retention."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from manobal_core.alerting.destinations import destination_for, register_destination
from manobal_core.alerting.sla import resurface_sla_breaches
from manobal_core.apps.authz.principal import Principal
from manobal_core.apps.governance.enums import (
    AlertChannel,
    DataType,
    GrantScope,
    LegalBasis,
    Role,
    SubjectStatus,
)
from manobal_core.apps.governance.models import (
    AccessGrant,
    AlertDispatch,
    ConsentEntry,
    ConsentTextVersion,
    DataQualityReport,
    Subject,
    Unit,
)
from manobal_core.apps.psystore.models import CheckinResponse
from manobal_core.ingest.contract import HRMS_CONTRACT
from manobal_core.ingest.identity import configure_identity
from manobal_core.ingest.incidents import record_incident
from manobal_core.ingest.nightly import pull_nightly_hrms
from manobal_core.ingest.packets import normalize_capture_payload
from manobal_core.ingest.pipeline import ingest_hrms_batch
from manobal_core.journal.service import JournalRefused, write_entry
from manobal_core.retention import purge_raw_observations
from manobal_core.scoring.explain import why_flagged
from manobal_core.scoring.orchestrator import persist_assessment
from manobal_risk.types import Tier as EngineTier

from .scoring_helpers import engine_assessment
from .test_core_api import client_for, personnel_of, wdec_principal
from .test_ingest import FakeIdentity, hrms_row

pytestmark = pytest.mark.django_db(databases=["default", "org", "psy", "bio", "voice"])


def _integration() -> APIClient:
    client = APIClient()
    client.force_authenticate(
        user=Principal(actor_id="ingest-worker", role=Role.INTEGRATION, force_code="CAPF")
    )
    return client


class TestTransferRevokesGrants:
    def test_a_unit_change_revokes_live_grants(self, unit_tree: dict[str, Unit], officer) -> None:
        del officer
        identity = FakeIdentity()
        ingest_hrms_batch(
            source_system="hrms",
            contract_version=HRMS_CONTRACT,
            records=[hrms_row()],
            identity=identity,
        )
        token = "st_000001"
        AccessGrant.objects.create(
            subject_token=token,
            grantee_id="officer-001",
            grantee_role=Role.WELFARE_OFFICER,
            scope=GrantScope.FLAG,
            expires_at=timezone.now() + timedelta(days=7),
            legal_basis=LegalBasis.CONSENT,
            justification="open case",
        )
        ingest_hrms_batch(
            source_system="hrms",
            contract_version=HRMS_CONTRACT,
            records=[
                hrms_row(unit_code="12BN", unit_path="CENTRAL/12BN", observed_on="2026-09-09")
            ],
            identity=identity,
        )
        grant = AccessGrant.objects.get(subject_token=token)
        assert grant.revoked_at is not None
        assert Subject.objects.get(pk=token).unit_id == "12BN"
        assert Subject.objects.get(pk=token).status == SubjectStatus.ACTIVE


class TestIncidents:
    def test_an_incident_offers_a_checkin_on_assessment(
        self, subject: Subject, unit_tree: dict[str, Unit]
    ) -> None:
        record_incident(
            unit_code=unit_tree["company"].code,
            occurred_at=timezone.now(),
            category="casualty",
            external_id="ops-1",
        )
        response = client_for(personnel_of(subject)).get("/v1/me/assessment")
        assert response.status_code == 200
        assert response.json()["offer_checkin"] is True

    def test_the_integration_role_can_post_an_incident(
        self, unit_tree: dict[str, Unit]
    ) -> None:
        response = _integration().post(
            "/v1/integration/incidents",
            {
                "unit_code": unit_tree["company"].code,
                "occurred_at": timezone.now().isoformat(),
                "category": "high_intensity",
                "external_id": "ops-2",
            },
            format="json",
        )
        assert response.status_code == 202
        assert response.json()["window_hours"] == 72

    def test_health_reports_the_last_hrms_batch(self, unit_tree: dict[str, Unit]) -> None:
        del unit_tree
        identity = FakeIdentity()
        configure_identity(identity)
        try:
            _integration().post(
                "/v1/ingest/hrms",
                {"source_system": "hrms", "contract_version": "hrms-1.0", "records": [hrms_row()]},
                format="json",
            )
        finally:
            configure_identity(None)
        health = _integration().get("/v1/integration/health")
        assert health.status_code == 200
        assert health.json()["hrms"]["last_status"] == "applied"
        assert DataQualityReport.objects.filter(source_system="hrms").exists()


class TestRightsApis:
    def test_helpline_does_not_open_a_case(
        self, subject: Subject, officer, consent_text: ConsentTextVersion
    ) -> None:
        del officer, consent_text
        response = client_for(personnel_of(subject)).post("/v1/me/helpline", {}, format="json")
        assert response.status_code == 200
        assert response.json()["recorded"] is False
        assert "helplines" in response.json()
        assert subject.cases.count() == 0 if hasattr(subject, "cases") else True
        from manobal_core.apps.governance.models import Case

        assert Case.objects.filter(subject_token=subject.subject_token).count() == 0

    def test_ledger_and_erasure_and_trends(
        self, subject: Subject, consent_text: ConsentTextVersion
    ) -> None:
        ConsentEntry.objects.create(
            subject_token=subject.subject_token,
            data_type=DataType.SELF_REPORT,
            granted=True,
            consent_text=consent_text,
        )
        CheckinResponse.objects.create(
            subject_token=subject.subject_token,
            observed_on=timezone.localdate(),
            mood=3,
            fatigue=2,
        )
        client = client_for(personnel_of(subject))
        ledger = client.get("/v1/me/consent/ledger")
        assert ledger.status_code == 200
        assert ledger.json()["entries"]
        trends = client.get("/v1/me/trends")
        assert trends.status_code == 200
        assert trends.json()["checkins"][0]["fatigue"] == 2
        erased = client.post("/v1/me/erasure", {"data_type": "selfreport"}, format="json")
        assert erased.status_code == 202
        assert erased.json()["receipt_id"]

    def test_journal_pauses_at_t3(
        self, subject: Subject, officer, consent_text: ConsentTextVersion
    ) -> None:
        del officer
        ConsentEntry.objects.create(
            subject_token=subject.subject_token,
            data_type=DataType.JOURNAL,
            granted=True,
            consent_text=consent_text,
        )
        persist_assessment(engine_assessment(subject.subject_token, tier=EngineTier.T3), subject)
        with pytest.raises(JournalRefused, match="paused"):
            write_entry(subject, body="should not store")

    def test_personnel_can_delete_a_journal_entry(
        self, subject: Subject, consent_text: ConsentTextVersion
    ) -> None:
        ConsentEntry.objects.create(
            subject_token=subject.subject_token,
            data_type=DataType.JOURNAL,
            granted=True,
            consent_text=consent_text,
        )
        client = client_for(personnel_of(subject))
        created = client.post("/v1/me/journal", {"body": "a private sentence"}, format="json")
        assert created.status_code == 201
        deleted = client.delete(f"/v1/me/journal/{created.json()['id']}")
        assert deleted.status_code == 204
        listing = client.get("/v1/me/journal")
        assert listing.json()["entries"] == []


class TestBreakGlassReview:
    def test_review_closes_the_queue(self, subject: Subject, officer) -> None:
        del officer
        opened = persist_assessment(
            engine_assessment(subject.subject_token, tier=EngineTier.T4, acute=True),
            subject,
        )
        grant = AccessGrant.objects.create(
            subject_token=subject.subject_token,
            grantee_id="wdec-001",
            grantee_role=Role.WDEC_AUDITOR,
            scope=GrantScope.IDENTITY,
            case=opened.case,
            expires_at=timezone.now() + timedelta(days=1),
            legal_basis=LegalBasis.LEGAL_OBLIGATION,
            justification="review",
            break_glass=True,
        )
        response = client_for(wdec_principal()).post(
            f"/v1/wdec/break-glass/{grant.id}/review", {}, format="json"
        )
        assert response.status_code == 200
        grant.refresh_from_db()
        assert grant.wdec_reviewed_at is not None
        listing = client_for(wdec_principal()).get("/v1/wdec/break-glass")
        assert listing.json()["grants"] == []


class TestSlaAndRetention:
    def test_a_late_t2_is_re_alerted(self, subject: Subject, officer) -> None:
        del officer
        result = persist_assessment(
            engine_assessment(subject.subject_token, tier=EngineTier.T2),
            subject,
        )
        assert result.case is not None
        first = AlertDispatch.objects.filter(case=result.case).count()
        opened = result.case
        opened.sla_due_at = timezone.now() - timedelta(hours=1)
        opened.save(update_fields=["sla_due_at"])
        created = resurface_sla_breaches()
        assert created
        assert AlertDispatch.objects.filter(case=result.case).count() == first + len(created)

    def test_stale_checkins_are_purged(self, subject: Subject) -> None:
        CheckinResponse.objects.create(
            subject_token=subject.subject_token,
            observed_on=timezone.localdate() - timedelta(days=120),
            mood=2,
        )
        CheckinResponse.objects.create(
            subject_token=subject.subject_token,
            observed_on=timezone.localdate(),
            mood=3,
        )
        removed = purge_raw_observations()
        assert removed >= 1
        assert CheckinResponse.objects.filter(subject_token=subject.subject_token).count() == 1


class TestDestinationsAndAliases:
    def test_an_officer_registers_a_duty_phone(self, officer, officer_principal) -> None:
        del officer
        response = client_for(officer_principal).post(
            "/v1/officer/destination",
            {"duty_phone_e164": "+919812345678"},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["duty_phone_set"] is True
        assert response.json()["duty_phone_hint"] == "5678"
        assert destination_for("officer-001", AlertChannel.SMS) == "+919812345678"

    def test_push_uses_the_registered_token_not_the_actor_id(self, officer) -> None:
        register_destination(officer.actor_id, push_token="fcm-device-token")
        assert destination_for(officer.actor_id, AlertChannel.PUSH) == "fcm-device-token"
        assert destination_for(officer.actor_id, AlertChannel.PUSH) != officer.actor_id

    def test_the_sdd_api_prefix_serves_the_same_surface(
        self, subject: Subject
    ) -> None:
        response = client_for(personnel_of(subject)).get("/api/v1/me/assessment")
        assert response.status_code == 200
        assert "tier" in response.json()

    def test_why_flagged_names_domains_not_scores(self) -> None:
        rows = why_flagged(["workload_and_duty", "immediate_safety_indicator"])
        blob = " ".join(row["meaning"] for row in rows).lower()
        assert "wsi" not in blob
        assert "score" not in blob
        assert "z-score" not in blob

    def test_a_session_journal_expires(self, subject: Subject, consent_text) -> None:
        ConsentEntry.objects.create(
            subject_token=subject.subject_token,
            data_type=DataType.JOURNAL,
            granted=True,
            consent_text=consent_text,
        )
        row = write_entry(subject, body="keep tonight only", retain=False)
        assert row.expires_at is not None

    def test_nightly_hrms_is_a_no_op_without_a_url(self) -> None:
        assert pull_nightly_hrms() is None

    def test_a_capture_packet_is_normalised(self) -> None:
        body = normalize_capture_payload(
            {
                "subject_token": "st_000001",
                "packet_id": "pkt-1",
                "payload_type": "checkin",
                "payload": {"mood": 3, "fatigue": 2},
            }
        )
        assert body["client_batch_id"] == "pkt-1"
        assert body["items"][0]["kind"] == "checkin"
