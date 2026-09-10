"""WDEC fairness, audit browser, and break-glass invoke."""

from __future__ import annotations

from datetime import datetime

from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from manobal_core.apps.api.views import TooMany, Unprocessable, _actor, _audit, _payload
from manobal_core.apps.api.views_extra import _as_int
from manobal_core.apps.authz.permissions import IsIntegration, IsWDECAuditor
from manobal_core.apps.governance.enums import AuditAction, LegalBasis, PurposeCode
from manobal_core.apps.governance.models import AuditEvent, Case, Subject, Unit
from manobal_core.erasure.separation import mark_separated
from manobal_core.identity.breakglass import BreakGlassRefused, invoke_break_glass
from manobal_core.oversight.audit import list_audit
from manobal_core.oversight.fairness import fairness_report


class WdecFairnessView(APIView):
    permission_classes = [IsWDECAuditor]  # noqa: RUF012

    def get(self, request: Request) -> Response:
        principal = _actor(request)
        unit_code = str(request.query_params.get("unit") or "")
        unit = Unit.objects.filter(code=unit_code).first()
        if unit is None:
            raise NotFound("MB-4040: not found")
        report = fairness_report(unit)
        _audit(
            principal,
            action=AuditAction.INDIVIDUAL_READ,
            purpose=PurposeCode.OVERSIGHT_AUDIT,
            basis=LegalBasis.LEGAL_OBLIGATION,
            outcome="success",
            detail={"event": "fairness.read", "unit": unit.code},
        )
        return Response(report)


class WdecAuditView(APIView):
    permission_classes = [IsWDECAuditor]  # noqa: RUF012

    def get(self, request: Request) -> Response:
        principal = _actor(request)
        after = _when(request.query_params.get("after"))
        before = _when(request.query_params.get("before"))
        limit = _as_int(request.query_params.get("limit") or 50)
        events = list_audit(
            action=str(request.query_params.get("action") or ""),
            after=after,
            before=before,
            limit=limit,
        )
        _audit(
            principal,
            action=AuditAction.INDIVIDUAL_READ,
            purpose=PurposeCode.OVERSIGHT_AUDIT,
            basis=LegalBasis.LEGAL_OBLIGATION,
            outcome="success",
            detail={"event": "audit.browse", "count": len(events)},
        )
        return Response({"events": events})


class WdecBreakGlassInvokeView(APIView):
    permission_classes = [IsWDECAuditor]  # noqa: RUF012

    def post(self, request: Request) -> Response:
        principal = _actor(request)
        if not _breakglass_rate_ok(principal.actor_id):
            raise TooMany("MB-4290: identity resolve rate limit exceeded")
        body = _payload(request)
        case = Case.objects.filter(pk=_as_int(body.get("case_id") or 0)).first()
        if case is None:
            raise Unprocessable("MB-4220: unknown case")
        try:
            _grant, person = invoke_break_glass(
                case,
                principal,
                justification=str(body.get("justification") or ""),
                second_approver_id=str(body.get("second_approver_id") or ""),
            )
        except BreakGlassRefused as exc:
            raise Unprocessable(f"MB-4220: {exc}") from exc
        _audit(
            principal,
            action=AuditAction.BREAK_GLASS,
            purpose=PurposeCode.BREAK_GLASS,
            basis=LegalBasis.LEGAL_OBLIGATION,
            outcome="success",
            subject_token=case.subject_token,
            detail={"event": "identity.break_glass", "case_id": case.id},
        )
        return Response(
            {
                "service_no": person.service_no,
                "full_name": person.full_name,
                "rank_code": person.rank_code,
                "mobile_e164": person.mobile_e164,
                "unit_code": person.unit_code,
                "force_code": person.force_code,
            },
            headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
            status=status.HTTP_200_OK,
        )


class IngestSeparationsView(APIView):
    permission_classes = [IsIntegration]  # noqa: RUF012

    def post(self, request: Request) -> Response:
        principal = _actor(request)
        body = _payload(request)
        tokens = body.get("subject_tokens")
        if not isinstance(tokens, list) or not tokens:
            raise Unprocessable("MB-4220: subject_tokens must be a non-empty list")
        marked = 0
        for raw in tokens:
            token = str(raw)
            subject = Subject.objects.filter(subject_token=token).first()
            if subject is None:
                continue
            mark_separated(subject)
            marked += 1
        _audit(
            principal,
            action=AuditAction.ADMIN_ACTION,
            purpose=PurposeCode.ERASURE,
            basis=LegalBasis.LEGAL_OBLIGATION,
            outcome="success",
            detail={"event": "subject.separated", "count": marked},
        )
        return Response({"marked": marked}, status=status.HTTP_202_ACCEPTED)


def _when(value: object) -> datetime | None:
    if not value:
        return None
    parsed = parse_datetime(str(value))
    return parsed


def _breakglass_rate_ok(actor_id: str) -> bool:
    from datetime import timedelta

    from django.conf import settings
    from django.utils import timezone

    day_ago = timezone.now() - timedelta(days=1)
    used = AuditEvent.objects.filter(
        actor_id=actor_id,
        action=AuditAction.BREAK_GLASS,
        occurred_at__gte=day_ago,
    ).count()
    limits = settings.RATE_LIMITS
    if not isinstance(limits, dict):
        raise TypeError("RATE_LIMITS must be a mapping")
    return used < int(limits["identity_breakglass_per_officer_day"])
