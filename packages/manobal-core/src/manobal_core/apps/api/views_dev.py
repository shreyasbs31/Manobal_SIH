"""Development-only token mint and JWKS. Not mounted in production."""

from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from manobal_core.agent.cloud import llm_api_key
from manobal_core.apps.authz.local_issuer import mint_token, public_jwk
from manobal_core.apps.governance.enums import Role, Tier
from manobal_core.apps.governance.models import Case, Subject


class DevJwksView(APIView):
    authentication_classes = []  # noqa: RUF012
    permission_classes = [AllowAny]  # noqa: RUF012

    def get(self, request: Request) -> Response:
        del request
        return Response({"keys": [public_jwk()]})


class DevTokenView(APIView):
    authentication_classes = []  # noqa: RUF012
    permission_classes = [AllowAny]  # noqa: RUF012

    def post(self, request: Request) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        role = str(body.get("role") or "")
        if role not in Role.values:
            return Response(
                {"code": "MB-4220", "detail": "unknown role"},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        actor_id = str(body.get("actor_id") or f"dev-{role}")
        token = mint_token(
            role=role,
            actor_id=actor_id,
            force_code=str(body.get("force_code") or "CAPF"),
            unit_code=str(body.get("unit_code") or ""),
            subject_token=str(body.get("subject_token") or ""),
        )
        return Response(
            {"token": token, "token_type": "Bearer", "role": role, "actor_id": actor_id}
        )


class DevSeedInfoView(APIView):
    authentication_classes = []  # noqa: RUF012
    permission_classes = [AllowAny]  # noqa: RUF012

    def get(self, request: Request) -> Response:
        del request
        case = Case.objects.filter(tier_at_open=Tier.T2).order_by("id").first()
        subject = (
            Subject.objects.filter(subject_token=case.subject_token).first()
            if case is not None
            else Subject.objects.order_by("subject_token").first()
        )
        return Response(
            {
                "personnel_token": subject.subject_token if subject else "tok_seed_0000",
                "officer_id": "officer-001",
                "unit_code": subject.unit_id if subject else "12BN_A",
                "llm_configured": bool(llm_api_key()),
                "walkthrough": [
                    "Personnel: check-in, helplines vs SOS, talk, journal, trends.",
                    "Officer: assigned T2/T3/T4 cases — category names only.",
                    "Medical: clinical queue after a referral.",
                    "Commander: unit band for 12BN_A. No tokens.",
                    "WDEC: audit, fairness, break-glass review.",
                ],
            }
        )
