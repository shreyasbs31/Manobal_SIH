"""HRMS ingest: tokenise at the boundary, never persist an identifier (FR-2.3, FR-2.4).

A duty roster can fail validation and still contain a service number. If that
number reached ``org_store`` or even the quarantine table, the analytics plane
would hold the one field the whole architecture exists to keep out. Tokenisation
therefore happens before any Zone 2 write, and the allow-list of what may be
stored is the enforcement — not a deny-list someone can forget to update.
"""

from __future__ import annotations

from datetime import date

import pytest
from rest_framework.test import APIClient

from manobal_core.apps.authz.principal import Principal
from manobal_core.apps.governance.enums import Role
from manobal_core.apps.governance.models import QuarantinedRecord, Subject
from manobal_core.apps.orgstore.models import DutyObservation, LeaveObservation
from manobal_core.ingest.contract import (
    HRMS_CONTRACT,
    IDENTIFYING_FIELDS,
    strip_identifiers,
    validate_envelope,
    validate_features,
)
from manobal_core.ingest.identity import configure_identity
from manobal_core.ingest.pipeline import ingest_hrms_batch

pytestmark = pytest.mark.django_db(databases=["default", "org"])


class FakeIdentity:
    def __init__(self) -> None:
        self.calls: list[list[dict[str, str]]] = []

    def tokenise(self, people: list[dict[str, str]]) -> dict[str, str]:
        self.calls.append(people)
        return {person["service_no"]: f"st_{person['service_no'][-6:]}" for person in people}


def hrms_row(service_no: str = "CRPF-1999-000001", **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "service_no": service_no,
        "full_name": "Constable Test",
        "rank_code": "CT",
        "mobile_e164": "+919800000001",
        "unit_code": "12BN_A",
        "unit_path": "CENTRAL/12BN/12BN_A",
        "force_code": "CAPF",
        "enrolled_on": "2020-01-15",
        "rank_band": "constable",
        "service_years_bucket": "5-9",
        "observed_on": "2026-09-08",
        "duty_hours": 10.5,
        "night_duty": False,
        "consecutive_duty_days": 3,
        "high_alert_posting": False,
        "location_changes_30d": 1,
        "days_since_last_leave": 40,
        "leave_denied_count_90d": 1,
        "leave_deferred_days": 0,
        "pending_leave_application": False,
        "home_distance_band": "200-400",
    }
    row.update(overrides)
    return row


class TestContract:
    def test_the_supported_contract_is_accepted(self) -> None:
        assert validate_envelope(HRMS_CONTRACT) is None

    def test_an_unknown_contract_is_rejected(self) -> None:
        assert validate_envelope("hrms-9.9") == "unknown_contract_version"

    def test_identifiers_are_stripped_for_storage(self) -> None:
        stored = strip_identifiers(hrms_row())
        assert IDENTIFYING_FIELDS.isdisjoint(stored)
        assert stored["observed_on"] == "2026-09-08"
        assert stored["duty_hours"] == 10.5

    def test_a_negative_duty_hour_is_invalid(self) -> None:
        assert validate_features(strip_identifiers(hrms_row(duty_hours=-1))) == "invalid_duty_hours"

    def test_a_missing_observation_date_is_invalid(self) -> None:
        row = strip_identifiers(hrms_row())
        del row["observed_on"]
        assert validate_features(row) == "missing_observed_on"


