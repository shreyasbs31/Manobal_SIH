"""How an alert leaves the process.

Production will put NIC SMS and the push gateway behind this protocol. Locally
and in tests the in-process transport marks the row sent: the routing and
minimisation logic is what must be proven, and a real gateway would hide a
dedupe bug behind a network mock.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from django.utils import timezone

from manobal_core.apps.governance.enums import DeliveryStatus
from manobal_core.apps.governance.models import AlertDispatch


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
