"""Personnel-only surfaces: journal, instruments, contest, disclosure answer."""

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
from manobal_core.apps.governance.models import Case, DisclosureRequest, Subject
from manobal_core.apps.psystore.models import InstrumentResponse
from manobal_core.casework.contest import ContestRefused, contest_case
from manobal_core.casework.disclosure import DisclosureRefused, answer_disclosure
from manobal_core.instruments.catalogue import SUPPORTED_LANGUAGES, catalogue_payload
from manobal_core.instruments.submit import InstrumentRefused, submit_instrument
from manobal_core.journal.service import (
    JournalRefused,
    journal_is_paused,
    list_entries,
    write_entry,
)


def _own(request: Request) -> tuple[object, Subject]:
    principal = _actor(request)
    token = principal.subject_token
    if not may_view_own_record(principal, subject_token=token):
        raise PermissionDenied("MB-4030: you are not permitted to perform this action")
    subject = Subject.objects.filter(subject_token=token).first()
    if subject is None:
        raise Unprocessable("MB-4220: unknown subject")
    return principal, subject


class MeJournalView(APIView):
    permission_classes = [IsPersonnel]  # noqa: RUF012

    def get(self, request: Request) -> Response:
        principal, subject = _own(request)
        entries = list_entries(subject.subject_token)
        _audit(
            principal,
            action=AuditAction.INDIVIDUAL_READ,
            purpose=PurposeCode.SUBJECT_SELF_ACCESS,
            basis=LegalBasis.SUBJECT_REQUEST,
            outcome="success",
            subject_token=subject.subject_token,
            detail={"event": "journal.list", "count": len(entries)},
        )
        return Response(
            {
                "entries": [_journal_body(row) for row in entries],
                "paused": journal_is_paused(subject.subject_token),
            }
        )

    def post(self, request: Request) -> Response:
        principal, subject = _own(request)
        body = _payload(request)
        try:
            retain = body.get("retain")
            row = write_entry(
                subject,
                body=str(body.get("body") or ""),
                crisis_accepted=bool(body.get("crisis_accepted")),
                retain=True if retain is None else bool(retain),
            )
        except JournalRefused as exc:
            raise Unprocessable(f"MB-4220: {exc}") from exc
        _audit(
            principal,
            action=AuditAction.INDIVIDUAL_READ,
            purpose=PurposeCode.SUBJECT_SELF_ACCESS,
            basis=LegalBasis.CONSENT,
            outcome="success",
            subject_token=subject.subject_token,
            detail={"event": "journal.write"},
        )
        return Response(_journal_body(row), status=status.HTTP_201_CREATED)


class MeInstrumentCatalogueView(APIView):
    permission_classes = [IsPersonnel]  # noqa: RUF012

    def get(self, request: Request) -> Response:
        principal, _subject = _own(request)
        code = str(request.query_params.get("code") or "phq9")
        language = str(request.query_params.get("lang") or "en")
        if language not in SUPPORTED_LANGUAGES:
            raise Unprocessable("MB-4220: language must be en or hi")
        try:
            payload = catalogue_payload(code, language)
        except ValueError as exc:
            raise Unprocessable(f"MB-4220: {exc}") from exc
        _audit(
            principal,
            action=AuditAction.INDIVIDUAL_READ,
            purpose=PurposeCode.SUBJECT_SELF_ACCESS,
            basis=LegalBasis.SUBJECT_REQUEST,
            outcome="success",
            subject_token=principal.subject_token,
            detail={"event": "instrument.catalogue", "code": code},
        )
        return Response(payload)


class MeInstrumentSubmitView(APIView):
    permission_classes = [IsPersonnel]  # noqa: RUF012

    def get(self, request: Request) -> Response:
        _principal, subject = _own(request)
        rows = InstrumentResponse.objects.filter(subject_token=subject.subject_token)[:20]
        return Response(
            {
                "history": [
                    {
                        "code": row.instrument_code,
                        "completed_at": row.completed_at.isoformat(),
                        "total": row.total_score,
                        "acute": row.is_acute_flagged,
                    }
                    for row in rows
                ]
            }
        )

    def post(self, request: Request) -> Response:
        principal, subject = _own(request)
        body = _payload(request)
        answers = body.get("answers")
        if not isinstance(answers, list):
            raise Unprocessable("MB-4220: answers must be a list")
        try:
            parsed = [int(item) for item in answers]
            duration = body.get("duration_seconds")
            submission = submit_instrument(
                subject,
                code=str(body.get("code") or ""),
                language=str(body.get("language") or "en"),
                answers=parsed,
                duration_seconds=None if duration in (None, "") else int(duration),
            )
        except (TypeError, ValueError, InstrumentRefused) as exc:
            raise Unprocessable(f"MB-4220: {exc}") from exc
        _audit(
            principal,
            action=AuditAction.INDIVIDUAL_READ,
            purpose=PurposeCode.SUBJECT_SELF_ACCESS,
            basis=LegalBasis.CONSENT,
            outcome="success",
            subject_token=subject.subject_token,
            detail={"event": "instrument.submit", "code": submission.scored.spec.code},
        )
        return Response(
            {
                "code": submission.response.instrument_code,
                "total": submission.response.total_score,
                "acute": submission.response.is_acute_flagged,
                "straight_lined": submission.response.straight_lined,
            },
            status=status.HTTP_201_CREATED,
        )


