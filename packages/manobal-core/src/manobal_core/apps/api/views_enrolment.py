"""Device pairing for an already-authenticated subject."""

from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from manobal_core.apps.api.views import Unprocessable, _actor, _audit, _payload
from manobal_core.apps.authz.permissions import IsPersonnel
from manobal_core.apps.authz.predicates import may_view_own_record
from manobal_core.apps.governance.enums import AuditAction, LegalBasis, PurposeCode
from manobal_core.apps.governance.models import Subject
from manobal_core.enrolment.pairing import PairingRefused, list_devices, pair_device, revoke_device


class MeDevicesView(APIView):
    permission_classes = [IsPersonnel]  # noqa: RUF012

    def get(self, request: Request) -> Response:
        principal, subject = _own(request)
        rows = list_devices(subject.subject_token)
        _audit(
            principal,
            action=AuditAction.INDIVIDUAL_READ,
            purpose=PurposeCode.CONSENT_MANAGEMENT,
            basis=LegalBasis.SUBJECT_REQUEST,
            outcome="success",
            subject_token=subject.subject_token,
            detail={"event": "device.list", "count": len(rows)},
        )
        return Response({"devices": [_device_body(row) for row in rows]})

    def post(self, request: Request) -> Response:
        principal, subject = _own(request)
        body = _payload(request)
        try:
            row = pair_device(
                subject,
                device_id=str(body.get("device_id") or ""),
                public_key=str(body.get("public_key") or ""),
            )
        except PairingRefused as exc:
            raise Unprocessable(f"MB-4220: {exc}") from exc
        _audit(
            principal,
            action=AuditAction.ADMIN_ACTION,
            purpose=PurposeCode.CONSENT_MANAGEMENT,
            basis=LegalBasis.SUBJECT_REQUEST,
            outcome="success",
            subject_token=subject.subject_token,
            detail={"event": "device.pair"},
        )
        return Response(_device_body(row), status=status.HTTP_201_CREATED)


class MeDeviceRevokeView(APIView):
    permission_classes = [IsPersonnel]  # noqa: RUF012

    def post(self, request: Request, device_id: int) -> Response:
        principal, subject = _own(request)
        try:
            row = revoke_device(subject.subject_token, device_id)
        except PairingRefused as exc:
            raise Unprocessable(f"MB-4220: {exc}") from exc
        _audit(
            principal,
            action=AuditAction.ADMIN_ACTION,
            purpose=PurposeCode.CONSENT_MANAGEMENT,
            basis=LegalBasis.SUBJECT_REQUEST,
            outcome="success",
            subject_token=subject.subject_token,
            detail={"event": "device.revoke"},
        )
        return Response(_device_body(row))


def _own(request: Request) -> tuple[object, Subject]:
    principal = _actor(request)
    token = principal.subject_token
    if not may_view_own_record(principal, subject_token=token):
        raise PermissionDenied("MB-4030: you are not permitted to perform this action")
    subject = Subject.objects.filter(subject_token=token).first()
    if subject is None:
        raise Unprocessable("MB-4220: unknown subject")
    return principal, subject


def _device_body(row: object) -> dict[str, object]:
    return {
        "id": row.id,  # type: ignore[attr-defined]
        "device_id": row.device_id,  # type: ignore[attr-defined]
        "paired_at": row.paired_at.isoformat(),  # type: ignore[attr-defined]
        "revoked_at": row.revoked_at.isoformat() if row.revoked_at else None,  # type: ignore[attr-defined]
    }
