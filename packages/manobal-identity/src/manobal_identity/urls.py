"""URL configuration for the identity enclave."""

from __future__ import annotations

from django.http import HttpRequest, JsonResponse
from django.urls import path

from manobal_identity.api.views import BreakGlassView, ResolveView, TokeniseView


def healthz(_: HttpRequest) -> JsonResponse:
    """Liveness only. Says nothing about the vault's contents or size."""
    return JsonResponse({"status": "ok", "zone": 3})


urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("v1/identity/tokenise", TokeniseView.as_view(), name="identity-tokenise"),
    path("v1/identity/resolve", ResolveView.as_view(), name="identity-resolve"),
    path("v1/identity/break-glass", BreakGlassView.as_view(), name="identity-break-glass"),
]