class MeCasesView(APIView):
    permission_classes = [IsPersonnel]  # noqa: RUF012

    def get(self, request: Request) -> Response:
        _principal, subject = _own(request)
        rows = Case.objects.filter(subject_token=subject.subject_token).order_by("-opened_at")[:20]
        return Response(
            {
                "cases": [
                    {
                        "id": row.id,
                        "tier": row.tier_at_open,
                        "status": row.status,
                        "contributing_categories": row.contributing_categories,
                        "contested_at": (
                            row.contested_at.isoformat() if row.contested_at else None
                        ),
                    }
                    for row in rows
                ]
            }
        )


class MeContestView(APIView):
    permission_classes = [IsPersonnel]  # noqa: RUF012

    def post(self, request: Request, case_id: int) -> Response:
        principal, subject = _own(request)
        case = Case.objects.filter(pk=case_id, subject_token=subject.subject_token).first()
        if case is None:
            raise Unprocessable("MB-4220: unknown case")
        try:
            updated = contest_case(
                case,
                subject_token=subject.subject_token,
                note=str(_payload(request).get("note") or ""),
            )
        except ContestRefused as exc:
            raise Unprocessable(f"MB-4220: {exc}") from exc
        _audit(
            principal,
            action=AuditAction.ADMIN_ACTION,
            purpose=PurposeCode.GRIEVANCE,
            basis=LegalBasis.SUBJECT_REQUEST,
            outcome="success",
            subject_token=subject.subject_token,
            detail={"event": "case.contested", "case_id": updated.id},
        )
        return Response({"id": updated.id, "status": updated.status})


class MeDisclosureListView(APIView):
    permission_classes = [IsPersonnel]  # noqa: RUF012

    def get(self, request: Request) -> Response:
        _principal, subject = _own(request)
        rows = DisclosureRequest.objects.filter(subject_token=subject.subject_token)[:20]
        return Response({"requests": [_disclosure_body(row) for row in rows]})


class MeDisclosureAnswerView(APIView):
    permission_classes = [IsPersonnel]  # noqa: RUF012

    def post(self, request: Request, request_id: int) -> Response:
        principal, subject = _own(request)
        row = DisclosureRequest.objects.filter(
            pk=request_id, subject_token=subject.subject_token
        ).first()
        if row is None:
            raise Unprocessable("MB-4220: unknown disclosure request")
        body = _payload(request)
        if "granted" not in body:
            raise Unprocessable("MB-4220: granted is required")
        try:
            updated = answer_disclosure(
                row, subject_token=subject.subject_token, granted=bool(body.get("granted"))
            )
        except DisclosureRefused as exc:
            raise Unprocessable(f"MB-4220: {exc}") from exc
        _audit(
            principal,
            action=AuditAction.DISCLOSURE_RESPONSE,
            purpose=PurposeCode.CONSENT_MANAGEMENT,
            basis=LegalBasis.SUBJECT_REQUEST,
            outcome="success",
            subject_token=subject.subject_token,
            detail={"event": "disclosure.response", "granted": updated.granted},
        )
        return Response(_disclosure_body(updated))


def _journal_body(row: object) -> dict[str, object]:
    return {
        "id": row.id,  # type: ignore[attr-defined]
        "created_at": row.created_at.isoformat(),  # type: ignore[attr-defined]
        "body": row.body,  # type: ignore[attr-defined]
        "crisis_referred": row.crisis_referred,  # type: ignore[attr-defined]
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,  # type: ignore[attr-defined]
    }


def _disclosure_body(row: DisclosureRequest) -> dict[str, object]:
    return {
        "id": row.id,
        "case_id": row.case_id,
        "category": row.category,
        "rationale": row.rationale,
        "expires_at": row.expires_at.isoformat(),
        "responded_at": row.responded_at.isoformat() if row.responded_at else None,
        "granted": row.granted,
    }
