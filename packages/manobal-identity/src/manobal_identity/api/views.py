"""The three methods §4.9 permits, and no others."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Final

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from manobal_identity.api.runtime import get_vault
from manobal_identity.api.workload import (
    SCOPE_BREAK_GLASS,
    SCOPE_RESOLVE,
    SCOPE_TOKENISE,
    WorkloadAuthentication,
    WorkloadPrincipal,
    WorkloadScopePermission,
)
from manobal_identity.apps.vault.services import CallerContext, PersonRecord, ResolvedIdentity
from manobal_identity.grants.assertion import Operation


class Unprocessable(APIException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "MB-4220: the request could not be processed"
    default_code = "MB-4220"


_NO_STORE: Final = {"Cache-Control": "no-store", "Pragma": "no-cache"}
_PERSON_FIELDS: Final = (
    "service_no",
    "full_name",
    "rank_code",
    "mobile_e164",
    "unit_code",
    "unit_path",
    "force_code",
    "enrolled_on",
)
MAX_TOKENISE_BATCH: Final = 500


class IdentityAPIView(APIView):
    authentication_classes = [WorkloadAuthentication]  # noqa: RUF012
    permission_classes = [WorkloadScopePermission]  # noqa: RUF012
    required_scope: str = ""

    def caller(self, request: Request) -> CallerContext:
        principal = request.user
        assert isinstance(principal, WorkloadPrincipal)
        return CallerContext(
            workload_id=principal.workload_id,
            source_ip=request.META.get("REMOTE_ADDR"),
        )


class TokeniseView(IdentityAPIView):
    required_scope = SCOPE_TOKENISE

    def post(self, request: Request) -> Response:
        people = _parse_people(request.data)
        tokens = get_vault().tokenise(people, self.caller(request))
        return Response({"tokens": tokens}, status=status.HTTP_200_OK)


class ResolveView(IdentityAPIView):
    required_scope = SCOPE_RESOLVE

    def post(self, request: Request) -> Response:
        assertion = _parse_assertion(request.data)
        identity = get_vault().resolve(
            assertion, operation=Operation.RESOLVE, caller=self.caller(request)
        )
        return Response(_identity_body(identity), status=status.HTTP_200_OK, headers=_NO_STORE)


class BreakGlassView(IdentityAPIView):
    required_scope = SCOPE_BREAK_GLASS

    def post(self, request: Request) -> Response:
        assertion = _parse_assertion(request.data)
        identity = get_vault().resolve(
            assertion, operation=Operation.BREAK_GLASS, caller=self.caller(request)
        )
        return Response(_identity_body(identity), status=status.HTTP_200_OK, headers=_NO_STORE)


def _parse_assertion(data: Any) -> str:
    if not isinstance(data, dict):
        raise Unprocessable("MB-4220: expected an object")
    assertion = data.get("assertion")
    if not isinstance(assertion, str) or not assertion.strip():
        raise Unprocessable("MB-4220: assertion is required")
    return assertion.strip()


def _parse_people(data: Any) -> list[PersonRecord]:
    if not isinstance(data, dict):
        raise Unprocessable("MB-4220: expected an object")
    raw = data.get("people")
    if not isinstance(raw, list) or not raw:
        raise Unprocessable("MB-4220: people must be a non-empty list")
    if len(raw) > MAX_TOKENISE_BATCH:
        raise Unprocessable("MB-4220: batch exceeds the enrolment ceiling")
    return [_parse_person(item) for item in raw]


def _parse_person(item: Any) -> PersonRecord:
    if not isinstance(item, dict):
        raise Unprocessable("MB-4220: each person must be an object")
    missing = [field for field in _PERSON_FIELDS if not item.get(field)]
    if missing:
        raise Unprocessable("MB-4220: person record is incomplete")
    try:
        enrolled = date.fromisoformat(str(item["enrolled_on"]))
    except ValueError as exc:
        raise Unprocessable("MB-4220: enrolled_on must be an ISO date") from exc
    return PersonRecord(
        service_no=str(item["service_no"]),
        full_name=str(item["full_name"]),
        rank_code=str(item["rank_code"]),
        mobile_e164=str(item["mobile_e164"]),
        unit_code=str(item["unit_code"]),
        unit_path=str(item["unit_path"]),
        force_code=str(item["force_code"]),
        enrolled_on=datetime.combine(enrolled, datetime.min.time()),
    )


def _identity_body(identity: ResolvedIdentity) -> dict[str, str]:
    return {
        "subject_token": identity.subject_token,
        "service_no": identity.service_no,
        "full_name": identity.full_name,
        "rank_code": identity.rank_code,
        "mobile_e164": identity.mobile_e164,
        "unit_code": identity.unit_code,
        "force_code": identity.force_code,
    }
