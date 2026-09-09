"""URL configuration for the identity enclave."""

from __future__ import annotations

from django.http import HttpRequest, JsonResponse
from django.urls import path


def healthz(_: HttpRequest) -> JsonResponse:
    """Liveness only. Says nothing about the vault's contents or size."""
    return JsonResponse({"status": "ok", "zone": 3})


urlpatterns = [path("healthz", healthz, name="healthz")]
