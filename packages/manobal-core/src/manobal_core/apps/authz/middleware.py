"""Scope the authenticated actor to the request that established it.

The actor is bound to the logging context by
:class:`~.authentication.OIDCBearerAuthentication`, at the point where the token
is verified and the principal comes into existence. That is inside the view,
because that is where DRF authenticates, and it is early enough for the log
lines that matter — everything the view goes on to do.

What is left for middleware is the other half: making sure the binding does not
outlive the request. Workers are reused, and a context variable left set by one
request is inherited by the next one to land on that thread. The failure mode is
quiet and bad: log lines for an unauthenticated or failed request, attributed to
whichever officer happened to be served just before. An audit trail that names
the wrong person is worse than one that names nobody.

This middleware never creates a principal and never authenticates anything.
Authentication belongs to :mod:`.authentication`, where the signature is
actually verified.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...observability.logging import actor_id_var, actor_role_var

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.http import HttpRequest, HttpResponse


class PrincipalMiddleware:
    """Opens a clean actor context per request and tears it down afterwards."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Start from empty rather than from whatever the previous request left
        # behind, so an unauthenticated request cannot inherit an actor.
        id_token = actor_id_var.set("")
        role_token = actor_role_var.set("")
        try:
            return self.get_response(request)
        finally:
            # `finally`, not a trailing statement: a view that raises must not
            # leak its actor into the next request handled by this worker.
            actor_id_var.reset(id_token)
            actor_role_var.reset(role_token)
