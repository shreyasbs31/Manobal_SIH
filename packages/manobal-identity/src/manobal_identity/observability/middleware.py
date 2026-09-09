"""Per-request correlation for the enclave.

Every request here is a boundary crossing, so every log line one produces
should be traceable to the request that caused it without the correlation id
having to be threaded through each call by hand.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from typing import Final

from django.http import HttpRequest, HttpResponse

REQUEST_ID_HEADER: Final = "HTTP_X_REQUEST_ID"
_context: Final = logging.getLogRecordFactory()


class RequestContextMiddleware:
    """Binds a request id to every record emitted while the request runs."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self._get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = request.META.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        request.request_id = request_id  # type: ignore[attr-defined]

        def factory(*args: object, **kwargs: object) -> logging.LogRecord:
            record = _context(*args, **kwargs)
            record.request_id = request_id
            return record

        logging.setLogRecordFactory(factory)
        try:
            response = self._get_response(request)
        finally:
            logging.setLogRecordFactory(_context)
        response["X-Request-ID"] = request_id
        return response
