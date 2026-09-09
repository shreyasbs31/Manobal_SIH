"""The Zone 3 HTTP surface: who may call it, and what they may learn.

§4.9: only four workload identities may call the enclave, and each may call
only specific methods. The ingest worker tokenises; it cannot resolve. The case
path resolves; it cannot enrol. The WDEC console break-glasses; it does not
browse. Those are not documentation — they are the allow-list these tests pin.

A second, quieter property: an error must not confirm that a person exists.
Problem details carry a code and a request id. They do not carry a service
number, a name, or a token the caller did not already send.
"""

from __future__ import annotations

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from manobal_identity.api.runtime import configure_vault
from manobal_identity.grants.assertion import Operation

pytestmark = pytest.mark.django_db

INGEST = "spiffe://manobal/ns/manobal-core/sa/ingest-worker"
CORE = "spiffe://manobal/ns/manobal-core/sa/core-api"
ALERT = "spiffe://manobal/ns/manobal-core/sa/alert-service"
WDEC = "spiffe://manobal/ns/manobal-core/sa/wdec-console"
STRANGER = "spiffe://manobal/ns/other/sa/curious"


@pytest.fixture
def client(vault):
    configure_vault(vault)
    try:
        yield APIClient()
    finally:
        configure_vault(None)


def post(client: APIClient, path: str, payload: dict, *, workload: str | None, **headers):
    extra = {}
    if workload is not None:
        extra["HTTP_X_WORKLOAD_ID"] = workload
    extra.update(headers)
    return client.post(path, payload, format="json", **extra)


def person_payload(service_no: str = "CRPF-1999-000001") -> dict:
    return {
        "service_no": service_no,
        "full_name": "Constable Test",
        "rank_code": "CT",
        "mobile_e164": "+919800000001",
        "unit_code": "ALPHA-COY",
        "unit_path": "CENTRAL/WESTERN/12BN/ALPHA-COY",
        "force_code": "CRPF",
        "enrolled_on": "2020-01-15",
    }


class TestWorkloadAllowList:
    def test_a_request_without_a_workload_is_unauthenticated(self, client) -> None:
        response = post(client, "/v1/identity/tokenise", {"people": []}, workload=None)
        assert response.status_code == 401
        assert response["Content-Type"] == "application/problem+json"
        assert response.json()["code"] == "MB-4010"

    def test_an_unknown_workload_is_unauthenticated(self, client) -> None:
        response = post(
            client, "/v1/identity/tokenise", {"people": [person_payload()]}, workload=STRANGER
        )
        assert response.status_code == 401
        assert response.json()["code"] == "MB-4011"

    def test_the_ingest_worker_cannot_resolve(self, client, enrolled, assert_for) -> None:
        token = next(iter(enrolled.values()))
        response = post(
            client,
            "/v1/identity/resolve",
            {"assertion": assert_for(token)},
            workload=INGEST,
        )
        assert response.status_code == 403
        assert response.json()["code"] == "MB-4030"

    def test_the_case_path_cannot_tokenise(self, client) -> None:
        response = post(
            client, "/v1/identity/tokenise", {"people": [person_payload()]}, workload=CORE
        )
        assert response.status_code == 403

    def test_the_wdec_console_cannot_resolve(self, client, enrolled, assert_for) -> None:
        token = next(iter(enrolled.values()))
        response = post(
            client,
            "/v1/identity/resolve",
            {"assertion": assert_for(token)},
            workload=WDEC,
        )
        assert response.status_code == 403

    def test_mtls_mode_ignores_the_local_header(self, client) -> None:
        with override_settings(REQUIRE_MTLS=True):
            response = post(
                client,
                "/v1/identity/tokenise",
                {"people": [person_payload()]},
                workload=INGEST,
            )
        assert response.status_code == 401

    def test_a_spiffe_id_from_the_proxy_is_accepted_under_mtls(self, client) -> None:
        with override_settings(REQUIRE_MTLS=True):
            response = post(
                client,
                "/v1/identity/tokenise",
                {"people": [person_payload()]},
                workload=None,
                HTTP_X_SPIFFE_ID=INGEST,
            )
        assert response.status_code == 200


