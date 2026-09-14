"""Resolve how an officer is reached. The dispatch row stores the actor id."""

from __future__ import annotations

import re

from manobal_core.apps.governance.enums import AlertChannel
from manobal_core.apps.governance.models import OfficerProfile

E164 = re.compile(r"^\+[1-9]\d{7,14}$")


class DestinationRefused(ValueError):  # noqa: N818
    """The officer sent a number or token that cannot be stored."""


def destination_for(actor_id: str, channel: str) -> str:
    """Return the live address for ``channel``, or empty if none is registered."""
    profile = OfficerProfile.objects.filter(pk=actor_id).first()
    if profile is None:
        return ""
    if channel == AlertChannel.SMS:
        return profile.duty_phone_e164
    if channel in {AlertChannel.PUSH, AlertChannel.DIGEST}:
        return profile.push_token
    return ""


def register_destination(
    actor_id: str,
    *,
    duty_phone_e164: str | None = None,
    push_token: str | None = None,
) -> OfficerProfile:
    """Store this officer's own reachability. Never a subject's number."""
    profile = OfficerProfile.objects.filter(pk=actor_id).first()
    if profile is None:
        raise DestinationRefused("unknown officer")
    updates: list[str] = []
    if duty_phone_e164 is not None:
        phone = str(duty_phone_e164).strip()
        if phone and E164.match(phone) is None:
            raise DestinationRefused("duty phone must be E.164")
        profile.duty_phone_e164 = phone
        updates.append("duty_phone_e164")
    if push_token is not None:
        token = str(push_token).strip()
        if len(token) > 4096:
            raise DestinationRefused("push token exceeds the length ceiling")
        profile.push_token = token
        updates.append("push_token")
    if updates:
        profile.save(update_fields=updates)
    return profile


def destination_status(profile: OfficerProfile) -> dict[str, object]:
    phone = profile.duty_phone_e164
    return {
        "duty_phone_set": bool(phone),
        "duty_phone_hint": phone[-4:] if len(phone) >= 4 else "",
        "push_token_set": bool(profile.push_token),
    }
