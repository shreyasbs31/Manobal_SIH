"""WDEC break-glass: sign, call Zone 3, forget the answer."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Protocol, cast

import httpx
from django.conf import settings
from django.utils import timezone

from manobal_core.apps.authz.principal import Principal
from manobal_core.apps.governance.enums import GrantScope, LegalBasis, Role
from manobal_core.apps.governance.models import MAX_GRANT_DAYS, AccessGrant, Case
from manobal_core.identity.assertions import sign_grant_assertion
from manobal_core.identity.resolve import ResolveClientError, ResolvedPerson

WDEC_WORKLOAD = "spiffe://manobal/ns/manobal-core/sa/wdec-console"


class BreakGlassClient(Protocol):
    def break_glass(self, assertion: str) -> ResolvedPerson: ...


class HttpBreakGlassClient:
    def __init__(self, *, transport: httpx.BaseTransport | None = None) -> None:
        resolver = cast(dict[str, Any], settings.IDENTITY_RESOLVER)
        self._url = f"{str(resolver['BASE_URL']).rstrip('/')}/v1/identity/break-glass"
        self._timeout = float(resolver["TIMEOUT_SECONDS"])
        cert = str(resolver.get("CLIENT_CERT") or "")
        key = str(resolver.get("CLIENT_KEY") or "")
        self._cert = (cert, key) if cert and key else None
        ca = str(resolver.get("CA_BUNDLE") or "")
        self._verify: str | bool = ca if ca else True
        self._transport = transport

    def break_glass(self, assertion: str) -> ResolvedPerson:
        with httpx.Client(
            timeout=self._timeout,
            cert=self._cert,
            verify=self._verify,
            transport=self._transport,
        ) as client:
            response = client.post(
                self._url,
                json={"assertion": assertion},
                headers={"X-Workload-Id": WDEC_WORKLOAD},
            )
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict):
            raise ResolveClientError("break-glass response was not an object")
        return ResolvedPerson(
            subject_token=str(body.get("subject_token") or ""),
            service_no=str(body.get("service_no") or ""),
            full_name=str(body.get("full_name") or ""),
            rank_code=str(body.get("rank_code") or ""),
            mobile_e164=str(body.get("mobile_e164") or ""),
            unit_code=str(body.get("unit_code") or ""),
            force_code=str(body.get("force_code") or ""),
        )


_client: BreakGlassClient | None = None


def configure_breakglass(client: BreakGlassClient | None) -> None:
    global _client
    _client = client


def get_breakglass() -> BreakGlassClient:
    return _client if _client is not None else HttpBreakGlassClient()


class BreakGlassRefused(ValueError):  # noqa: N818
    """Second approver missing, or the actor approved themselves."""


def invoke_break_glass(
    case: Case,
    principal: Principal,
    *,
    justification: str,
    second_approver_id: str,
    client: BreakGlassClient | None = None,
) -> tuple[AccessGrant, ResolvedPerson]:
    """Create the grant, sign, resolve, and return. Callers must not persist the person."""
    reason = justification.strip()
    approver = second_approver_id.strip()
    if not reason or not approver:
        raise BreakGlassRefused("justification and second_approver_id are required")
    if approver == principal.actor_id:
        raise BreakGlassRefused("you cannot be your own second approver")
    now = timezone.now()
    grant = AccessGrant.objects.create(
        subject_token=case.subject_token,
        grantee_id=principal.actor_id,
        grantee_role=Role.WDEC_AUDITOR,
        scope=GrantScope.IDENTITY,
        case=case,
        granted_at=now,
        expires_at=now + timedelta(days=MAX_GRANT_DAYS),
        subject_consented=False,
        legal_basis=LegalBasis.LEGAL_OBLIGATION,
        justification=reason[:1000],
        break_glass=True,
        subject_notified_at=now,
    )
    assertion = sign_grant_assertion(
        case=case,
        grant=grant,
        principal=principal,
        operation="break_glass",
        purpose="break_glass",
        second_approver_id=approver,
    )
    try:
        person = (client or get_breakglass()).break_glass(assertion)
    except Exception:
        grant.revoked_at = timezone.now()
        grant.save(update_fields=["revoked_at"])
        raise
    return grant, person