class TestTokenise:
    def test_the_ingest_worker_receives_only_tokens(self, client) -> None:
        payload = person_payload("CRPF-2001-111111")
        response = post(client, "/v1/identity/tokenise", {"people": [payload]}, workload=INGEST)
        assert response.status_code == 200
        body = response.json()
        assert set(body) == {"tokens"}
        token = body["tokens"][payload["service_no"]]
        assert token.startswith("st_")
        assert payload["full_name"] not in response.content.decode()

    def test_an_empty_batch_is_rejected(self, client) -> None:
        response = post(client, "/v1/identity/tokenise", {"people": []}, workload=INGEST)
        assert response.status_code == 422
        assert response.json()["code"] == "MB-4220"

    def test_a_missing_field_is_rejected_without_echoing_the_name(self, client) -> None:
        broken = person_payload()
        name = broken.pop("full_name")
        response = post(client, "/v1/identity/tokenise", {"people": [broken]}, workload=INGEST)
        assert response.status_code == 422
        assert name not in response.content.decode()


class TestResolve:
    def test_the_case_path_may_resolve_a_live_grant(
        self, client, enrolled, assert_for, people
    ) -> None:
        service_no = people[0].service_no
        token = enrolled[service_no]
        response = post(
            client,
            "/v1/identity/resolve",
            {"assertion": assert_for(token)},
            workload=CORE,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["service_no"] == service_no
        assert body["subject_token"] == token
        assert response["Cache-Control"] == "no-store"

    def test_the_alert_service_may_also_resolve(self, client, enrolled, assert_for) -> None:
        token = next(iter(enrolled.values()))
        response = post(
            client,
            "/v1/identity/resolve",
            {"assertion": assert_for(token)},
            workload=ALERT,
        )
        assert response.status_code == 200

    def test_a_forged_assertion_does_not_confirm_the_token(self, client, enrolled) -> None:
        token = next(iter(enrolled.values()))
        response = post(
            client,
            "/v1/identity/resolve",
            {"assertion": "mbga1.not-a-real-assertion"},
            workload=CORE,
        )
        assert response.status_code == 403
        text = response.content.decode()
        assert token not in text
        assert "service_no" not in response.json()

    def test_a_missing_assertion_is_rejected(self, client) -> None:
        response = post(client, "/v1/identity/resolve", {}, workload=CORE)
        assert response.status_code == 422


class TestBreakGlass:
    def test_the_wdec_console_may_break_glass(self, client, enrolled, assert_for, people) -> None:
        service_no = people[0].service_no
        token = enrolled[service_no]
        response = post(
            client,
            "/v1/identity/break-glass",
            {
                "assertion": assert_for(
                    token,
                    operation=Operation.BREAK_GLASS,
                    second_approver_id="wdec_chair",
                )
            },
            workload=WDEC,
        )
        assert response.status_code == 200
        assert response.json()["service_no"] == service_no

    def test_the_case_path_cannot_break_glass(self, client, enrolled, assert_for) -> None:
        token = next(iter(enrolled.values()))
        response = post(
            client,
            "/v1/identity/break-glass",
            {
                "assertion": assert_for(
                    token,
                    operation=Operation.BREAK_GLASS,
                    second_approver_id="wdec_chair",
                )
            },
            workload=CORE,
        )
        assert response.status_code == 403


class TestHealthAndErrors:
    def test_liveness_does_not_require_a_workload(self, client) -> None:
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "zone": 3}

    def test_every_error_carries_a_request_id_and_no_identity(self, client) -> None:
        response = post(
            client,
            "/v1/identity/tokenise",
            {"people": [person_payload()]},
            workload=STRANGER,
            HTTP_X_REQUEST_ID="req-audit-1",
        )
        body = response.json()
        assert body["request_id"]
        assert "Kumar" not in response.content.decode()
        assert "CRPF-" not in response.content.decode()
