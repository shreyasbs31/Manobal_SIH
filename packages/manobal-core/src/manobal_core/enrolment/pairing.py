"""Bind a device to a subject token. The device never learns a service number."""

from __future__ import annotations

import re

from django.utils import timezone

from manobal_core.apps.governance.models import PairedDevice, Subject

_DEVICE = re.compile(r"^[A-Za-z0-9_.:-]{8,64}$")
_KEY = re.compile(r"^[A-Za-z0-9+/=_-]{32,512}$")


class PairingRefused(ValueError):  # noqa: N818
    """The device id or key is malformed, or the device is already live."""


def pair_device(subject: Subject, *, device_id: str, public_key: str) -> PairedDevice:
    if not _DEVICE.match(device_id):
        raise PairingRefused("device_id is not acceptable")
    if not _KEY.match(public_key):
        raise PairingRefused("public_key is not acceptable")
    existing = PairedDevice.objects.filter(
        subject_token=subject.subject_token, device_id=device_id
    ).first()
    now = timezone.now()
    if existing is not None:
        existing.public_key = public_key
        existing.last_seen_at = now
        if existing.revoked_at is not None:
            existing.revoked_at = None
            existing.paired_at = now
            existing.save(
                update_fields=["public_key", "last_seen_at", "revoked_at", "paired_at"]
            )
        else:
            existing.save(update_fields=["public_key", "last_seen_at"])
        return existing
    if subject.enrolled_at is None:
        subject.enrolled_at = now
        subject.save(update_fields=["enrolled_at", "updated_at"])
    return PairedDevice.objects.create(
        subject_token=subject.subject_token,
        device_id=device_id,
        public_key=public_key,
        last_seen_at=now,
    )


def revoke_device(subject_token: str, device_id: int) -> PairedDevice:
    row = PairedDevice.objects.filter(pk=device_id, subject_token=subject_token).first()
    if row is None:
        raise PairingRefused("device is not paired to you")
    if row.revoked_at is None:
        row.revoked_at = timezone.now()
        row.save(update_fields=["revoked_at"])
    return row


def list_devices(subject_token: str) -> list[PairedDevice]:
    return list(
        PairedDevice.objects.filter(subject_token=subject_token).order_by("-paired_at")
    )
