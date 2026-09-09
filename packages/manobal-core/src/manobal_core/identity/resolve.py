"""Call Zone 3 resolve. The identifying payload is never written to Zone 2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, cast

import httpx
from django.conf import settings

from manobal_core.apps.authz.principal import Principal
from manobal_core.apps.governance.models import AccessGrant, Case
from manobal_core.identity.assertions import sign_resolve_assertion

RESOLVE_WORKLOAD = "spiffe://manobal/ns/manobal-core/sa/core-api"


@dataclass(frozen=True, slots=True)
class ResolvedPerson:
    """Identifying fields as returned by the enclave. Not a persisted model."""

    subject_token: str
    service_no: str
    full_name: str
    rank_code: str
    mobile_e164: str
    unit_code: str
    force_code: str


class ResolveClient(Protocol):
    def resolve(self, assertion: str) -> ResolvedPerson: ...


class HttpResolveClient:
    def __init__(self, *, transport: httpx.BaseTransport | None = None) -> None:
        resolver = cast(dict[str, Any], settings.IDENTITY_RESOLVER)
        self._url = f"{str(resolver['BASE_URL']).rstrip('/')}/v1/identity/resolve"
        self._timeout = float(resolver["TIMEOUT_SECONDS"])
        cert = str(resolver.get("CLIENT_CERT") or "")
        key = str(resolver.get("CLIENT_KEY") or "")
        self._cert = (cert, key) if cert and key else None
        ca = str(resolver.get("CA_BUNDLE") or "")
        self._verify: str | bool = ca if ca else True
        self._transport = transport

    def resolve(self, assertion: str) -> ResolvedPerson:
        with httpx.Client(
            timeout=self._timeout,
            cert=self._cert,
            verify=self._verify,
            transport=self._transport,
        ) as client:
            response = client.post(
                self._url,
                json={"assertion": assertion},
                headers={"X-Workload-Id": RESOLVE_WORKLOAD},
            )
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict):
            raise ResolveClientError("resolve response was not an object")
        return ResolvedPerson(
            subject_token=str(body.get("subject_token") or ""),
            service_no=str(body.get("service_no") or ""),
            full_name=str(body.get("full_name") or ""),
            rank_code=str(body.get("rank_code") or ""),
            mobile_e164=str(body.get("mobile_e164") or ""),
            unit_code=str(body.get("unit_code") or ""),
            force_code=str(body.get("force_code") or ""),
        )


class ResolveClientError(RuntimeError):
    """The enclave refused the assertion or misfired."""


_client: ResolveClient | None = None


def configure_resolve(client: ResolveClient | None) -> None:
    global _client
    _client = client


def get_resolve() -> ResolveClient:
    return _client if _client is not None else HttpResolveClient()


def resolve_for_case(
    case: Case,
    grant: AccessGrant,
    principal: Principal,
    *,
    client: ResolveClient | None = None,
) -> ResolvedPerson:
    """Sign, call, return. Callers must not persist the result."""
    assertion = sign_resolve_assertion(case=case, grant=grant, principal=principal)
    return (client or get_resolve()).resolve(assertion)
