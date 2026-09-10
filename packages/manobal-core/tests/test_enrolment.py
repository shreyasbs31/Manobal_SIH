"""Zone 2 pairing binds a device to a token. It never learns a service number."""

from __future__ import annotations

import pytest

from manobal_core.apps.governance.models import PairedDevice, Subject

from .test_core_api import client_for, personnel_of

pytestmark = pytest.mark.django_db

VALID_KEY = "A" * 32
VALID_DEVICE = "phone-alpha-01"


class TestDevicePairing:
    def test_personnel_can_pair_and_revoke_a_device(self, subject: Subject) -> None:
        client = client_for(personnel_of(subject))
        created = client.post(
            "/v1/me/devices",
            {"device_id": VALID_DEVICE, "public_key": VALID_KEY},
            format="json",
        )
        assert created.status_code == 201
        assert created.json()["device_id"] == VALID_DEVICE
        assert created.json()["revoked_at"] is None
        listing = client.get("/v1/me/devices")
        assert listing.status_code == 200
        assert listing.json()["devices"][0]["device_id"] == VALID_DEVICE
        revoked = client.post(f"/v1/me/devices/{created.json()['id']}/revoke", {}, format="json")
        assert revoked.status_code == 200
        assert revoked.json()["revoked_at"]
        row = PairedDevice.objects.get(pk=created.json()["id"])
        assert row.revoked_at is not None

    def test_a_malformed_device_id_is_rejected(self, subject: Subject) -> None:
        response = client_for(personnel_of(subject)).post(
            "/v1/me/devices",
            {"device_id": "x", "public_key": VALID_KEY},
            format="json",
        )
        assert response.status_code == 422
        assert PairedDevice.objects.count() == 0

    def test_a_revoked_device_can_be_paired_again(self, subject: Subject) -> None:
        client = client_for(personnel_of(subject))
        created = client.post(
            "/v1/me/devices",
            {"device_id": VALID_DEVICE, "public_key": VALID_KEY},
            format="json",
        )
        client.post(f"/v1/me/devices/{created.json()['id']}/revoke", {}, format="json")
        again = client.post(
            "/v1/me/devices",
            {"device_id": VALID_DEVICE, "public_key": "B" * 32},
            format="json",
        )
        assert again.status_code == 201
        assert again.json()["revoked_at"] is None
        assert PairedDevice.objects.filter(subject_token=subject.subject_token).count() == 1