class TestPipeline:
    def test_an_unknown_contract_rejects_the_batch_without_calling_identity(
        self, unit_tree: dict
    ) -> None:
        del unit_tree
        identity = FakeIdentity()
        batch = ingest_hrms_batch(
            source_system="hrms",
            contract_version="hrms-9.9",
            records=[hrms_row()],
            identity=identity,
        )
        assert batch.status == "rejected"
        assert identity.calls == []
        assert DutyObservation.objects.count() == 0

    def test_a_valid_row_is_tokenised_then_stored_without_identifiers(
        self, unit_tree: dict
    ) -> None:
        del unit_tree
        identity = FakeIdentity()
        batch = ingest_hrms_batch(
            source_system="hrms",
            contract_version=HRMS_CONTRACT,
            records=[hrms_row()],
            identity=identity,
        )
        assert batch.status == "applied"
        assert batch.accepted_count == 1
        assert batch.quarantined_count == 0
        assert identity.calls and identity.calls[0][0]["service_no"] == "CRPF-1999-000001"

        duty = DutyObservation.objects.get()
        assert duty.subject_token == "st_000001"
        assert duty.observed_on == date(2026, 9, 8)
        assert duty.duty_hours == 10.5
        assert duty.duty_hours_7d == 10.5
        leave = LeaveObservation.objects.get()
        assert leave.leave_denied_count_90d == 1

        subject = Subject.objects.get(pk="st_000001")
        assert subject.unit_id == "12BN_A"
        assert subject.rank_band == "constable"
        names = {field.name for field in duty._meta.get_fields()}
        assert names.isdisjoint(IDENTIFYING_FIELDS)
        dumped = str(duty.__dict__)
        assert "CRPF-" not in dumped
        assert "Constable" not in dumped

    def test_a_bad_feature_is_quarantined_under_the_token_not_the_service_number(
        self, unit_tree: dict
    ) -> None:
        del unit_tree
        identity = FakeIdentity()
        batch = ingest_hrms_batch(
            source_system="hrms",
            contract_version=HRMS_CONTRACT,
            records=[hrms_row(duty_hours=-8)],
            identity=identity,
        )
        assert batch.status == "applied"
        assert batch.accepted_count == 0
        assert batch.quarantined_count == 1
        held = QuarantinedRecord.objects.get()
        assert held.subject_token == "st_000001"
        assert held.reason_code == "invalid_duty_hours"
        assert IDENTIFYING_FIELDS.isdisjoint(held.payload)
        assert "CRPF-" not in str(held.payload)
        assert DutyObservation.objects.count() == 0

    def test_a_redelivery_of_the_same_day_updates_rather_than_duplicating(
        self, unit_tree: dict
    ) -> None:
        del unit_tree
        identity = FakeIdentity()
        ingest_hrms_batch(
            source_system="hrms",
            contract_version=HRMS_CONTRACT,
            records=[hrms_row(duty_hours=8)],
            identity=identity,
        )
        ingest_hrms_batch(
            source_system="hrms",
            contract_version=HRMS_CONTRACT,
            records=[hrms_row(duty_hours=12)],
            identity=identity,
        )
        assert DutyObservation.objects.count() == 1
        assert DutyObservation.objects.get().duty_hours == 12
        assert DutyObservation.objects.get().duty_hours_7d == 12

    def test_duty_hours_7d_is_the_trailing_week_not_the_day(
        self, unit_tree: dict
    ) -> None:
        del unit_tree
        identity = FakeIdentity()
        ingest_hrms_batch(
            source_system="hrms",
            contract_version=HRMS_CONTRACT,
            records=[hrms_row(observed_on="2026-09-02", duty_hours=8)],
            identity=identity,
        )
        ingest_hrms_batch(
            source_system="hrms",
            contract_version=HRMS_CONTRACT,
            records=[hrms_row(observed_on="2026-09-08", duty_hours=10.5)],
            identity=identity,
        )
        day = DutyObservation.objects.get(observed_on=date(2026, 9, 8))
        assert day.duty_hours == 10.5
        assert day.duty_hours_7d == 18.5
        earlier = DutyObservation.objects.get(observed_on=date(2026, 9, 2))
        assert earlier.duty_hours_7d == 8

        ingest_hrms_batch(
            source_system="hrms",
            contract_version=HRMS_CONTRACT,
            records=[hrms_row(observed_on="2026-09-01", duty_hours=4)],
            identity=identity,
        )
        outside = DutyObservation.objects.get(observed_on=date(2026, 9, 1))
        assert outside.duty_hours_7d == 4
        # 1 September sits inside 2 September's window, not 8 September's.
        assert DutyObservation.objects.get(observed_on=date(2026, 9, 2)).duty_hours_7d == 12
        assert DutyObservation.objects.get(observed_on=date(2026, 9, 8)).duty_hours_7d == 18.5

        ingest_hrms_batch(
            source_system="hrms",
            contract_version=HRMS_CONTRACT,
            records=[hrms_row(observed_on="2026-09-05", duty_hours=6)],
            identity=identity,
        )
        assert DutyObservation.objects.get(observed_on=date(2026, 9, 8)).duty_hours_7d == 24.5


class TestIngestHttp:
    def test_only_the_integration_role_may_post_an_extract(self, unit_tree: dict) -> None:
        del unit_tree
        client = APIClient()
        client.force_authenticate(
            user=Principal(
                actor_id="officer-001",
                role=Role.WELFARE_OFFICER,
                force_code="CAPF",
                unit_code="12BN",
                auth_methods=frozenset({"pwd", "otp"}),
            )
        )
        response = client.post(
            "/v1/ingest/hrms",
            {"contract_version": "hrms-1.0", "records": [hrms_row()]},
            format="json",
        )
        assert response.status_code == 403

    def test_the_integration_worker_receives_counts_not_identifiers(
        self, unit_tree: dict
    ) -> None:
        del unit_tree
        identity = FakeIdentity()
        configure_identity(identity)
        try:
            client = APIClient()
            client.force_authenticate(
                user=Principal(
                    actor_id="ingest-worker",
                    role=Role.INTEGRATION,
                    force_code="CAPF",
                )
            )
            response = client.post(
                "/v1/ingest/hrms",
                {"source_system": "hrms", "contract_version": "hrms-1.0", "records": [hrms_row()]},
                format="json",
            )
        finally:
            configure_identity(None)
        assert response.status_code == 202
        body = response.json()
        assert body["accepted"] == 1
        assert "Constable" not in response.content.decode()
        assert "CRPF-" not in response.content.decode()


class TestIdentityClientIsolation:
    def test_the_ingest_package_does_not_import_the_enclave(self) -> None:
        import ast
        from pathlib import Path

        import manobal_core.ingest.identity as client_mod
        import manobal_core.ingest.pipeline as pipeline_mod

        assert "manobal_identity" not in client_mod.__dict__
        assert "manobal_identity" not in pipeline_mod.__dict__
        for module in (client_mod, pipeline_mod):
            assert module.__file__ is not None
            tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
            imported: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module)
            assert not any(name.startswith("manobal_identity") for name in imported)
