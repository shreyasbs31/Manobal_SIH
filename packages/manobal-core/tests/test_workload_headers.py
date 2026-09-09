"""Zone 2 identity clients present a workload id. They never open the vault."""

from __future__ import annotations

import httpx
import pytest

from manobal_core.identity.resolve import RESOLVE_WORKLOAD, HttpResolveClient
from manobal_core.ingest.identity import TOKENISE_WORKLOAD, IdentityClient

pytestmark = pytest.mark.django_db


def test_the_resolve_client_identifies_itself_as_core_api() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers.get("X-Workload-Id", ""))
        return httpx.Response(
            200,
            json={
                "subject_token": "tok",
                "service_no": "x",
                "full_name": "x",
                "rank_code": "CT",
                "mobile_e164": "+91",
                "unit_code": "12BN_A",
                "force_code": "CAPF",
            },
        )

    client = HttpResolveClient(transport=httpx.MockTransport(handler))
    client.resolve("mbga1.payload.sig")
    assert seen == [RESOLVE_WORKLOAD]


def test_the_tokenise_client_identifies_itself_as_ingest_worker() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers.get("X-Workload-Id", ""))
        return httpx.Response(200, json={"tokens": {"CRPF-1": "tok_1"}})

    client = IdentityClient(transport=httpx.MockTransport(handler))
    client.tokenise([{"service_no": "CRPF-1"}])
    assert seen == [TOKENISE_WORKLOAD]
    assert TOKENISE_WORKLOAD != RESOLVE_WORKLOAD
