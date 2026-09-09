"""Additional Zone 2 HTTP surfaces: resolve, agent, captures, ruleset."""

from __future__ import annotations

from datetime import timedelta
from typing import cast

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from manobal_core.agent.harness import run_turn
from manobal_core.apps.api.views import (
    Unprocessable,
    _actor,
    _actor_unit_path,
    _audit,
    _authorised_case,
    _mfa,
    _payload,
)
from manobal_core.apps.authz.permissions import (
    IsCaseOfficer,
    IsIntegration,
    IsMedicalOfficer,
    IsPersonnel,
    IsRulesetReviewer,
    IsWDECAuditor,
)
from manobal_core.apps.authz.predicates import (
    may_resolve_identity,
    may_view_flag,
    may_view_own_record,
)
from manobal_core.apps.governance.enums import (
    AuditAction,
    DataType,
    GrantScope,
    LegalBasis,
    PurposeCode,
    Tier,
)
from manobal_core.apps.governance.models import (
    AccessGrant,
    AuditEvent,
    ConsentEntry,
    RulesetProposal,
    Subject,
)
from manobal_core.apps.psystore.models import CheckinResponse
from manobal_core.identity.resolve import resolve_for_case
from manobal_core.ingest.captures import ingest_capture_batch
from manobal_core.ruleset.registry import approve_proposal, register_proposal


class OfficerResolveView(APIView):
    permission_classes = [IsCaseOfficer]  # noqa: RUF012

    def post(self, request: Request, case_id: int) -> Response:
        principal, case = _authorised_case(request, case_id)
        grant = (
            AccessGrant.objects.filter(
                case=case,
                grantee_id=principal.actor_id,
                scope=GrantScope.IDENTITY,
                revoked_at__isnull=True,
                expires_at__gt=timezone.now(),
            )
            .order_by("-granted_at")
            .first()
        )
        scopes = [GrantScope.IDENTITY] if grant is not None else []
        flag = may_view_flag(
            principal,
            subject_force_code=case.unit.force_code,
            subject_unit_path=case.unit.path,
            actor_unit_path=_actor_unit_path(principal),
            tier=Tier(case.tier_at_open),
            officer_is_certified=True,
            has_live_grant=True,
            mfa_satisfied=_mfa(principal),
        )
        decision = may_resolve_identity(
            principal, base=flag, grant_scopes=scopes, mfa_satisfied=_mfa(principal)
        )
        if not decision:
            _audit(
                principal,
                action=AuditAction.ACCESS_DENIED,
                purpose=PurposeCode.ACUTE_RESPONSE,
                basis=LegalBasis.VITAL_INTEREST,
                outcome="denied",
                subject_token=case.subject_token,
                detail={"reason": decision.reason},
            )
            raise PermissionDenied("MB-4032: this information is not available to you")
        if not _resolve_rate_ok(principal.actor_id):
            raise PermissionDenied("MB-4290: identity resolve rate limit exceeded")
        if grant is None:
            raise PermissionDenied("MB-4032: this information is not available to you")
        person = resolve_for_case(case, grant, principal)
        _audit(
            principal,
            action=AuditAction.IDENTITY_RESOLVE,
            purpose=PurposeCode.ACUTE_RESPONSE,
            basis=LegalBasis.VITAL_INTEREST,
            outcome="success",
            subject_token=case.subject_token,
            detail={"case_id": case.id},
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
        )


class MeAgentView(APIView):
    permission_classes = [IsPersonnel]  # noqa: RUF012

    def post(self, request: Request) -> Response:
        principal = _actor(request)
        token = principal.subject_token
        subject = Subject.objects.filter(subject_token=token).first()
        if subject is None:
            raise Unprocessable("MB-4220: unknown subject")
        body = _payload(request)
        turn = run_turn(
            subject,
            str(body.get("message") or ""),
            session_id=str(body.get("session_id") or "") or None,
        )
        _audit(
            principal,
            action=AuditAction.INDIVIDUAL_READ,
            purpose=PurposeCode.SUBJECT_SELF_ACCESS,
            basis=LegalBasis.CONSENT,
            outcome="success",
            subject_token=token,
            detail={"crisis": turn.crisis, "accepted": turn.accepted},
        )
        return Response(
            {
                "session_id": turn.session_id,
                "reply": turn.reply,
                "crisis": turn.crisis,
                "accepted": turn.accepted,
            }
        )


class MeCheckinView(APIView):
    permission_classes = [IsPersonnel]  # noqa: RUF012

    def get(self, request: Request) -> Response:
        principal = _actor(request)
        token = principal.subject_token
        if not may_view_own_record(principal, subject_token=token):
            raise PermissionDenied("MB-4030: you are not permitted to perform this action")
        row = CheckinResponse.objects.filter(
            subject_token=token, observed_on=timezone.localdate()
        ).first()
        return Response(_checkin_body(row))

    def post(self, request: Request) -> Response:
        principal = _actor(request)
        token = principal.subject_token
        if not may_view_own_record(principal, subject_token=token):
            raise PermissionDenied("MB-4030: you are not permitted to perform this action")
        if not ConsentEntry.current_for(token).get(DataType.SELF_REPORT):
            raise Unprocessable("MB-4220: self-report consent is required")
        body = _payload(request)
        row, _created = CheckinResponse.objects.update_or_create(
            subject_token=token,
            observed_on=timezone.localdate(),
            defaults={
                "mood": _scale(body.get("mood")),
                "sleep_quality": _scale(body.get("sleep_quality")),
                "stress": _scale(body.get("stress")),
                "connection": _scale(body.get("connection")),
                "concern_tag": str(body.get("concern_tag") or "")[:32],
            },
        )
        _audit(
            principal,
            action=AuditAction.INDIVIDUAL_READ,
            purpose=PurposeCode.SUBJECT_SELF_ACCESS,
            basis=LegalBasis.CONSENT,
            outcome="success",
            subject_token=token,
            detail={"event": "checkin.recorded"},
        )
        return Response(_checkin_body(row), status=status.HTTP_201_CREATED)


