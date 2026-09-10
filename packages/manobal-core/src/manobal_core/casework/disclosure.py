"""Officer asks; the individual answers. Refusal is not a scoring input (FR-4.4)."""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from manobal_core.apps.governance.enums import OFFICER_VISIBLE_TIERS
from manobal_core.apps.governance.models import Case, DisclosureRequest, RiskAssessmentRecord

MAX_RATIONALE = 500
TREND_LIMIT = 12


class DisclosureRefused(ValueError):  # noqa: N818
    """The request is malformed, expired, or not the subject's to answer."""


def request_disclosure(
    case: Case, *, actor_id: str, category: str, rationale: str
) -> DisclosureRequest:
    name = category.strip()
    reason = rationale.strip()
    if not name or not reason:
        raise DisclosureRefused("category and rationale are required")
    if len(reason) > MAX_RATIONALE:
        raise DisclosureRefused("rationale exceeds the length ceiling")
    days = int(settings.PRIVACY.get("DISCLOSURE_TTL_DAYS", 7))
    return DisclosureRequest.objects.create(
        case=case,
        subject_token=case.subject_token,
        requested_by=actor_id,
        category=name,
        rationale=reason[:MAX_RATIONALE],
        expires_at=timezone.now() + timedelta(days=days),
    )


def answer_disclosure(
    request: DisclosureRequest, *, subject_token: str, granted: bool
) -> DisclosureRequest:
    if request.subject_token != subject_token:
        raise DisclosureRefused("you may only answer a request about you")
    if request.responded_at is not None:
        raise DisclosureRefused("this request has already been answered")
    if request.expires_at <= timezone.now():
        raise DisclosureRefused("this request has expired")
    request.granted = granted
    request.responded_at = timezone.now()
    request.save(update_fields=["granted", "responded_at"])
    return request


def category_trend(case: Case, category: str) -> list[dict[str, object]]:
    """Presence of ``category`` over time. Never a score."""
    live = DisclosureRequest.objects.filter(
        case=case,
        category=category,
        granted=True,
        expires_at__gt=timezone.now(),
    ).exists()
    if not live:
        raise DisclosureRefused("no live disclosure grant")
    rows = RiskAssessmentRecord.objects.filter(
        subject_token=case.subject_token
    ).order_by("-assessed_at", "-id")[:TREND_LIMIT]
    return [
        {
            "assessed_at": row.assessed_at.isoformat(),
            "tier_visible": row.tier in OFFICER_VISIBLE_TIERS,
            "present": category in row.contributing_categories,
        }
        for row in rows
    ]
