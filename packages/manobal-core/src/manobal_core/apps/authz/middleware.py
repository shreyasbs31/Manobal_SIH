"""Bind the authenticated principal to the logging context.

DRF authenticates inside the view, which is too late for any log line emitted by
middleware below it. This middleware runs after the response has been produced
and copies the principal — if one was established — into the correlation
context, so the request's access log carries the actor.

It never *creates* a principal and never authenticates anything. Authentication
belongs to :mod:`.authentication`, where the signature is actually verified.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...observability.logging import actor_id_var, actor_role_var
from .principal import Principal

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.http import HttpRequest, HttpResponse


class PrincipalMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        principal = getattr(request, "principal", None)
        if isinstance(principal, Principal):
            actor_id_var.set(principal.actor_id)
            actor_role_var.set(principal.role.value)
        return response
