"""Enrolment OTP returns a token. It never confirms whether a mobile is known."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from manobal_identity.api.runtime import configure_vault
from manobal_identity.apps.vault.models import SubjectIdentity
from manobal_identity.enrolment.otp import request_otp, verify_otp

pytestmark = pytest.mark.django_db

KNOWN = "+919812345670"
UNKNOWN = "+919800000099"


@pytest.fixture
def client(vault):
    configure_vault(vault)
    try:
        yield APIClient()
    finally:
        configure_vault(None)


class TestMobileIndex:
    def test_enrolment_writes_a_mobile_index_and_never_the_number(
        self, enrolled, people
    ) -> None:
        token = enrolled[people[0].service_no]
        row = SubjectIdentity.objects.get(pk=token)
        assert row.mobile_e164_index
        assert people[0].mobile_e164 not in row.mobile_e164_index
        assert "9812345670" not in row.mobile_e164_index


class TestOtpService:
    def test_a_known_mobile_exchanges_a_code_for_a_token(
        self, vault, enrolled, people
    ) -> None:
        configure_vault(vault)
        try:
            issued = request_otp(KNOWN, code="123456")
            assert issued.accepted is True
            token = verify_otp(KNOWN, "123456")
        finally:
            configure_vault(None)
        assert token == enrolled[people[0].service_no]

    def test_an_unknown_mobile_fails_the_same_way(self, vault) -> None:
        configure_vault(vault)
        try:
            issued = request_otp(UNKNOWN, code="123456")
            assert issued.accepted is True
            with pytest.raises(Exception, match="invalid"):
                verify_otp(UNKNOWN, "123456")
        finally:
            configure_vault(None)


class TestOtpHttp:
    def test_request_does_not_disclose_enrolment_or_echo_a_code(
        self, client, enrolled
    ) -> None:
        del enrolled
        known = client.post(
            "/v1/enrolment/otp/request",
            {"mobile_e164": KNOWN, "code": "000000"},
            format="json",
        )
        unknown = client.post(
            "/v1/enrolment/otp/request",
            {"mobile_e164": UNKNOWN},
            format="json",
        )
        assert known.status_code == 202
        assert unknown.status_code == 202
        assert known.json() == {"accepted": True}
        assert unknown.json() == {"accepted": True}
        assert "code" not in known.json()
        verify = client.post(
            "/v1/enrolment/otp/verify",
            {"mobile_e164": KNOWN, "code": "000000"},
            format="json",
        )
        assert verify.status_code == 422
        assert verify.json()["code"] == "MB-4220"
        assert "subject_token" not in verify.json()

    def test_verify_returns_only_the_token(self, client, vault, enrolled, people) -> None:
        del vault
        request_otp(KNOWN, code="654321")
        response = client.post(
            "/v1/enrolment/otp/verify",
            {"mobile_e164": KNOWN, "code": "654321"},
            format="json",
        )
        assert response.status_code == 200
        assert response.json() == {"subject_token": enrolled[people[0].service_no]}
        assert response["Cache-Control"] == "no-store"
        assert people[0].full_name not in response.content.decode()
        assert people[0].service_no not in response.content.decode()
