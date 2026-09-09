"""Zone 2's only call into Zone 3: service number → token (FR-2.4).

This client speaks HTTP. It does not import ``manobal_identity``. The enclave
is a network service with its own database; sharing a Python package would
put vault types on this side of the air-gap and invite someone to "just"
open a second connection.

The method here is tokenise. There is no resolve helper in this module on
purpose: the ingest worker's service account must not hold that scope, and a
function that does not exist cannot be called by mistake.
"""

from __future__ import annotations

from typing import Any, Protocol, cast

import httpx
from django.conf import settings

TOKENISE_WORKLOAD = "spiffe://manobal/ns/manobal-core/sa/ingest-worker"


class TokeniseClient(Protocol):
    def tokenise(self, people: list[dict[str, str]]) -> dict[str, str]: ...


class IdentityClient:
    """HTTP client for ``POST /v1/identity/tokenise``."""

    def __init__(self, *, transport: httpx.BaseTransport | None = None) -> None:
        resolver = cast(dict[str, Any], settings.IDENTITY_RESOLVER)
        self._url = f"{str(resolver['BASE_URL']).rstrip('/')}/v1/identity/tokenise"
        self._timeout = float(resolver["TIMEOUT_SECONDS"])
        self._cert = _client_cert(resolver)
        ca = str(resolver["CA_BUNDLE"] or "")
        self._verify: str | bool = ca if ca else True
        self._transport = transport

    def tokenise(self, people: list[dict[str, str]]) -> dict[str, str]:
        if not people:
            return {}
        with httpx.Client(
            timeout=self._timeout,
            cert=self._cert,
            verify=self._verify,
            transport=self._transport,
        ) as client:
            response = client.post(
                self._url,
                json={"people": people},
                headers={"X-Workload-Id": TOKENISE_WORKLOAD},
            )
        response.raise_for_status()
        body = response.json()
        tokens = body.get("tokens") if isinstance(body, dict) else None
        if not isinstance(tokens, dict):
            raise IdentityClientError("tokenise response did not contain a token map")
        return {str(key): str(value) for key, value in tokens.items()}


class IdentityClientError(RuntimeError):
    """The enclave refused or misfired. Callers must not persist the batch."""


_client: TokeniseClient | None = None


def configure_identity(client: TokeniseClient | None) -> None:
    """Install (or clear) the tokenise client. Tests use this; production does not."""
    global _client
    _client = client


def get_identity() -> TokeniseClient:
    return _client if _client is not None else IdentityClient()


def _client_cert(resolver: dict[str, Any]) -> tuple[str, str] | None:
    cert = str(resolver.get("CLIENT_CERT") or "")
    key = str(resolver.get("CLIENT_KEY") or "")
    if cert and key:
        return cert, key
    return None
