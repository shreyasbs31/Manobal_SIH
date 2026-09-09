"""The only sentences an alert is allowed to say (FR-6.2).

A lock screen in a barracks is a public surface. The body is therefore a
constant, not a template: there is no slot to put a name, a tier or a
category into, so those things cannot leak by interpolation.
"""

from __future__ import annotations

from django.conf import settings

from manobal_core.apps.governance.enums import Tier


def lock_screen_body(tier: Tier) -> str:
    """Return the exact published sentence for ``tier``. Nothing is interpolated."""
    alerting = settings.ALERTING
    if tier == Tier.T4:
        return str(alerting["URGENT_PUSH_BODY"])
    return str(alerting["PUSH_BODY"])


def assert_minimised(body: str) -> None:
    """Refuse to queue a body that is not one of the two published sentences.

    Defence in depth: a future caller who concatenates a token onto the
    constant fails here, before the row is written and before a gateway sees it.
    """
    allowed = {
        str(settings.ALERTING["PUSH_BODY"]),
        str(settings.ALERTING["URGENT_PUSH_BODY"]),
    }
    if body not in allowed:
        raise ValueError("alert body is not a published lock-screen sentence")
