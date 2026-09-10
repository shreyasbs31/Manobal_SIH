"""One path across personnel, officer, and clinical desks.

The remaining-product slices were built separately. This test is the seam:
consent → journal → instrument → contest → disclosure → trend → clinical
referral. A medical officer can open the referred case and cannot close it.
"""

from __future__ import annotations

import pytest

from manobal_core.apps.governance.enums import CaseStatus, DataType
from manobal_core.apps.governance.models import (
    ConsentEntry,
    ConsentTextVersion,
    OfficerProfile,
    Subject,
)
from manobal_core.scoring.orchestrator import persist_assessment
from manobal_risk.types import Tier as EngineTier

from .scoring_helpers import engine_assessment
from .test_core_api import client_for, medical_officer, personnel_of

pytestmark = pytest.mark.django_db(databases=["default", "psy"])

PHQ9_MILD = [1, 1, 1, 1, 1, 1, 1, 1, 0]


class TestCrossDeskFlow:
    def test_personnel_officer_and_clinical_desks_hand_off(
        self,
        subject: Subject,
        officer: OfficerProfile,
        officer_principal,
        consent_text: ConsentTextVersion,
        unit_tree,
    ) -> None:
        del officer
        for data_type in (DataType.JOURNAL, DataType.SELF_REPORT):
            ConsentEntry.objects.create(
                subject_token=subject.subject_token,
                data_type=data_type,
                granted=True,
                consent_text=consent_text,
            )
        personnel = client_for(personnel_of(subject))
        welfare = client_for(officer_principal)
        _profile, medical = medical_officer(unit_tree)
        clinical = client_for(medical)

        journal = personnel.post("/v1/me/journal", {"body": "a private sentence"}, format="json")
        assert journal.status_code == 201
        assert journal.json()["body"] == "a private sentence"
        assert welfare.get("/v1/me/journal").status_code == 403

        instrument = personnel.post(
            "/v1/me/instruments",
            {
                "code": "phq9",
                "language": "en",
                "answers": PHQ9_MILD,
                "duration_seconds": 90,
            },
            format="json",
        )
        assert instrument.status_code == 201
        assert instrument.json()["acute"] is False
        assert "answers" not in instrument.json()

        opened = persist_assessment(
            engine_assessment(subject.subject_token, tier=EngineTier.T3), subject
        )
        assert opened.case is not None

        contested = personnel.post(
            f"/v1/me/cases/{opened.case.id}/contest",
            {"note": "this flag does not describe my situation"},
            format="json",
        )
        assert contested.status_code == 200
        assert contested.json()["status"] == CaseStatus.CONTESTED

        asked = welfare.post(
            f"/v1/officer/cases/{opened.case.id}/disclosure",
            {"category": "workload_and_duty", "rationale": "need the recent pattern"},
            format="json",
        )
        assert asked.status_code == 201
        granted = personnel.post(
            f"/v1/me/disclosures/{asked.json()['id']}",
            {"granted": True},
            format="json",
        )
        assert granted.status_code == 200
        trend = welfare.get(
            f"/v1/officer/cases/{opened.case.id}/trend",
            {"category": "workload_and_duty"},
        )
        assert trend.status_code == 200
        assert "wsi" not in trend.json()
        assert trend.json()["points"][0]["present"] is True

        referred = welfare.post(
            f"/v1/officer/cases/{opened.case.id}/refer-clinical",
            {"medical_actor_id": "medical-001", "rationale": "clinical review of a T3"},
            format="json",
        )
        assert referred.status_code == 201
        assert referred.json()["assigned"] is False

        queue = clinical.get("/v1/clinical/queue")
        assert queue.status_code == 200
        assert opened.case.id in [row["id"] for row in queue.json()["cases"]]
        detail = clinical.get(f"/v1/officer/cases/{opened.case.id}")
        assert detail.status_code == 200
        assert detail.json()["contested_at"]
        closed = clinical.post(
            f"/v1/officer/cases/{opened.case.id}/decision",
            {"outcome_code": "consulted", "rationale": "clinical note"},
            format="json",
        )
        assert closed.status_code == 403
        opened.case.refresh_from_db()
        assert opened.case.assigned_officer_id != "medical-001"
        assert opened.case.status == CaseStatus.CONTESTED
