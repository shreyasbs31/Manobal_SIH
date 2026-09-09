"""RFC 9457 problem details for the enclave. Copied, not imported, from Zone 2.

A shared error helper would pull ``manobal_core`` into this image. The
duplication is forty lines; the import would be a zone crossing.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from typing import Any, Final

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from manobal_identity.apps.vault.services import ResolutionDeniedError, SubjectNotFoundError
from manobal_identity.grants.assertion import AssertionRejectedError

logger = logging.getLogger(__name__)

_BASE_URI: Final = "https://manobal.gov.in/problems"

_DETAILS: Final[Mapping[str, str]] = {
    "MB-3001": "The grant assertion was not accepted.",
    "MB-3002": "The grant assertion was not accepted.",
    "MB-3003": "The grant assertion was not accepted.",
    "MB-3004": "The grant assertion was not accepted.",
    "MB-3005": "The grant assertion was not accepted.",
    "MB-3006": "The grant assertion was not accepted.",
    "MB-3007": "The grant assertion was not accepted.",
    "MB-3008": "The grant assertion was not accepted.",
    "MB-3009": "The grant assertion was not accepted.",
    "MB-3010": "The grant assertion was not accepted.",
    "MB-3011": "The grant assertion was not accepted.",
    "MB-3012": "The grant assertion was not accepted.",
    "MB-3013": "The grant assertion was not accepted.",
    "MB-3201": "Too many requests. Please slow down.",
    "MB-3202": "Too many requests. Please slow down.",
    "MB-3203": "Too many requests. Please slow down.",
    "MB-3404": "Not found.",
    "MB-4010": "Authentication failed.",
    "MB-4011": "Authentication failed.",
    "MB-4030": "You are not permitted to perform this action.",
    "MB-4040": "Not found.",
    "MB-4220": "The request was understood but could not be processed.",
    "MB-4290": "Too many requests. Please slow down.",
    "MB-5000": "Something went wrong. The incident has been recorded.",
}

_CODE_IN_TEXT = re.compile(r"\b(MB-\d{4})\b")
_RATE_LIMITS = frozenset({"MB-3201", "MB-3202", "MB-3203", "MB-4290"})

_STATUS_TO_CODE: Final[Mapping[int, str]] = {
    401: "MB-4010",
    403: "MB-4030",
    404: "MB-4040",
    422: "MB-4220",
    429: "MB-4290",
}


def _code_for(exc: Exception, status_code: int) -> str:
    if isinstance(exc, AssertionRejectedError):
        return exc.reason.value
    if isinstance(exc, ResolutionDeniedError):
        return exc.reason if exc.reason in _DETAILS else "MB-4030"
    if isinstance(exc, SubjectNotFoundError):
        return "MB-3404"
    text = str(getattr(exc, "detail", "") or exc)
    found = _CODE_IN_TEXT.search(text)
    if found and found.group(1) in _DETAILS:
        return found.group(1)
    return _STATUS_TO_CODE.get(status_code, "MB-5000")


def _request_id(context: dict[str, Any]) -> str:
    request = context.get("request")
    return str(getattr(request, "request_id", "") or "")


def problem_detail_handler(exc: Exception, context: dict[str, Any]) -> Response:
    original = exc
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()
    elif isinstance(exc, ValidationError):
        exc = exceptions.ValidationError(detail=getattr(exc, "messages", ["invalid"]))
    elif isinstance(exc, AssertionRejectedError):
        exc = exceptions.PermissionDenied(detail=str(exc))
    elif isinstance(exc, ResolutionDeniedError):
        if exc.reason in _RATE_LIMITS:
            exc = exceptions.Throttled(detail=str(exc))
        else:
            exc = exceptions.PermissionDenied(detail=str(exc))
    elif isinstance(exc, SubjectNotFoundError):
        exc = exceptions.NotFound()

    response = drf_exception_handler(exc, context)
    status_code = (
        response.status_code if response is not None else status.HTTP_500_INTERNAL_SERVER_ERROR
    )
    code = _code_for(original, status_code)

    if status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        logger.exception("unhandled error serving %s", context.get("request"))

    body: dict[str, Any] = {
        "type": f"{_BASE_URI}/{code.lower()}",
        "title": _DETAILS.get(code, _DETAILS["MB-5000"]),
        "status": status_code,
        "code": code,
        "request_id": _request_id(context),
    }
    if isinstance(exc, exceptions.ValidationError):
        body["errors"] = exc.detail

    return Response(body, status=status_code, content_type="application/problem+json")
