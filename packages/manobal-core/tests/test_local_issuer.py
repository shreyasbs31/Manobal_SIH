"""The laptop issuer mints the same claim set a force IdP would issue."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from manobal_core.apps.authz.local_issuer import mint_token
from manobal_core.apps.governance.enums import DataType, Role
from manobal_core.apps.governance.models import ConsentTextVersion, Subject

pytestmark = pytest.mark.django_db


def test_a_minted_personnel_token_reaches_the_consent_surface(
    subject: Subject, consent_text: ConsentTextVersion
) -> None:
    del consent_text
    token = mint_token(
        role=Role.PERSONNEL,
        actor_id=subject.subject_token,
        subject_token=subject.subject_token,
        unit_code="12BN_A",
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    created = client.post(
        "/v1/me/consent",
        {"data_type": DataType.SELF_REPORT, "granted": True},
        format="json",
    )
    assert created.status_code == 201
    listing = client.get("/v1/me/consent")
    assert listing.status_code == 200
    assert listing.json()["subject_token"] == subject.subject_token


def test_dev_jwks_is_published_when_the_local_issuer_is_on() -> None:
    response = APIClient().get("/dev/jwks")
    assert response.status_code == 200
    keys = response.json()["keys"]
    assert keys[0]["kid"] == "manobal-dev-1"
    assert keys[0]["kty"] == "RSA"


def test_dev_token_rejects_an_unknown_role() -> None:
    response = APIClient().post("/dev/token", {"role": "spy"}, format="json")
    assert response.status_code == 422


def test_dev_seed_describes_the_demo_walkthrough() -> None:
    response = APIClient().get("/dev/seed")
    assert response.status_code == 200
    body = response.json()
    assert "personnel_token" in body
    assert isinstance(body["llm_configured"], bool)
    assert len(body["walkthrough"]) >= 4
