"""The Zone 2 HTTP surface: consent, casework, aggregates, oversight.

Each view does three things in the same order: identify the caller, ask a
predicate, write an audit row. The audit happens even on a denial — a refused
read is as interesting as a permitted one, and a path that cannot be audited
must not run.
"""

from __future__ import annotations

from typing import Any, cast

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from manobal_core.alerting.acute import raise_acute
from manobal_core.apps.authz.permissions import (
    IsCaseOfficer,
    IsCommander,
    IsIntegration,
    IsPersonnel,
    IsWDECAuditor,
    IsWelfareOfficer,
    principal_of,
)
from manobal_core.apps.authz.predicates import (
    DENY_K_ANON,
    Decision,
    may_view_aggregate,
    may_view_flag,
    may_view_own_record,
    mfa_is_satisfied,
)
from manobal_core.apps.authz.principal import Principal
from manobal_core.apps.governance.aggregation import ensure_aggregate, public_aggregate_payload
from manobal_core.apps.governance.enums import (
    AuditAction,
    CaseStatus,
    DataType,
    ErasureStatus,
    GrantScope,
    LegalBasis,
    PurposeCode,
    Role,
    Tier,
)
from manobal_core.apps.governance.models import (
    AccessGrant,
    AuditAnchor,
    AuditEvent,
    Case,
    ConsentEntry,
    ConsentTextVersion,
    ErasureRequest,
    OfficerProfile,
    RiskAssessmentRecord,
    Subject,
    Unit,
)
from manobal_core.ingest.identity import get_identity
from manobal_core.ingest.pipeline import ingest_hrms_batch
from manobal_core.observability.logging import request_id_var


