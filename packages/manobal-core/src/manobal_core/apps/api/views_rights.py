"""Personnel rights surfaces: ledger, erasure, trends, helpline (FR-1.12, FR-7.2)."""

from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from manobal_core.apps.api.views import Unprocessable, _actor, _audit, _payload
from manobal_core.apps.authz.permissions import IsPersonnel
from manobal_core.apps.authz.predicates import may_view_own_record
from manobal_core.apps.governance.enums import (
    AuditAction,
    DataType,
    ErasureStatus,
    LegalBasis,
    PurposeCode,
)
from manobal_core.apps.governance.models import (
    ConsentEntry,
    ConsentTextVersion,
    ErasureRequest,
    RiskAssessmentRecord,
    Subject,
)
from manobal_core.apps.psystore.models import CheckinResponse, InstrumentResponse
from manobal_core.erasure.saga import advance_erasure
from manobal_core.ingest.incidents import offer_checkin_for
from manobal_core.insights.briefing import personnel_briefing
from manobal_core.insights.store import checkin_rows
from manobal_core.journal.service import JournalRefused, delete_entry, journal_is_paused


def _own(request: Request) -> tuple[object, Subject]:
    principal = _actor(request)
    token = principal.subject_token
    if not may_view_own_record(principal, subject_token=token):
        raise PermissionDenied("MB-4030: you are not permitted to perform this action")
    subject = Subject.objects.filter(subject_token=token).first()
    if subject is None:
        raise Unprocessable("MB-4220: unknown subject")
    return principal, subject


class MeConsentLedgerView(APIView):
    permission_classes = [IsPersonnel]  # noqa: RUF012

    def get(self, request: Request) -> Response:
        principal, subject = _own(request)
        rows = ConsentEntry.objects.filter(subject_token=subject.subject_token).order_by(
            "-recorded_at", "-id"
        )[:100]
        _audit(
            principal,
            action=AuditAction.INDIVIDUAL_READ,
            purpose=PurposeCode.CONSENT_MANAGEMENT,
            basis=LegalBasis.SUBJECT_REQUEST,
            outcome="success",
            subject_token=subject.subject_token,
            detail={"event": "consent.ledger"},
        )
        return Response(
            {
                "entries": [
                    {
                        "data_type": row.data_type,
                        "granted": row.granted,
                        "recorded_at": row.recorded_at.isoformat(),
                        "method": row.method,
                        "consent_text_sha256": row.consent_text_sha256,
                    }
                    for row in rows
                ]
            }
        )


class MeErasureView(APIView):
    permission_classes = [IsPersonnel]  # noqa: RUF012

    def get(self, request: Request) -> Response:
        _principal, subject = _own(request)
        rows = ErasureRequest.objects.filter(subject_token=subject.subject_token)[:20]
        return Response({"requests": [_erasure_body(row) for row in rows]})

    def post(self, request: Request) -> Response:
        principal, subject = _own(request)
        body = _payload(request)
        data_type = str(body.get("data_type") or "") or None
        if data_type is not None and data_type not in DataType.values:
            raise Unprocessable("MB-4220: unknown data type")
        text = (
            ConsentTextVersion.objects.filter(retired_at__isnull=True)
            .order_by("-effective_from")
            .first()
        )
        if text is None:
            raise Unprocessable("MB-4220: no active consent text")
        if data_type:
            ConsentEntry.objects.create(
                subject_token=subject.subject_token,
                data_type=data_type,
                granted=False,
                consent_text=text,
                method="app",
            )
        request_row = ErasureRequest.objects.create(
            subject_token=subject.subject_token,
            data_type=data_type,
            status=ErasureStatus.INTENT_RECORDED,
        )
        from django.conf import settings

        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            request_row = advance_erasure(request_row)
        else:
            from manobal_core.tasks import advance_erasure_task

            advance_erasure_task.delay(request_row.id)
        _audit(
            principal,
            action=AuditAction.ERASURE_REQUEST,
            purpose=PurposeCode.ERASURE,
            basis=LegalBasis.SUBJECT_REQUEST,
            outcome="success",
            subject_token=subject.subject_token,
            detail={"erasure_id": request_row.id, "data_type": data_type},
        )
        return Response(_erasure_body(request_row), status=status.HTTP_202_ACCEPTED)


