"""RFC 9457 problem-detail error responses (SDD §6.6).

Two constraints shape this module.

The first is that error responses must not leak. A message like "no subject with
token X in unit 12BN" confirms both that the token exists and where it sits, to
a caller who was just told they are not allowed to know. Detail strings are
therefore drawn from a fixed table keyed by error code, and exception text from
deeper layers is logged rather than returned.

The second is that support staff need to triage without seeing anyone's data.
Every response carries a stable ``MB-xxxx`` code and the request id, which is
enough to find the corresponding log entry and audit row.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Final

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from ...observability.logging import request_id_var

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = logging.getLogger(__name__)

_BASE_URI: Final = "https://manobal.gov.in/problems"

#: Safe, caller-facing text per code. Anything absent here is reported as a
#: generic failure, which is the correct default for an error nobody anticipated.
_DETAILS: Final[Mapping[str, str]] = {
    "MB-4010": "Authentication failed.",
    "MB-4011": "Authentication failed.",
    "MB-4012": "This role requires a second authentication factor.",
    "MB-4013": "Your session has expired. Please sign in again.",
    "MB-4030": "You are not permitted to perform this action.",
    "MB-4031": "You are not permitted to perform this action.",
    "MB-4032": "This information is not available to you.",
    "MB-4040": "Not found.",
    "MB-4090": "This request conflicts with the current state.",
    "MB-4220": "The request was understood but could not be processed.",
    "MB-4290": "Too many requests. Please slow down.",
    "MB-5000": "Something went wrong. The incident has been recorded.",
}

_STATUS_TO_CODE: Final[Mapping[int, str]] = {
    401: "MB-4010",
    403: "MB-4030",
    404: "MB-4040",
    409: "MB-4090",
    422: "MB-4220",
    429: "MB-4290",
}


def _code_for(exc: Exception, status_code: int) -> str:
    """Recover an ``MB-xxxx`` code from the exception, or fall back by status.

    Views raise with the code as a prefix — ``"MB-4032: ..."`` — which keeps the
    code next to the condition that produced it rather than in a mapping table
    that drifts away from the code it describes.
    """
    text = str(getattr(exc, "detail", "") or exc)
    if text.startswith("MB-") and ":" in text:
        candidate = text.split(":", 1)[0].strip()
        if candidate in _DETAILS:
            return candidate
    return _STATUS_TO_CODE.get(status_code, "MB-5000")


def problem_detail_handler(exc: Exception, context: dict[str, Any]) -> Response:
    """Render any exception as a problem document."""
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()
    elif isinstance(exc, ValidationError):
        exc = exceptions.ValidationError(detail=getattr(exc, "messages", ["invalid"]))

    response = drf_exception_handler(exc, context)
    status_code = (
        response.status_code if response is not None else status.HTTP_500_INTERNAL_SERVER_ERROR
    )
    code = _code_for(exc, status_code)

    if status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        # Log the real cause; return the generic text. The redaction filter
        # scrubs the record before it reaches a handler.
        logger.exception("unhandled error serving %s", context.get("request"))

    body: dict[str, Any] = {
        "type": f"{_BASE_URI}/{code.lower()}",
        "title": _DETAILS.get(code, _DETAILS["MB-5000"]),
        "status": status_code,
        "code": code,
        "request_id": request_id_var.get(),
    }

    # Field-level validation errors are safe to return: they describe the
    # caller's own submission, not somebody else's record.
    if isinstance(exc, exceptions.ValidationError):
        body["errors"] = exc.detail

    return Response(body, status=status_code, content_type="application/problem+json")
