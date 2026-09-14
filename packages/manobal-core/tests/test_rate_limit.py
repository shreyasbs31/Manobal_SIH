"""HTTP rate limits fire after the published ceiling (SDD §6.5)."""

from __future__ import annotations

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@override_settings(
    RATE_LIMITS_DISABLED=False,
    RATE_LIMITS={"unauthenticated_per_ip_minute": 2, "officer_queue_per_hour": 600},
)
def test_unauthenticated_callers_are_limited() -> None:
    client = APIClient()
    first = client.get("/v1/me/consent")
    second = client.get("/v1/me/consent")
    third = client.get("/v1/me/consent")
    assert first.status_code == 401
    assert second.status_code == 401
    assert third.status_code == 429
    assert third.json()["code"] == "MB-4290"