class IngestCapturesView(APIView):
    permission_classes = [IsIntegration]  # noqa: RUF012

    def post(self, request: Request) -> Response:
        principal = _actor(request)
        body = _payload(request)
        token = str(body.get("subject_token") or "")
        batch_id = str(body.get("client_batch_id") or "")
        items = body.get("items")
        if not token or not batch_id or not isinstance(items, list):
            raise Unprocessable("MB-4220: subject_token, client_batch_id and items are required")
        receipt = ingest_capture_batch(
            subject_token=token, client_batch_id=batch_id, items=items
        )
        _audit(
            principal,
            action=AuditAction.ADMIN_ACTION,
            purpose=PurposeCode.DATA_INGESTION,
            basis=LegalBasis.CONSENT,
            outcome="success",
            subject_token=token,
            detail={"accepted": receipt.accepted_count, "batch": batch_id},
        )
        return Response(
            {
                "client_batch_id": receipt.client_batch_id,
                "accepted": receipt.accepted_count,
                "rejected_unconsented": receipt.rejected_unconsented,
                "rejected_stale": receipt.rejected_stale,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class RulesetProposeView(APIView):
    def get_permissions(self) -> list[BasePermission]:
        if self.request.method == "GET":
            return [IsRulesetReviewer()]
        return [IsWDECAuditor()]

    def get(self, request: Request) -> Response:
        principal = _actor(request)
        rows = RulesetProposal.objects.order_by("-proposed_at")[:50]
        _audit(
            principal,
            action=AuditAction.INDIVIDUAL_READ,
            purpose=PurposeCode.OVERSIGHT_AUDIT,
            basis=LegalBasis.LEGAL_OBLIGATION,
            outcome="success",
            detail={"count": len(rows)},
        )
        return Response(
            {
                "proposals": [
                    {
                        "id": row.id,
                        "version": row.version,
                        "digest": row.digest,
                        "status": row.status,
                        "clinical_approver": row.clinical_approver,
                        "wdec_approver": row.wdec_approver,
                        "proposed_at": row.proposed_at.isoformat(),
                    }
                    for row in rows
                ]
            }
        )

    def post(self, request: Request) -> Response:
        principal = _actor(request)
        body = _payload(request)
        proposal = register_proposal(
            version=str(body.get("version") or ""),
            digest=str(body.get("digest") or ""),
            signature=str(body.get("signature") or ""),
            signing_key_id=str(body.get("signing_key_id") or ""),
            proposed_by=principal.actor_id,
            artefact_path=str(body.get("artefact_path") or ""),
            shadow_report=cast(dict[str, object], body.get("shadow_report") or {}),
        )
        return Response(
            {"id": proposal.id, "status": proposal.status}, status=status.HTTP_201_CREATED
        )


class RulesetApproveView(APIView):
    permission_classes = [IsWDECAuditor]  # noqa: RUF012

    def post(self, request: Request, proposal_id: int) -> Response:
        return _approve(request, proposal_id)


class RulesetClinicalApproveView(APIView):
    permission_classes = [IsMedicalOfficer]  # noqa: RUF012

    def post(self, request: Request, proposal_id: int) -> Response:
        return _approve(request, proposal_id)


def _approve(request: Request, proposal_id: int) -> Response:
    principal = _actor(request)
    proposal = RulesetProposal.objects.filter(pk=proposal_id).first()
    if proposal is None:
        raise Unprocessable("MB-4220: unknown proposal")
    try:
        updated = approve_proposal(proposal, actor_id=principal.actor_id, role=principal.role)
    except ValueError as exc:
        raise Unprocessable(f"MB-4220: {exc}") from exc
    return Response({"id": updated.id, "status": updated.status})


def _resolve_rate_ok(actor_id: str) -> bool:
    hour_ago = timezone.now() - timedelta(hours=1)
    used = AuditEvent.objects.filter(
        actor_id=actor_id,
        action=AuditAction.IDENTITY_RESOLVE,
        occurred_at__gte=hour_ago,
    ).count()
    limits = settings.RATE_LIMITS
    if not isinstance(limits, dict):
        raise TypeError("RATE_LIMITS must be a mapping")
    return used < _as_int(limits["identity_resolve_per_officer_hour"])


def _scale(value: object) -> int | None:
    if value in (None, ""):
        return None
    number = _as_int(value)
    if number < 1 or number > 5:
        raise Unprocessable("MB-4220: check-in items must be 1-5")
    return number


def _as_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return int(str(value))
    return value


def _checkin_body(row: CheckinResponse | None) -> dict[str, object]:
    if row is None:
        return {
            "observed_on": None,
            "mood": None,
            "sleep_quality": None,
            "stress": None,
            "connection": None,
        }
    return {
        "observed_on": row.observed_on.isoformat(),
        "mood": row.mood,
        "sleep_quality": row.sleep_quality,
        "stress": row.stress,
        "connection": row.connection,
        "concern_tag": row.concern_tag,
    }
