"""Officer reachability: duty phone and push token (FR-6)."""

from __future__ import annotations

from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from manobal_core.alerting.destinations import (
    DestinationRefused,
    destination_status,
    register_destination,
)
from manobal_core.apps.api.views import Unprocessable, _actor, _audit, _payload
from manobal_core.apps.authz.permissions import IsCaseOfficer
from manobal_core.apps.authz.principal import Principal
from manobal_core.apps.governance.enums import AuditAction, LegalBasis, PurposeCode
from manobal_core.apps.governance.models import OfficerProfile


class OfficerDestinationView(APIView):
    permission_classes = [IsCaseOfficer]  # noqa: RUF012

    def get(self, request: Request) -> Response:
        principal, profile = _own_profile(request)
        _audit(
            principal,
            action=AuditAction.INDIVIDUAL_READ,
            purpose=PurposeCode.CASE_REVIEW,
            basis=LegalBasis.LEGAL_OBLIGATION,
            outcome="success",
            detail={"event": "officer.destination.read"},
        )
        return Response(destination_status(profile))

    def post(self, request: Request) -> Response:
        principal, _profile = _own_profile(request)
        body = _payload(request)
        try:
            updated = register_destination(
                principal.actor_id,
                duty_phone_e164=body.get("duty_phone_e164")
                if "duty_phone_e164" in body
                else None,
                push_token=body.get("push_token") if "push_token" in body else None,
            )
        except DestinationRefused as exc:
            raise Unprocessable(f"MB-4220: {exc}") from exc
        _audit(
            principal,
            action=AuditAction.ADMIN_ACTION,
            purpose=PurposeCode.CASE_REVIEW,
            basis=LegalBasis.LEGAL_OBLIGATION,
            outcome="success",
            detail={"event": "officer.destination.write"},
        )
        return Response(destination_status(updated))


def _own_profile(request: Request) -> tuple[Principal, OfficerProfile]:
    principal = _actor(request)
    profile = OfficerProfile.objects.filter(pk=principal.actor_id).first()
    if profile is None:
        raise PermissionDenied("MB-4030: you are not permitted to perform this action")
    return principal, profile
