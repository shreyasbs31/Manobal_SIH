"""DRF permission classes.

The default permission for the whole API is :class:`DenyAll`. That is a
deliberate inversion of the usual convention: a view that forgets to declare
``permission_classes`` serves nobody, rather than serving everybody. In a system
holding mental-health records, the failure mode of an omission has to be an
outage, not a disclosure.

Role checks here are coarse — they answer "may this kind of actor use this kind
of endpoint". The per-record decision, which is the one that matters, belongs to
:mod:`.predicates` and runs inside the view with the record's own attributes in
hand.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from rest_framework.permissions import BasePermission

from ..governance.enums import Role
from .principal import Principal

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.views import APIView


class DenyAll(BasePermission):
    """Refuse everything. The API-wide default."""

    message = "MB-4030: this endpoint declares no permission policy"

    def has_permission(self, request: Request, view: APIView) -> bool:
        return False


def principal_of(request: Request) -> Principal | None:
    """The authenticated actor, whichever attribute it was bound on.

    Authentication writes both ``request.user`` (what DRF requires) and
    ``request.principal`` (what the rest of this package reads). Tests that
    call ``force_authenticate`` only set the first. A permission class that
    looks at only one of them will deny everyone the other path admits.
    """
    for candidate in (getattr(request, "principal", None), getattr(request, "user", None)):
        if isinstance(candidate, Principal):
            request.principal = candidate  # type: ignore[attr-defined]
            return candidate
    return None


class HasRole(BasePermission):
    """Allow an authenticated principal whose role is in ``allowed_roles``."""

    allowed_roles: ClassVar[frozenset[Role]] = frozenset()
    message = "MB-4031: your role may not use this endpoint"

    def has_permission(self, request: Request, view: APIView) -> bool:
        principal = principal_of(request)
        if principal is None:
            return False
        return principal.role in self.allowed_roles


class IsPersonnel(HasRole):
    """The individual acting on their own record."""

    allowed_roles: ClassVar[frozenset[Role]] = frozenset({Role.PERSONNEL})


class IsWelfareOfficer(HasRole):
    allowed_roles: ClassVar[frozenset[Role]] = frozenset({Role.WELFARE_OFFICER})


class IsCaseOfficer(HasRole):
    """Either kind of officer who may be shown an individual flag."""

    allowed_roles: ClassVar[frozenset[Role]] = frozenset(
        {Role.WELFARE_OFFICER, Role.MEDICAL_OFFICER}
    )


class IsMedicalOfficer(HasRole):
    allowed_roles: ClassVar[frozenset[Role]] = frozenset({Role.MEDICAL_OFFICER})


class IsCommander(HasRole):
    """Aggregates only. No endpoint guarded by this may return a subject token."""

    allowed_roles: ClassVar[frozenset[Role]] = frozenset({Role.COMMANDER})


class IsRulesetReviewer(HasRole):
    """Either signer on the dual-approval path may read the proposal queue."""

    allowed_roles: ClassVar[frozenset[Role]] = frozenset(
        {Role.WDEC_AUDITOR, Role.MEDICAL_OFFICER}
    )


class IsWDECAuditor(HasRole):
    """Oversight of the system's own behaviour — accesses, overrides, parity.

    Note what this does *not* grant. A WDEC auditor reviews whether a
    break-glass was justified and whether flag rates differ across subgroups;
    they do not thereby acquire a window into individual welfare records. The
    oversight body is not exempt from the zone model it oversees.
    """

    allowed_roles: ClassVar[frozenset[Role]] = frozenset({Role.WDEC_AUDITOR})


class IsIntegration(HasRole):
    """Machine-to-machine source-system ingestion."""

    allowed_roles: ClassVar[frozenset[Role]] = frozenset({Role.INTEGRATION})
