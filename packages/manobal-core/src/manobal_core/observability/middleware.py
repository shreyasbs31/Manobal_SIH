"""Per-request correlation context.

Sits early in the middleware chain so that anything logged during a request —
including an authentication failure, which happens before a principal exists —
carries the same request id as the response the caller receives.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from .logging import actor_id_var, actor_role_var, request_id_var

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.http import HttpRequest, HttpResponse

#: Inbound header is accepted so a trace started at the gateway continues here,
#: but the value is never trusted for anything but correlation: it is not an
#: identifier, not a capability, and never reaches a query.
_HEADER = "HTTP_X_REQUEST_ID"
_MAX_LEN = 64


class RequestContextMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        incoming = request.META.get(_HEADER, "")
        request_id = incoming[:_MAX_LEN] if incoming.isascii() and incoming else uuid.uuid4().hex
        token = request_id_var.set(request_id)
        request.request_id = request_id  # type: ignore[attr-defined]
        try:
            response = self.get_response(request)
            response["X-Request-Id"] = request_id
            return response
        finally:
            # Reset on the way out so a pooled worker thread cannot leak one
            # request's correlation context into the next request it serves.
            # The header is set above, inside the try: a view that raises must
            # not leave ``response`` unbound, and must not leak this request's
            # id into the next one either.
            request_id_var.reset(token)
            actor_id_var.set("")
            actor_role_var.set("")
