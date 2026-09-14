"""Enrolment OTP. Confirms a mobile without disclosing whether it is known."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from manobal_identity.apps.vault.models import EnrolmentChallenge
from manobal_identity.crypto.blind_index import blind_index_mobile, normalise_mobile

OTP_TTL = timedelta(minutes=5)
MAX_ATTEMPTS = 5


class OtpRefused(ValueError):  # noqa: N818
    """Rate limited, expired, or the code did not match."""


@dataclass(frozen=True, slots=True)
class IssuedOtp:
    accepted: bool
    #: Present only when a test injected ``code``. Never serialised on the wire.
    code: str | None = None


def request_otp(mobile_e164: str, *, code: str | None = None) -> IssuedOtp:
    """Record a challenge. The response shape does not depend on enrolment."""
    try:
        index = _index(mobile_e164)
    except ValueError:
        return IssuedOtp(accepted=True)
    if not _rate_ok(index):
        raise OtpRefused("rate limited")
    digits = code or f"{secrets.randbelow(1_000_000):06d}"
    EnrolmentChallenge.objects.create(
        mobile_index=index,
        code_hash=_hash(index, digits),
        expires_at=timezone.now() + OTP_TTL,
    )
    if code is None:
        _dispatch_otp_sms(mobile_e164, digits)
    return IssuedOtp(accepted=True, code=digits if code is not None else None)


def verify_otp(mobile_e164: str, code: str) -> str:
    """Return the subject token. Failures share one message."""
    try:
        index = _index(mobile_e164)
    except ValueError as exc:
        raise OtpRefused("invalid code") from exc
    row = (
        EnrolmentChallenge.objects.filter(mobile_index=index, consumed_at__isnull=True)
        .order_by("-created_at")
        .first()
    )
    if row is None or row.expires_at <= timezone.now():
        raise OtpRefused("invalid code")
    if row.attempts >= MAX_ATTEMPTS:
        raise OtpRefused("invalid code")
    row.attempts = row.attempts + 1
    row.save(update_fields=["attempts"])
    if not hmac.compare_digest(row.code_hash, _hash(index, code)):
        raise OtpRefused("invalid code")
    from manobal_identity.api.runtime import get_vault

    token = get_vault().token_for_mobile(mobile_e164)
    if token is None:
        raise OtpRefused("invalid code")
    row.consumed_at = timezone.now()
    row.save(update_fields=["consumed_at"])
    return token


def _index(mobile_e164: str) -> str:
    normalise_mobile(mobile_e164)
    from manobal_identity.api.runtime import get_vault

    return blind_index_mobile(mobile_e164, get_vault().kms)


def _hash(mobile_index: str, code: str) -> str:
    material = f"{mobile_index}:{code.strip()}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), material, hashlib.sha256).hexdigest()


def _rate_ok(mobile_index: str) -> bool:
    hour = timezone.now() - timedelta(hours=1)
    day = timezone.now() - timedelta(days=1)
    hourly = EnrolmentChallenge.objects.filter(
        mobile_index=mobile_index, created_at__gte=hour
    ).count()
    daily = EnrolmentChallenge.objects.filter(
        mobile_index=mobile_index, created_at__gte=day
    ).count()
    limits = getattr(
        settings, "ENROLMENT", {"otp_per_mobile_hour": 3, "otp_per_mobile_day": 10}
    )
    return hourly < int(limits["otp_per_mobile_hour"]) and daily < int(
        limits["otp_per_mobile_day"]
    )


def _dispatch_otp_sms(mobile_e164: str, digits: str) -> None:
    """Send the challenge via NIC SMS when credentials are configured.

    The HTTP response never includes the digits. Without credentials this is a
    no-op so local and CI enrolment tests stay offline.
    """
    import json
    import logging
    import os
    import urllib.request

    user = os.environ.get("MANOBAL_NIC_SMS_USER", "")
    password = os.environ.get("MANOBAL_NIC_SMS_PASSWORD", "")
    sender = os.environ.get("MANOBAL_NIC_SMS_SENDER", "")
    endpoint = os.environ.get("MANOBAL_NIC_SMS_URL", "")
    if not (user and password and sender and endpoint):
        return
    payload = json.dumps(
        {
            "username": user,
            "password": password,
            "sender": sender,
            "message": f"MANOBAL enrolment code: {digits}",
            "recipient": mobile_e164,
        }
    ).encode()
    if not endpoint.startswith("https://"):
        return
    request = urllib.request.Request(  # noqa: S310
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(request, timeout=5)  # noqa: S310
    except (OSError, TimeoutError):
        logging.getLogger(__name__).warning("enrolment_otp_sms_failed")
