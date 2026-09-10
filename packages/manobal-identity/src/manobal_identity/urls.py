"""URL configuration for the identity enclave."""

from __future__ import annotations

from django.http import HttpRequest, JsonResponse
from django.urls import path

from manobal_identity.api.views import BreakGlassView, ResolveView, TokeniseView
from manobal_identity.api.views_enrolment import EnrolmentOtpRequestView, EnrolmentOtpVerifyView


def healthz(_: HttpRequest) -> JsonResponse:
    """Liveness only. Says nothing about the vault's contents or size."""
    return JsonResponse({"status": "ok", "zone": 3})


urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("v1/identity/tokenise", TokeniseView.as_view(), name="identity-tokenise"),
    path("v1/identity/resolve", ResolveView.as_view(), name="identity-resolve"),
    path("v1/identity/break-glass", BreakGlassView.as_view(), name="identity-break-glass"),
    path(
        "v1/enrolment/otp/request",
        EnrolmentOtpRequestView.as_view(),
        name="enrolment-otp-request",
    ),
    path(
        "v1/enrolment/otp/verify",
        EnrolmentOtpVerifyView.as_view(),
        name="enrolment-otp-verify",
    ),
]
