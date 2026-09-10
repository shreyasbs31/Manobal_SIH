"""Officer actions that sit beside the existing case views."""

from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from manobal_core.apps.api.views import (
    Unprocessable,
    _actor,
    _audit,
    _authorised_case,
    _case_summary,
    _payload,
)
from manobal_core.apps.authz.permissions import IsCaseOfficer, IsMedicalOfficer, IsWelfareOfficer
from manobal_core.apps.governance.enums import AuditAction, GrantScope, LegalBasis, PurposeCode
from manobal_core.casework.clinical import ClinicalRefused, clinical_queue, refer_clinical
from manobal_core.casework.disclosure import (
    DisclosureRefused,
    category_trend,
    request_disclosure,
)


class OfficerDisclosureView(APIView):
    permission_classes = [IsWelfareOfficer]  # noqa: RUF012

    def post(self, request: Request, case_id: int) -> Response:
        principal, case = _authorised_case(request, case_id)
        body = _payload(request)
        try:
            row = request_disclosure(
                case,
                actor_id=principal.actor_id,
                category=str(body.get("category") or ""),
                rationale=str(body.get("rationale") or ""),
            )
        except DisclosureRefused as exc:
            raise Unprocessable(f"MB-4220: {exc}") from exc
        _audit(
            principal,
            action=AuditAction.DISCLOSURE_REQUEST,
            purpose=PurposeCode.CASE_REVIEW,
            basis=LegalBasis.CONSENT,
            outcome="success",
            subject_token=case.subject_token,
            detail={"event": "disclosure.request", "case_id": case.id},
        )
        return Response(
            {
                "id": row.id,
                "category": row.category,
                "expires_at": row.expires_at.isoformat(),
                "granted": row.granted,
            },
            status=status.HTTP_201_CREATED,
        )


class OfficerTrendView(APIView):
    permission_classes = [IsCaseOfficer]  # noqa: RUF012

    def get(self, request: Request, case_id: int) -> Response:
        principal, case = _authorised_case(request, case_id)
        category = str(request.query_params.get("category") or "")
        try:
            points = category_trend(case, category)
        except DisclosureRefused as exc:
            raise PermissionDenied("MB-4032: this information is not available to you") from exc
        _audit(
            principal,
            action=AuditAction.INDIVIDUAL_READ,
            purpose=PurposeCode.CASE_REVIEW,
            basis=LegalBasis.CONSENT,
            outcome="success",
            subject_token=case.subject_token,
            detail={"event": "disclosure.trend", "case_id": case.id},
        )
        return Response({"category": category, "points": points})


class OfficerClinicalReferView(APIView):
    permission_classes = [IsWelfareOfficer]  # noqa: RUF012

    def post(self, request: Request, case_id: int) -> Response:
        principal, case = _authorised_case(request, case_id)
        body = _payload(request)
        try:
            grant = refer_clinical(
                case,
                medical_actor_id=str(body.get("medical_actor_id") or ""),
                rationale=str(body.get("rationale") or ""),
            )
        except ClinicalRefused as exc:
            raise Unprocessable(f"MB-4220: {exc}") from exc
        _audit(
            principal,
            action=AuditAction.OFFICER_DECISION,
            purpose=PurposeCode.CLINICAL_REFERRAL,
            basis=LegalBasis.CONSENT,
            outcome="success",
            subject_token=case.subject_token,
            detail={"event": "clinical.refer", "case_id": case.id},
        )
        return Response(
            {"grant_id": grant.id, "scope": GrantScope.CLINICAL_REFERRAL, "assigned": False},
            status=status.HTTP_201_CREATED,
        )


class ClinicalQueueView(APIView):
    permission_classes = [IsMedicalOfficer]  # noqa: RUF012

    def get(self, request: Request) -> Response:
        principal = _actor(request)
        cases = clinical_queue(principal.actor_id)
        _audit(
            principal,
            action=AuditAction.INDIVIDUAL_READ,
            purpose=PurposeCode.CLINICAL_REFERRAL,
            basis=LegalBasis.CONSENT,
            outcome="success",
            detail={"count": len(cases)},
        )
        return Response({"cases": [_case_summary(row) for row in cases]})
