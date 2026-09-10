"""WDEC sees bands and an audit browser. Commanders see neither route."""

from __future__ import annotations

import json

import pytest
from django.conf import settings
from django.test import override_settings

from manobal_core.apps.governance.enums import LegalBasis, PurposeCode, Role
from manobal_core.apps.governance.models import AuditEvent, OfficerProfile, Subject, Unit
from manobal_core.scoring.orchestrator import persist_assessment
from manobal_risk.types import Tier as EngineTier

from .scoring_helpers import engine_assessment, make_subjects
from .test_core_api import client_for, commander_of, wdec_principal

pytestmark = pytest.mark.django_db


def _privacy(*, k: int) -> dict[str, object]:
    return {**settings.PRIVACY, "K_ANONYMITY_THRESHOLD": k}


class TestFairness:
    def test_cells_below_k_are_suppressed_and_tokens_never_appear(
        self, unit_tree: dict[str, Unit], officer: OfficerProfile
    ) -> None:
        del officer
        unit = unit_tree["company"]
        cohort = make_subjects(unit, 3, established=True)
        for person in cohort:
            persist_assessment(
                engine_assessment(person.subject_token, tier=EngineTier.T2), person
            )
        lone = Subject.objects.create(
            subject_token="tok_officer_band",
            unit=unit,
            force_code=unit.force_code,
            rank_band="officer",
            service_years_bucket="15-19",
        )
        persist_assessment(engine_assessment(lone.subject_token, tier=EngineTier.T2), lone)

        with override_settings(PRIVACY=_privacy(k=3)):
            response = client_for(wdec_principal()).get(
                "/v1/wdec/fairness", {"unit": unit.code}
            )
        assert response.status_code == 200
        body = response.json()
        rendered = json.dumps(body)
        assert "tok_" not in rendered
        assert "subject_token" not in rendered
        cells = {cell["rank_band"]: cell for cell in body["cells"]}
        assert cells["constable"]["suppressed"] is False
        assert cells["officer"]["suppressed"] is True
        assert "elevated_band" not in cells["officer"]

    def test_unassessed_people_count_toward_k(
        self, unit_tree: dict[str, Unit], officer: OfficerProfile
    ) -> None:
        del officer
        unit = unit_tree["company"]
        cohort = make_subjects(unit, 5, established=True)
        persist_assessment(
            engine_assessment(cohort[0].subject_token, tier=EngineTier.T2), cohort[0]
        )
        with override_settings(PRIVACY=_privacy(k=5)):
            response = client_for(wdec_principal()).get(
                "/v1/wdec/fairness", {"unit": unit.code}
            )
        assert response.status_code == 200
        cell = response.json()["cells"][0]
        assert cell["suppressed"] is False
        assert cell["elevated_band"] == "1-4"

    def test_a_parent_unit_includes_its_companies(
        self, unit_tree: dict[str, Unit], officer: OfficerProfile
    ) -> None:
        del officer
        company = unit_tree["company"]
        cohort = make_subjects(company, 5, established=True)
        persist_assessment(
            engine_assessment(cohort[0].subject_token, tier=EngineTier.T2), cohort[0]
        )
        with override_settings(PRIVACY=_privacy(k=5)):
            response = client_for(wdec_principal()).get(
                "/v1/wdec/fairness", {"unit": unit_tree["battalion"].code}
            )
        assert response.status_code == 200
        cell = response.json()["cells"][0]
        assert cell["suppressed"] is False
        sibling = client_for(wdec_principal()).get(
            "/v1/wdec/fairness", {"unit": unit_tree["sibling"].code}
        )
        assert sibling.status_code == 200
        assert sibling.json()["cells"] == []

    def test_a_commander_cannot_read_fairness(
        self, unit_tree: dict[str, Unit]
    ) -> None:
        response = client_for(commander_of(unit_tree["company"])).get(
            "/v1/wdec/fairness", {"unit": unit_tree["company"].code}
        )
        assert response.status_code == 403


class TestAuditBrowser:
    def test_detail_is_allow_listed_and_tokens_may_appear(
        self, subject: Subject, unit_tree: dict[str, Unit]
    ) -> None:
        AuditEvent.record(
            actor_id="officer-001",
            actor_role=Role.WELFARE_OFFICER,
            action="data.individual_read",
            purpose_code=PurposeCode.CASE_REVIEW,
            legal_basis=LegalBasis.CONSENT,
            outcome="success",
            subject_token=subject.subject_token,
            detail={"event": "case.read", "full_name": "Must Not Leak", "case_id": 9},
        )
        response = client_for(wdec_principal()).get("/v1/wdec/audit")
        assert response.status_code == 200
        event = response.json()["events"][0]
        assert event["subject_token"] == subject.subject_token
        assert event["detail"] == {"event": "case.read", "case_id": 9}
        assert "Must Not Leak" not in response.content.decode()

        forbidden = client_for(commander_of(unit_tree["company"])).get("/v1/wdec/audit")
        assert forbidden.status_code == 403
