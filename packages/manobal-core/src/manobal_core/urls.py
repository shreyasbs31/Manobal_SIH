"""Root URL configuration.

Endpoints are added alongside their views as each module lands. Django's admin
is deliberately absent and will stay absent: it offers generic model-level CRUD
over consent entries, audit rows and assessments, which is precisely the
unaudited, unscoped access path the whole authorisation design exists to
prevent. Administrative actions belong to purpose-built, audited endpoints.
"""

from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.urls import include, path


def healthz(_: HttpRequest) -> JsonResponse:
    """Liveness only. Carries no version, no build id and no dependency state.

    Health endpoints are usually reachable without authentication, so anything
    they report is public. Readiness — which does touch the databases and the
    broker — belongs behind authentication.
    """
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("", include("manobal_core.apps.api.urls")),
]

if getattr(settings, "LOCAL_ISSUER_ENABLED", False):
    from manobal_core.apps.api.views_dev import DevJwksView, DevSeedInfoView, DevTokenView

    urlpatterns += [
        path("dev/jwks", DevJwksView.as_view(), name="dev-jwks"),
        path("dev/token", DevTokenView.as_view(), name="dev-token"),
        path("dev/seed", DevSeedInfoView.as_view(), name="dev-seed"),
    ]
