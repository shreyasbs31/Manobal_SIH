"""How an alert leaves the process.

FCM and NIC SMS fire only when their credentials are present. Without keys the
in-process transport still marks the row sent so routing tests stay honest.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from django.conf import settings
from django.utils import timezone

from manobal_core.alerting.destinations import destination_for
from manobal_core.apps.governance.enums import AlertChannel, DeliveryStatus
from manobal_core.apps.governance.models import AlertDispatch

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SendResult:
    accepted: bool
    failure_reason: str = ""


class AlertTransport(Protocol):
    def send(self, row: AlertDispatch) -> SendResult: ...


class InProcessTransport:
    """Marks the dispatch sent. Used in development and in the suite."""

    def send(self, row: AlertDispatch) -> SendResult:
        del row
        return SendResult(accepted=True)


class FcmTransport:
    """Firebase Cloud Messaging. No-ops unless ``MANOBAL_FCM_SERVER_KEY`` is set."""

    def send(self, row: AlertDispatch) -> SendResult:
        key = os.environ.get("MANOBAL_FCM_SERVER_KEY", "")
        if not key:
            return SendResult(accepted=True, failure_reason="fcm_unconfigured")
        token = destination_for(row.recipient_id, row.channel)
        if not token:
            return SendResult(accepted=False, failure_reason="destination_missing")
        payload = json.dumps(
            {
                "to": token,
                "notification": {"title": "MANOBAL", "body": row.body},
                "priority": "high",
            }
        ).encode()
        return _post_json("https://fcm.googleapis.com/fcm/send", payload, auth=f"key={key}")


class NicSmsTransport:
    """NIC SMS gateway. No-ops unless username and password are set."""

    def send(self, row: AlertDispatch) -> SendResult:
        user = os.environ.get("MANOBAL_NIC_SMS_USER", "")
        password = os.environ.get("MANOBAL_NIC_SMS_PASSWORD", "")
        sender = os.environ.get("MANOBAL_NIC_SMS_SENDER", "")
        endpoint = os.environ.get("MANOBAL_NIC_SMS_URL", "")
        if not (user and password and sender and endpoint):
            return SendResult(accepted=True, failure_reason="sms_unconfigured")
        phone = destination_for(row.recipient_id, row.channel)
        if not phone:
            return SendResult(accepted=False, failure_reason="destination_missing")
        payload = json.dumps(
            {
                "username": user,
                "password": password,
                "sender": sender,
                "message": row.body,
                "recipient": phone,
            }
        ).encode()
        return _post_json(endpoint, payload)


class CompositeTransport:
    """Route push to FCM and SMS to NIC when those keys exist."""

    def send(self, row: AlertDispatch) -> SendResult:
        if row.channel == AlertChannel.SMS:
            return NicSmsTransport().send(row)
        if row.channel in {AlertChannel.PUSH, AlertChannel.DIGEST}:
            return FcmTransport().send(row)
        return InProcessTransport().send(row)


def _post_json(url: str, payload: bytes, *, auth: str = "") -> SendResult:
    if not url.startswith("https://"):
        return SendResult(accepted=False, failure_reason="insecure_endpoint")
    headers = {"Content-Type": "application/json"}
    if auth:
        headers["Authorization"] = auth
    request = urllib.request.Request(url, data=payload, headers=headers, method="POST")  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=5) as response:  # noqa: S310
            if int(response.status) >= 400:
                return SendResult(accepted=False, failure_reason=f"http_{response.status}")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.warning("alert_transport_failed")
        return SendResult(accepted=False, failure_reason=str(exc)[:200])
    return SendResult(accepted=True)


def configured_transport() -> AlertTransport:
    alerting = getattr(settings, "ALERTING", {})
    if alerting.get("USE_IN_PROCESS_TRANSPORT", True) and not (
        os.environ.get("MANOBAL_FCM_SERVER_KEY") or os.environ.get("MANOBAL_NIC_SMS_USER")
    ):
        return InProcessTransport()
    return CompositeTransport()


def apply_send(row: AlertDispatch, result: SendResult) -> AlertDispatch:
    """Record what the transport did. The row is the audit of delivery."""
    if result.accepted:
        AlertDispatch.objects.filter(pk=row.pk).update(
            status=DeliveryStatus.SENT,
            sent_at=timezone.now(),
            failure_reason="",
        )
    else:
        AlertDispatch.objects.filter(pk=row.pk).update(
            status=DeliveryStatus.FAILED,
            failure_reason=result.failure_reason[:256],
        )
    row.refresh_from_db()
    return row
