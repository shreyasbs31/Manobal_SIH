"""k-anonymised unit rollups for the commander view (SDD §4.6, §4.8).

A commander sees a band and a category name, or they see that the figure was
withheld. They never see a headcount below *k*, an exact elevated count, a
subject token, or an individual tier. Suppression is stored, not recomputed at
render time, so a commander refreshing a small unit cannot fish for the moment
it crosses the threshold, and the WDEC can count how often we withheld.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from django.conf import settings
from django.utils import timezone

from manobal_core.apps.governance.enums import (
    OFFICER_VISIBLE_TIERS,
    AuditAction,
    LegalBasis,
    PurposeCode,
    Role,
    SubjectStatus,
)
from manobal_core.apps.governance.models import (
    AuditEvent,
    RiskAssessmentRecord,
    Subject,
    Unit,
    UnitAggregate,
)
from manobal_core.insights.briefing import unit_briefing

SUPPRESSED_BELOW_K = "below_k"
SUPPRESSED_CHURN = "cohort_churn"


@dataclass(frozen=True, slots=True)
class Rollup:
    headcount: int
    elevated: int
    elevated_band: str
    dominant_category: str
    trend_direction: str
    suppressed: bool
    suppression_reason: str


def band_elevated(count: int) -> str:
    """Round an exact count to a band so two queries cannot isolate a person."""
    if count <= 0:
        return "0"
    if count <= 4:
        return "1-4"
    if count <= 9:
        return "5-9"
    if count <= 19:
        return "10-19"
    return "20+"


def decide_rollup(
    *,
    headcount: int,
    elevated: int,
    dominant_category: str,
    previous_elevated_band: str,
    churn: float,
    k_threshold: int,
    max_churn: float,
) -> Rollup:
    """Pure decision: counts in, a publishable or suppressed rollup out."""
    if headcount < k_threshold:
        return Rollup(
            headcount=headcount,
            elevated=elevated,
            elevated_band="",
            dominant_category="",
            trend_direction="",
            suppressed=True,
            suppression_reason=SUPPRESSED_BELOW_K,
        )
    if churn > max_churn:
        return Rollup(
            headcount=headcount,
            elevated=elevated,
            elevated_band="",
            dominant_category="",
            trend_direction="",
            suppressed=True,
            suppression_reason=SUPPRESSED_CHURN,
        )
    band = band_elevated(elevated)
    trend = "stable"
    if previous_elevated_band and previous_elevated_band != band:
        trend = "up" if _band_rank(band) > _band_rank(previous_elevated_band) else "down"
    return Rollup(
        headcount=headcount,
        elevated=elevated,
        elevated_band=band,
        dominant_category=dominant_category,
        trend_direction=trend,
        suppressed=False,
        suppression_reason="",
    )


def ensure_aggregate(
    unit: Unit, *, period_start: date | None = None, period_end: date | None = None
) -> UnitAggregate:
    """Return the rollup for ``unit`` in the period, computing it if needed."""
    end = period_end or timezone.localdate()
    start = period_start or (end - timedelta(days=7))
    existing = UnitAggregate.objects.filter(
        unit=unit, period_start=start, period_end=end
    ).first()
    if existing is not None:
        return existing

    privacy = settings.PRIVACY
    k_threshold = int(privacy["K_ANONYMITY_THRESHOLD"])
    max_churn = float(privacy["MAX_COHORT_CHURN"])

    subjects = Subject.objects.filter(unit=unit, status=SubjectStatus.ACTIVE)
    headcount = subjects.count()
    tokens = list(subjects.values_list("subject_token", flat=True))

    latest = _latest_assessments(tokens, start, end)
    elevated_rows = [row for row in latest if row.tier in OFFICER_VISIBLE_TIERS]
    dominant = _dominant_category(elevated_rows)

    previous = (
        UnitAggregate.objects.filter(unit=unit, period_end__lt=start)
        .order_by("-period_end")
        .first()
    )
    churn = _churn(unit, start, headcount)
    rollup = decide_rollup(
        headcount=headcount,
        elevated=len(elevated_rows),
        dominant_category=dominant,
        previous_elevated_band=previous.elevated_band if previous else "",
        churn=churn,
        k_threshold=k_threshold,
        max_churn=max_churn,
    )
    aggregate = UnitAggregate.objects.create(
        unit=unit,
        period_start=start,
        period_end=end,
        headcount=rollup.headcount,
        elevated_band=rollup.elevated_band,
        dominant_category=rollup.dominant_category,
        trend_direction=rollup.trend_direction,
        suppressed=rollup.suppressed,
        suppression_reason=rollup.suppression_reason,
        k_threshold=k_threshold,
    )
    if rollup.suppressed:
        AuditEvent.record(
            actor_id="manobal-core",
            actor_role=Role.INTEGRATION,
            action=AuditAction.AGGREGATE_SUPPRESSED,
            purpose_code=PurposeCode.OVERSIGHT_AUDIT,
            legal_basis=LegalBasis.LEGAL_OBLIGATION,
            outcome="success",
            detail={
                "unit": unit.code,
                "reason": rollup.suppression_reason,
                "k_threshold": k_threshold,
            },
        )
    return aggregate


def public_aggregate_payload(aggregate: UnitAggregate) -> dict[str, object]:
    """What a commander may be told. Omits exact counts when suppressed."""
    body: dict[str, object] = {
        "unit": aggregate.unit_id,
        "period_start": aggregate.period_start.isoformat(),
        "period_end": aggregate.period_end.isoformat(),
        "suppressed": aggregate.suppressed,
    }
    if aggregate.suppressed:
        return body
    body.update(
        {
            "elevated_band": aggregate.elevated_band,
            "dominant_category": aggregate.dominant_category,
            "trend_direction": aggregate.trend_direction,
            "briefing": unit_briefing(
                suppressed=False,
                elevated_band=str(aggregate.elevated_band or ""),
                dominant_category=str(aggregate.dominant_category or ""),
                trend_direction=str(aggregate.trend_direction or ""),
            ),
        }
    )
    return body


def _latest_assessments(
    tokens: list[str], start: date, end: date
) -> list[RiskAssessmentRecord]:
    if not tokens:
        return []
    rows = (
        RiskAssessmentRecord.objects.filter(
            subject_token__in=tokens,
            assessed_at__date__gte=start,
            assessed_at__date__lte=end,
        )
        .order_by("subject_token", "-assessed_at", "-id")
    )
    seen: set[str] = set()
    latest: list[RiskAssessmentRecord] = []
    for row in rows:
        if row.subject_token in seen:
            continue
        seen.add(row.subject_token)
        latest.append(row)
    return latest


def _dominant_category(rows: list[RiskAssessmentRecord]) -> str:
    counts: dict[str, int] = {}
    for row in rows:
        for category in row.contributing_categories:
            counts[category] = counts.get(category, 0) + 1
    if not counts:
        return ""
    return max(counts, key=lambda name: (counts[name], name))


def _churn(unit: Unit, period_start: date, headcount: int) -> float:
    """Arrivals plus departures in the period, over current headcount."""
    if headcount == 0:
        return 0.0
    arrived = Subject.objects.filter(unit=unit, created_at__date__gte=period_start).count()
    left = Subject.objects.filter(
        unit=unit,
        status=SubjectStatus.TRANSFERRED,
        updated_at__date__gte=period_start,
    ).count()
    return (arrived + left) / headcount


def _band_rank(band: str) -> int:
    order = {"0": 0, "1-4": 1, "5-9": 2, "10-19": 3, "20+": 4}
    return order.get(band, -1)
