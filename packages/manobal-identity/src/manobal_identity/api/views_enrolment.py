"""Device enrolment OTP. No workload identity: the caller has a mobile, not SPIFFE."""

from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from manobal_identity.api.views import Unprocessable
from manobal_identity.enrolment.otp import OtpRefused, request_otp, verify_otp


class TooMany(APIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "MB-4290: too many requests"
    default_code = "MB-4290"


class EnrolmentOtpRequestView(APIView):
    authentication_classes: list[object] = []  # noqa: RUF012
    permission_classes = [AllowAny]  # noqa: RUF012

    def post(self, request: Request) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        try:
            request_otp(str(body.get("mobile_e164") or ""))
        except OtpRefused as exc:
            raise TooMany("MB-4290: too many requests") from exc
        return Response({"accepted": True}, status=status.HTTP_202_ACCEPTED)


class EnrolmentOtpVerifyView(APIView):
    authentication_classes: list[object] = []  # noqa: RUF012
    permission_classes = [AllowAny]  # noqa: RUF012

    def post(self, request: Request) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        try:
            token = verify_otp(str(body.get("mobile_e164") or ""), str(body.get("code") or ""))
        except OtpRefused as exc:
            raise Unprocessable("MB-4220: invalid code") from exc
        return Response({"subject_token": token}, headers={"Cache-Control": "no-store"})
