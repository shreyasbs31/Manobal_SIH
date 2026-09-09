"""Domain aggregation and the composite Welfare Signal Index.

SDD §4.5 steps 3-4, FR-3.3.

    Z_d = weighted mean of the domain's usable indicator deviations
    WSI = sum_{d in A} w_d * Z_d / sum_{d in A} w_d      A = {d : coverage_d >= floor}

The renormalised denominator is the entire point. With a fixed denominator of
1.0, a subject who contributes four domains instead of seven would score
mechanically lower, and declining to share data would become the rational way to
stay off the officer's queue. Renormalisation removes that incentive, which is
what makes the voluntary model survivable in a rank structure.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

from .errors import ManobalRiskError
from .ruleset import DomainSpec
from .types import Domain, DomainScore, IndicatorDeviation


def compute_domain_score(
    spec: DomainSpec,
    deviations: Iterable[IndicatorDeviation],
    *,
    indicator_weights: Mapping[str, float],
    expected_indicator_count: int,
    coverage_floor: float,
) -> DomainScore:
    """Aggregate one domain's usable indicators into a single score.

    ``coverage`` is the fraction of the domain's *declared* indicators that
    produced a usable deviation. A domain below the floor is inactive: it is
    excluded from the composite, and — importantly — it cannot count as one of
    the two corroborating signals. Allowing a barely-observed domain to
    corroborate would let thin data defeat the gate that exists to require
    thick data.
    """
    usable = list(deviations)

    coverage = len(usable) / expected_indicator_count if expected_indicator_count > 0 else 0.0
    active = coverage >= coverage_floor

    if usable:
        weights = [max(indicator_weights.get(d.indicator_code, 1.0), 0.0) for d in usable]
        total_weight = sum(weights)
        score = (
            sum(w * d.deviation for w, d in zip(weights, usable, strict=True)) / total_weight
            if total_weight > 0
            else 0.0
        )
    else:
        score = 0.0

    return DomainScore(
        domain=spec.domain,
        score=score,
        coverage=coverage,
        contributing_indicators=tuple(d.indicator_code for d in usable),
        breached=active and score >= spec.corroboration_threshold,
        active=active,
    )


def compute_wsi(
    domain_scores: Sequence[DomainScore],
    domain_specs: Mapping[Domain, DomainSpec],
) -> float:
    """Combine active domain scores into the composite index.

    Raises when no domain is active. Returning 0.0 would be a statement that the
    subject is fine; the truth in that case is that we cannot see them at all,
    and the caller must mark the assessment ``insufficient_coverage`` rather than
    quietly reporting T0.
    """
    active = [
        (domain_specs[ds.domain], ds)
        for ds in domain_scores
        if ds.active and ds.domain in domain_specs
    ]
    if not active:
        raise ManobalRiskError(
            "No domain met the coverage floor; the subject cannot be scored. "
            "This is insufficient coverage, not a stable result."
        )

    total_weight = sum(spec.weight for spec, _ in active)
    if total_weight <= 0:
        raise ManobalRiskError("Active domain weights sum to zero; ruleset is unusable.")

    return sum(spec.weight * ds.score for spec, ds in active) / total_weight