class Unprocessable(APIException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "MB-4220: the request could not be processed"
    default_code = "MB-4220"


class TooMany(APIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "MB-4290: too many requests"
    default_code = "MB-4290"


def _actor(request: Request) -> Principal:
    principal = principal_of(request)
    if principal is None:
        raise PermissionDenied("MB-4010: authentication failed")
    return principal


def _audit(
    principal: Principal,
    *,
    action: str,
    purpose: str,
    basis: str,
    outcome: str,
    subject_token: str | None = None,
    detail: dict[str, object] | None = None,
) -> None:
    AuditEvent.record(
        actor_id=principal.actor_id,
        actor_role=principal.role,
        action=action,
        subject_token=subject_token,
        purpose_code=purpose,
        legal_basis=basis,
        outcome=outcome,
        request_id=request_id_var.get() or None,
        detail=detail or {},
    )


def _mfa(principal: Principal) -> bool:
    oidc = cast(dict[str, Any], settings.OIDC)
    return mfa_is_satisfied(
        principal,
        required_roles=cast(list[str], oidc["MFA_REQUIRED_ROLES"]),
        accepted_methods=cast(list[str], oidc["SECOND_FACTOR_METHODS"]),
    )


def _payload(request: Request) -> dict[str, Any]:
    data = request.data
    if not isinstance(data, dict):
        raise Unprocessable("MB-4220: expected an object")
    return data


def _actor_unit_path(principal: Principal) -> str:
    if principal.unit_code:
        unit = Unit.objects.filter(code=principal.unit_code).first()
        if unit is not None:
            return unit.path
    profile = (
        OfficerProfile.objects.filter(actor_id=principal.actor_id).select_related("unit").first()
    )
    return profile.unit.path if profile is not None else ""


class ConsentView(APIView):
    permission_classes = [IsPersonnel]  # noqa: RUF012

    def get(self, request: Request) -> Response:
        principal = _actor(request)
        token = principal.subject_token
        decision = may_view_own_record(principal, subject_token=token)
        if not decision:
            _audit(
                principal,
                action=AuditAction.ACCESS_DENIED,
                purpose=PurposeCode.CONSENT_MANAGEMENT,
                basis=LegalBasis.SUBJECT_REQUEST,
                outcome="denied",
                detail={"reason": decision.reason},
            )
            raise PermissionDenied("MB-4030: you are not permitted to perform this action")
        state = ConsentEntry.current_for(token)
        _audit(
            principal,
            action=AuditAction.INDIVIDUAL_READ,
            purpose=PurposeCode.CONSENT_MANAGEMENT,
            basis=LegalBasis.SUBJECT_REQUEST,
            outcome="success",
            subject_token=token,
        )
        return Response({"subject_token": token, "consents": state})

    def post(self, request: Request) -> Response:
        principal = _actor(request)
        token = principal.subject_token
        decision = may_view_own_record(principal, subject_token=token)
        if not decision:
            raise PermissionDenied("MB-4030: you are not permitted to perform this action")
        body = _payload(request)
        data_type = str(body.get("data_type", ""))
        if data_type not in DataType.values:
            raise Unprocessable("MB-4220: unknown data type")
        if "granted" not in body:
            raise Unprocessable("MB-4220: granted is required")
        granted = bool(body.get("granted"))
        text = (
            ConsentTextVersion.objects.filter(retired_at__isnull=True)
            .order_by("-effective_from")
            .first()
        )
        if text is None:
            raise Unprocessable("MB-4220: no active consent text")
        entry = ConsentEntry.objects.create(
            subject_token=token,
            data_type=data_type,
            granted=granted,
            consent_text=text,
            method=str(body.get("method") or "app"),
        )
        if not granted:
            erasure = ErasureRequest.objects.create(
                subject_token=token,
                data_type=data_type,
                status=ErasureStatus.INTENT_RECORDED,
            )
            if not getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
                from manobal_core.tasks import advance_erasure_task

                advance_erasure_task.delay(erasure.id)
        _audit(
            principal,
            action=AuditAction.CONSENT_CHANGE,
            purpose=PurposeCode.CONSENT_MANAGEMENT,
            basis=LegalBasis.SUBJECT_REQUEST,
            outcome="success",
            subject_token=token,
            detail={"data_type": data_type, "granted": granted},
        )
        return Response(
            {
                "data_type": entry.data_type,
                "granted": entry.granted,
                "recorded_at": entry.recorded_at.isoformat(),
            },
            status=status.HTTP_201_CREATED,
        )


class MeAssessmentView(APIView):
    permission_classes = [IsPersonnel]  # noqa: RUF012

    def get(self, request: Request) -> Response:
        principal = _actor(request)
        token = principal.subject_token
        if not may_view_own_record(principal, subject_token=token):
            raise PermissionDenied("MB-4030: you are not permitted to perform this action")
        record = (
            RiskAssessmentRecord.objects.filter(subject_token=token)
            .order_by("-assessed_at", "-id")
            .first()
        )
        _audit(
            principal,
            action=AuditAction.INDIVIDUAL_READ,
            purpose=PurposeCode.SUBJECT_SELF_ACCESS,
            basis=LegalBasis.SUBJECT_REQUEST,
            outcome="success",
            subject_token=token,
        )
        if record is None:
            return Response({"tier": None, "contributing_categories": []})
        return Response(
            {
                "tier": record.tier,
                "contributing_categories": record.contributing_categories,
                "assessed_at": record.assessed_at.isoformat(),
                "acute_override": record.acute_override,
            }
        )


class MeSosView(APIView):
    permission_classes = [IsPersonnel]  # noqa: RUF012

    def post(self, request: Request) -> Response:
        principal = _actor(request)
        token = principal.subject_token
        if not may_view_own_record(principal, subject_token=token):
            raise PermissionDenied("MB-4030: you are not permitted to perform this action")
        subject = Subject.objects.filter(subject_token=token).first()
        if subject is None:
            raise NotFound("MB-4040: not found")
        result = raise_acute(
            subject,
            signal_code="explicit_sos",
            source="self_report",
            self_initiated=True,
        )
        _audit(
            principal,
            action=AuditAction.ALERT_DISPATCH,
            purpose=PurposeCode.ACUTE_RESPONSE,
            basis=LegalBasis.VITAL_INTEREST,
            outcome="success",
            subject_token=token,
            detail={"accepted": True, "case_id": result.case.id if result.case else None},
        )
        return Response({"accepted": True}, status=status.HTTP_202_ACCEPTED)


class OfficerQueueView(APIView):
    permission_classes = [IsCaseOfficer]  # noqa: RUF012

    def get(self, request: Request) -> Response:
        principal = _actor(request)
        cases = (
            Case.objects.filter(
                assigned_officer_id=principal.actor_id,
                status__in={CaseStatus.OPEN, CaseStatus.CONTACTED, CaseStatus.CONTESTED},
            )
            .select_related("unit", "assessment")
            .order_by("sla_due_at", "id")
        )
        items = []
        for case in cases:
            decision = _case_flag_decision(principal, case)
            if not decision:
                continue
            items.append(_case_summary(case))
        _audit(
            principal,
            action=AuditAction.INDIVIDUAL_READ,
            purpose=PurposeCode.CASE_REVIEW,
            basis=LegalBasis.CONSENT,
            outcome="success",
            detail={"count": len(items)},
        )
        return Response({"cases": items})


class OfficerCaseView(APIView):
    permission_classes = [IsCaseOfficer]  # noqa: RUF012

    def get(self, request: Request, case_id: int) -> Response:
        principal, case = _authorised_case(request, case_id)
        _audit(
            principal,
            action=AuditAction.INDIVIDUAL_READ,
            purpose=PurposeCode.CASE_REVIEW,
            basis=LegalBasis.CONSENT,
            outcome="success",
            subject_token=case.subject_token,
            detail={"case_id": case.id},
        )
        return Response(_case_detail(case))


class OfficerContactView(APIView):
    permission_classes = [IsWelfareOfficer]  # noqa: RUF012

    def post(self, request: Request, case_id: int) -> Response:
        principal, case = _authorised_case(request, case_id)
        if case.first_contact_at is None:
            case.first_contact_at = timezone.now()
        case.status = CaseStatus.CONTACTED
        case.save(update_fields=["first_contact_at", "status"])
        from manobal_core.alerting.dispatch import acknowledge_case_alerts

        acknowledge_case_alerts(case, actor_id=principal.actor_id)
        _audit(
            principal,
            action=AuditAction.OFFICER_DECISION,
            purpose=PurposeCode.CASE_REVIEW,
            basis=LegalBasis.CONSENT,
            outcome="success",
            subject_token=case.subject_token,
            detail={"case_id": case.id, "action": "contact", "status": case.status},
        )
        return Response(_case_detail(case))


class OfficerDecisionView(APIView):
    permission_classes = [IsWelfareOfficer]  # noqa: RUF012

    def post(self, request: Request, case_id: int) -> Response:
        principal, case = _authorised_case(request, case_id)
        body = _payload(request)
        outcome = str(body.get("outcome_code", "")).strip()
        rationale = str(body.get("rationale", "")).strip()
        if not outcome or not rationale:
            raise Unprocessable("MB-4220: outcome_code and rationale are required")
        closed = str(body.get("status") or CaseStatus.RESOLVED)
        if closed not in {CaseStatus.RESOLVED, CaseStatus.NO_ACTION}:
            raise Unprocessable("MB-4220: status must be resolved or no_action")
        case.outcome_code = outcome
        case.officer_rationale = rationale
        case.status = closed
        case.closed_at = timezone.now()
        case.save(update_fields=["outcome_code", "officer_rationale", "status", "closed_at"])
        AccessGrant.objects.filter(case=case, revoked_at__isnull=True).update(
            revoked_at=timezone.now()
        )
        _audit(
            principal,
            action=AuditAction.OFFICER_DECISION,
            purpose=PurposeCode.CASE_REVIEW,
            basis=LegalBasis.CONSENT,
            outcome="success",
            subject_token=case.subject_token,
            detail={"case_id": case.id, "action": "decide", "status": case.status},
        )
        return Response(_case_detail(case))


class CommanderAggregateView(APIView):
    permission_classes = [IsCommander]  # noqa: RUF012

    def get(self, request: Request) -> Response:
        principal = _actor(request)
        unit_code = str(request.query_params.get("unit") or principal.unit_code)
        unit = Unit.objects.filter(code=unit_code, force_code=principal.force_code).first()
        if unit is None:
            raise NotFound("MB-4040: not found")
        actor_path = _actor_unit_path(principal)
        k_threshold = int(settings.PRIVACY["K_ANONYMITY_THRESHOLD"])
        # Headcount is used only to decide whether the predicate allows the
        # *request*. The payload still withholds numbers when the stored rollup
        # is suppressed.
        headcount = Subject.objects.filter(unit=unit).count()
        decision = may_view_aggregate(
            principal,
            actor_unit_path=actor_path,
            target_unit_path=unit.path,
            cohort_size=headcount,
            k_threshold=k_threshold,
        )
        if not decision and decision.reason != DENY_K_ANON:
            _audit(
                principal,
                action=AuditAction.ACCESS_DENIED,
                purpose=PurposeCode.OVERSIGHT_AUDIT,
                basis=LegalBasis.EMPLOYMENT,
                outcome="denied",
                detail={"reason": decision.reason, "unit": unit.code},
            )
            raise PermissionDenied("MB-4032: this information is not available to you")
        aggregate = ensure_aggregate(unit)
        payload = public_aggregate_payload(aggregate)
        _audit(
            principal,
            action=AuditAction.INDIVIDUAL_READ
            if not aggregate.suppressed
            else AuditAction.AGGREGATE_SUPPRESSED,
            purpose=PurposeCode.OVERSIGHT_AUDIT,
            basis=LegalBasis.EMPLOYMENT,
            outcome="success",
            detail={"unit": unit.code, "suppressed": aggregate.suppressed},
        )
        return Response(payload)


class WdecBreakGlassView(APIView):
    permission_classes = [IsWDECAuditor]  # noqa: RUF012

    def post(self, request: Request) -> Response:
        from manobal_core.apps.api.views_oversight import WdecBreakGlassInvokeView

        return WdecBreakGlassInvokeView().post(request)

    def get(self, request: Request) -> Response:
        principal = _actor(request)
        rows = AccessGrant.objects.filter(
            break_glass=True, wdec_reviewed_at__isnull=True
        ).order_by("-granted_at")
        _audit(
            principal,
            action=AuditAction.INDIVIDUAL_READ,
            purpose=PurposeCode.OVERSIGHT_AUDIT,
            basis=LegalBasis.LEGAL_OBLIGATION,
            outcome="success",
            detail={"count": rows.count()},
        )
        return Response(
            {
                "grants": [
                    {
                        "id": row.id,
                        "grantee_id": row.grantee_id,
                        "justification": row.justification,
                        "granted_at": row.granted_at.isoformat(),
                        "case_id": row.case_id,
                    }
                    for row in rows
                ]
            }
        )


class IngestHrmsView(APIView):
    permission_classes = [IsIntegration]  # noqa: RUF012

    def post(self, request: Request) -> Response:
        principal = _actor(request)
        body = _payload(request)
        records = body.get("records")
        if not isinstance(records, list):
            raise Unprocessable("MB-4220: records must be a list")
        batch = ingest_hrms_batch(
            source_system=str(body.get("source_system") or "hrms"),
            contract_version=str(body.get("contract_version") or ""),
            records=[row for row in records if isinstance(row, dict)],
            identity=get_identity(),
        )
        _audit(
            principal,
            action=AuditAction.ADMIN_ACTION,
            purpose=PurposeCode.DATA_INGESTION,
            basis=LegalBasis.EMPLOYMENT,
            outcome="success",
            detail={
                "batch_id": batch.id,
                "status": batch.status,
                "accepted": batch.accepted_count,
                "quarantined": batch.quarantined_count,
            },
        )
        return Response(
            {
                "batch_id": batch.id,
                "status": batch.status,
                "accepted": batch.accepted_count,
                "quarantined": batch.quarantined_count,
            },
            status=(
                status.HTTP_202_ACCEPTED
                if batch.status != "rejected"
                else status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
        )


class WdecAnchorsView(APIView):
    permission_classes = [IsWDECAuditor]  # noqa: RUF012

    def get(self, request: Request) -> Response:
        principal = _actor(request)
        rows = AuditAnchor.objects.order_by("-anchored_at")[:50]
        _audit(
            principal,
            action=AuditAction.INDIVIDUAL_READ,
            purpose=PurposeCode.OVERSIGHT_AUDIT,
            basis=LegalBasis.LEGAL_OBLIGATION,
            outcome="success",
        )
        return Response(
            {
                "anchors": [
                    {
                        "anchored_at": row.anchored_at.isoformat(),
                        "head_hash": row.head_hash,
                        "event_count": row.event_count,
                        "published_to": row.published_to,
                    }
                    for row in rows
                ]
            }
        )


def _load_case(case_id: int) -> Case:
    try:
        return (
            Case.objects.select_related("unit", "assessment", "assigned_officer")
            .prefetch_related("recommendations")
            .get(pk=case_id)
        )
    except Case.DoesNotExist as exc:
        raise NotFound("MB-4040: not found") from exc


def _authorised_case(request: Request, case_id: int) -> tuple[Principal, Case]:
    principal = _actor(request)
    case = _load_case(case_id)
    decision = _case_flag_decision(principal, case)
    if not decision:
        _audit(
            principal,
            action=AuditAction.ACCESS_DENIED,
            purpose=PurposeCode.CASE_REVIEW,
            basis=LegalBasis.CONSENT,
            outcome="denied",
            subject_token=case.subject_token,
            detail={"reason": decision.reason},
        )
        raise PermissionDenied("MB-4032: this information is not available to you")
    return principal, case


def _flag_grant_scopes(principal: Principal) -> tuple[str, ...]:
    """A clinical referral is a live grant for the medical officer only.

    Welfare officers keep working from FLAG grants created at case open. A
    medical officer is never the assignee; their window is the referral grant
    itself (or a T4 FLAG page). Treating only FLAG as live left referred T3
    cases visible in the clinical queue and 403 on the case they just opened.
    """
    if principal.role is Role.MEDICAL_OFFICER:
        return (GrantScope.FLAG, GrantScope.CLINICAL_REFERRAL)
    return (GrantScope.FLAG,)


def _case_flag_decision(principal: Principal, case: Case) -> Decision:
    profile = OfficerProfile.objects.filter(actor_id=principal.actor_id).first()
    grant_live = AccessGrant.objects.filter(
        grantee_id=principal.actor_id,
        subject_token=case.subject_token,
        scope__in=_flag_grant_scopes(principal),
        revoked_at__isnull=True,
        expires_at__gt=timezone.now(),
    ).exists()
    return may_view_flag(
        principal,
        subject_force_code=case.unit.force_code,
        subject_unit_path=case.unit.path,
        actor_unit_path=_actor_unit_path(principal),
        tier=Tier(case.tier_at_open),
        officer_is_certified=profile.is_certified if profile is not None else False,
        has_live_grant=grant_live,
        mfa_satisfied=_mfa(principal),
    )


def _case_summary(case: Case) -> dict[str, object]:
    return {
        "id": case.id,
        "subject_token": case.subject_token,
        "tier": case.tier_at_open,
        "contributing_categories": case.contributing_categories,
        "status": case.status,
        "sla_due_at": case.sla_due_at.isoformat(),
        "opened_at": case.opened_at.isoformat(),
    }


def _case_detail(case: Case) -> dict[str, object]:
    body = _case_summary(case)
    body.update(
        {
            "first_contact_at": (
                case.first_contact_at.isoformat() if case.first_contact_at else None
            ),
            "closed_at": case.closed_at.isoformat() if case.closed_at else None,
            "outcome_code": case.outcome_code,
            "officer_rationale": case.officer_rationale,
            "contested_at": case.contested_at.isoformat() if case.contested_at else None,
            "contest_note": case.contest_note,
            "recommendations": [
                {
                    "code": row.code,
                    "rationale": row.rationale,
                    "priority": row.priority,
                    "accepted": row.accepted,
                }
                for row in case.recommendations.all()
            ],
        }
    )
    return body