class MeErasureDetailView(APIView):
    permission_classes = [IsPersonnel]  # noqa: RUF012

    def get(self, request: Request, request_id: int) -> Response:
        principal, subject = _own(request)
        row = ErasureRequest.objects.filter(
            pk=request_id, subject_token=subject.subject_token
        ).first()
        if row is None:
            raise NotFound("MB-4040: not found")
        _audit(
            principal,
            action=AuditAction.INDIVIDUAL_READ,
            purpose=PurposeCode.ERASURE,
            basis=LegalBasis.SUBJECT_REQUEST,
            outcome="success",
            subject_token=subject.subject_token,
            detail={"erasure_id": row.id},
        )
        return Response(_erasure_body(row))


class MeInsightsView(APIView):
    permission_classes = [IsPersonnel]  # noqa: RUF012

    def get(self, request: Request) -> Response:
        principal, subject = _own(request)
        record = (
            RiskAssessmentRecord.objects.filter(subject_token=subject.subject_token)
            .order_by("-assessed_at", "-id")
            .first()
        )
        offer = offer_checkin_for(subject)
        body = personnel_briefing(
            checkin_rows(subject.subject_token),
            tier=record.tier if record else None,
            categories=list(record.contributing_categories or []) if record else [],
            offer_checkin=bool(offer.get("offer_checkin")),
        )
        _audit(
            principal,
            action=AuditAction.INDIVIDUAL_READ,
            purpose=PurposeCode.SUBJECT_SELF_ACCESS,
            basis=LegalBasis.SUBJECT_REQUEST,
            outcome="success",
            subject_token=subject.subject_token,
            detail={"event": "insights.read"},
        )
        return Response(body)


class MeTrendsView(APIView):
    permission_classes = [IsPersonnel]  # noqa: RUF012

    def get(self, request: Request) -> Response:
        principal, subject = _own(request)
        domain = str(request.query_params.get("domain") or "self_report")
        checkins = CheckinResponse.objects.filter(subject_token=subject.subject_token).order_by(
            "-observed_on"
        )[:30]
        instruments = InstrumentResponse.objects.filter(
            subject_token=subject.subject_token
        ).order_by("-completed_at")[:20]
        _audit(
            principal,
            action=AuditAction.INDIVIDUAL_READ,
            purpose=PurposeCode.SUBJECT_SELF_ACCESS,
            basis=LegalBasis.SUBJECT_REQUEST,
            outcome="success",
            subject_token=subject.subject_token,
            detail={"event": "trends.read", "domain": domain},
        )
        return Response(
            {
                "domain": domain,
                "checkins": [
                    {
                        "observed_on": row.observed_on.isoformat(),
                        "mood": row.mood,
                        "sleep_quality": row.sleep_quality,
                        "stress": row.stress,
                        "fatigue": row.fatigue,
                        "connection": row.connection,
                    }
                    for row in checkins
                ],
                "instruments": [
                    {
                        "code": row.instrument_code,
                        "completed_at": row.completed_at.isoformat(),
                        "acute": row.is_acute_flagged,
                    }
                    for row in instruments
                ],
            }
        )


class MeHelplineView(APIView):
    """FR-1.12: helpline numbers without opening a welfare record."""

    permission_classes = [IsPersonnel]  # noqa: RUF012

    def post(self, request: Request) -> Response:
        principal, subject = _own(request)
        from django.conf import settings

        numbers = getattr(settings, "HELPLINES", {})
        _audit(
            principal,
            action=AuditAction.INDIVIDUAL_READ,
            purpose=PurposeCode.SUBJECT_SELF_ACCESS,
            basis=LegalBasis.SUBJECT_REQUEST,
            outcome="success",
            subject_token=subject.subject_token,
            detail={"event": "helpline.shown"},
        )
        return Response({"helplines": numbers, "recorded": False})


class MeJournalEntryView(APIView):
    permission_classes = [IsPersonnel]  # noqa: RUF012

    def delete(self, request: Request, entry_id: int) -> Response:
        principal, subject = _own(request)
        try:
            delete_entry(subject.subject_token, entry_id)
        except JournalRefused as exc:
            raise Unprocessable(f"MB-4220: {exc}") from exc
        _audit(
            principal,
            action=AuditAction.INDIVIDUAL_READ,
            purpose=PurposeCode.SUBJECT_SELF_ACCESS,
            basis=LegalBasis.SUBJECT_REQUEST,
            outcome="success",
            subject_token=subject.subject_token,
            detail={"event": "journal.delete", "entry_id": entry_id},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


def _erasure_body(row: ErasureRequest) -> dict[str, object]:
    return {
        "id": row.id,
        "data_type": row.data_type,
        "status": row.status,
        "requested_at": row.requested_at.isoformat(),
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        "receipt_id": row.receipt_id or None,
        "receipt_signature": row.receipt_signature or None,
        "paused_journal": journal_is_paused(row.subject_token),
    }
