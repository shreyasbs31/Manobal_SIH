"""Build engine results for orchestrator and API tests.

The engine type is frozen and has many fields. Tests only care about the
tier, the category names and which domains were present — this helper fills
the rest with values that will never be persisted as scores.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from django.utils import timezone

from manobal_core.apps.governance.models import Subject, Unit
from manobal_risk.types import DOMAIN_CATEGORY, Domain, RiskAssessment
from manobal_risk.types import Tier as EngineTier


def engine_assessment(
    subject_token: str,
    *,
    tier: EngineTier,
    categories: tuple[str, ...] = ("workload_and_duty", "leave_and_time_off"),
    covered: frozenset[Domain] | None = None,
    acute: bool = False,
    insufficient: bool = False,
    assessed_at: datetime | None = None,
) -> RiskAssessment:
    """A complete ``RiskAssessment`` with no numeric welfare score on it."""
    present = covered if covered is not None else frozenset(Domain)
    return RiskAssessment(
        subject_token=subject_token,
        assessed_at=assessed_at or datetime.now(tz=UTC),
        tier=tier,
        contributing_categories=categories,
        contributing_domains=tuple(
            domain for domain, name in DOMAIN_CATEGORY.items() if name in categories
        ),
        domain_coverage=tuple((domain, domain in present) for domain in Domain),
        ruleset_version="1.0.0-test",
        ruleset_sha256="a" * 64,
        corroborated=tier >= EngineTier.T2,
        acute_override=acute,
        insufficient_coverage=insufficient,
    )


def make_subjects(unit: Unit, count: int, *, established: bool) -> list[Subject]:
    """Create ``count`` subjects. ``established`` backdates them outside the period."""
    now = timezone.now()
    rows: list[Subject] = []
    for index in range(count):
        rows.append(
            Subject.objects.create(
                subject_token=f"tok_agg_{unit.code}_{index:04d}",
                unit=unit,
                force_code=unit.force_code,
                rank_band="constable",
                service_years_bucket="5-9",
                enrolled_at=now - timedelta(days=60),
            )
        )
    if established:
        Subject.objects.filter(subject_token__in=[row.subject_token for row in rows]).update(
            created_at=now - timedelta(days=30)
        )
        for row in rows:
            row.refresh_from_db()
    return rows
