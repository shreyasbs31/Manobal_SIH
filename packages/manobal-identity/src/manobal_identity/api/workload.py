"""Identify the calling workload and what it is allowed to ask for.

§4.9: "Only four workload identities may call it, and each may call only
specific methods." In production those identities are SPIFFE IDs on an mTLS
client certificate, terminated at the ingress and forwarded as a header the
ingress itself sets. Locally, and only locally, the same names arrive on
``X-Workload-Id`` so a laptop can exercise the allow-list without a mesh.

The local header is ignored whenever ``REQUIRE_MTLS`` is on. Honouring both
at once would let anyone who can reach the process impersonate the ingest
worker by setting a header, which is exactly the bypass mTLS exists to close.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from django.conf import settings
from rest_framework import authentication, exceptions
from rest_framework.permissions import BasePermission

if TYPE_CHECKING:
    from rest_framework.request import Request

SCOPE_TOKENISE: Final = "manobal.identity.tokenise"
SCOPE_RESOLVE: Final = "manobal.identity.resolve"
SCOPE_BREAK_GLASS: Final = "manobal.identity.breakglass"

#: Headers set by a mesh / ingress after it has verified the client certificate.
_MTLS_IDENTITY_HEADERS: Final = ("HTTP_X_SPIFFE_ID", "SSL_CLIENT_SAN_URI")
_LOCAL_IDENTITY_HEADER: Final = "HTTP_X_WORKLOAD_ID"


@dataclass(frozen=True, slots=True)
class WorkloadPrincipal:
    """The caller, as far as this process is willing to believe."""

    workload_id: str
    scopes: frozenset[str]

    @property
    def is_authenticated(self) -> bool:
        return True


def identify_workload(request: Request, *, require_mtls: bool) -> str | None:
    """Return the workload id, or ``None`` if the caller did not present one."""
    for header in _MTLS_IDENTITY_HEADERS:
        value = (request.META.get(header) or "").strip()
        if value:
            return value
    if require_mtls:
        return None
    return (request.META.get(_LOCAL_IDENTITY_HEADER) or "").strip() or None


class WorkloadAuthentication(authentication.BaseAuthentication):
    """Accept a known workload; refuse everyone else without explaining why."""

    def authenticate(self, request: Request) -> tuple[WorkloadPrincipal, str] | None:
        workload_id = identify_workload(request, require_mtls=settings.REQUIRE_MTLS)
        if not workload_id:
            raise exceptions.AuthenticationFailed("MB-4010: missing workload identity")

        scopes = settings.WORKLOAD_SCOPES.get(workload_id)
        if scopes is None:
            raise exceptions.AuthenticationFailed("MB-4011: unknown workload identity")

        principal = WorkloadPrincipal(workload_id=workload_id, scopes=frozenset(scopes))
        request.workload = principal  # type: ignore[attr-defined]
        return principal, workload_id

    def authenticate_header(self, request: Request) -> str:
        return 'SPIFFE realm="manobal-identity"'


class WorkloadScopePermission(BasePermission):
    """The view names the scope; the principal either has it or does not."""

    def has_permission(self, request: Request, view: object) -> bool:
        required = getattr(view, "required_scope", None)
        principal = getattr(request, "user", None)
        return isinstance(principal, WorkloadPrincipal) and required in principal.scopes
