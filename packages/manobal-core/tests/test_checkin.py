"""Personnel check-ins require self-report consent and stay on the 1-5 scale."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from manobal_core.apps.authz.principal import Principal
from manobal_core.apps.governance.enums import DataType, Role
from manobal_core.apps.governance.models import ConsentEntry, ConsentTextVersion, Subject

pytestmark = pytest.mark.django_db(databases=["default", "org", "psy", "bio", "voice"])


def _client(subject: Subject) -> APIClient:
    principal = Principal(
        actor_id=subject.subject_token,
        role=Role.PERSONNEL,
        force_code=subject.force_code,
        unit_code=subject.unit_id,
        subject_token=subject.subject_token,
    )
    client = APIClient()
    client.force_authenticate(user=principal)
    return client


def test_a_consented_checkin_is_recorded(
    subject: Subject, consent_text: ConsentTextVersion
) -> None:
    ConsentEntry.objects.create(
        subject_token=subject.subject_token,
        data_type=DataType.SELF_REPORT,
        granted=True,
        consent_text=consent_text,
    )
    response = _client(subject).post(
        "/v1/me/checkin",
        {"mood": 3, "sleep_quality": 2, "stress": 4, "connection": 3},
        format="json",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["mood"] == 3
    assert body["stress"] == 4
    assert "insights" in body
    assert body["insights"]["lede"]
    assert "wsi" not in str(body).lower()
    assert "score" not in str(body["insights"]).lower()
    picture = _client(subject).get("/v1/me/insights")
    assert picture.status_code == 200
    assert picture.json()["lede"]
    assert picture.json()["engine_note"]
    assert "next" in picture.json()


def test_a_checkin_without_consent_is_refused(subject: Subject) -> None:
    response = _client(subject).post("/v1/me/checkin", {"mood": 3}, format="json")
    assert response.status_code == 422
