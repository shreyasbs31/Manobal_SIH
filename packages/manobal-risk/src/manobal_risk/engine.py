"""The risk engine — SDD §4.5 module M5/M6.

    consent filter -> current values -> baselines -> deviations -> domain scores
                   -> WSI (coverage-renormalised) -> raw tier
                   -> corroboration gate -> hysteresis -> acute override

:func:`score` is a pure function of ``(history, ruleset, assessed_at)``. Given the
same three inputs it produces the same assessment forever, which is what makes
FR-3.9 ("an immutable, replayable scoring record sufficient to reconstruct any
past decision") achievable without storing any intermediate numbers.

That last point is the reason for the two-function shape. :func:`score` returns a
:class:`~manobal_risk.types.RiskAssessment` carrying no numeric field at all;
:func:`score_with_trace` additionally returns the arithmetic, for the property
tests, the observation-mode backtest harness and quarterly recalibration. Nothing
in the API layer may call the second one.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import UTC, date, datetime, timedelta

from .baseline import compute_baseline
from .composite import compute_domain_score, compute_wsi
from .deviation import compute_deviation
from .errors import ManobalRiskError
from .ruleset import Ruleset
from .tiering import (
    apply_acute_override,
    apply_corroboration_gate,
    apply_hysteresis,
    raw_tier_for,
)
from .types import (
    DOMAIN_CATEGORY,
    Domain,
    DomainScore,
    IndicatorDeviation,
    Observation,
    RiskAssessment,
    ScoringTrace,
    SubjectHistory,
    Tier,
)

#: Category surfaced alongside the domain categories when the acute override
#: fires. Without it a T4 case arriving with no corroborating domain data would
#: reach the officer with an empty "why" — which is exactly the case where they
#: most need to know that this is a safety escalation and not a scoring artefact.
ACUTE_CATEGORY = "immediate_safety_indicator"


def score(
    history: SubjectHistory,
    ruleset: Ruleset,
    *,
    assessed_at: datetime | None = None,
) -> RiskAssessment:
    """Produce the tier and contributing categories for one subject."""
    assessment, _ = score_with_trace(history, ruleset, assessed_at=assessed_at)
    return assessment


def score_with_trace(
    history: SubjectHistory,
    ruleset: Ruleset,
    *,
    assessed_at: datetime | None = None,
) -> tuple[RiskAssessment, ScoringTrace]:
    """As :func:`score`, plus the intermediate arithmetic.

    The trace is for tests, backtesting and recalibration only. It is never
    serialised to an API, never persisted, and never logged — see FR-3.7 and the
    absence of a score column in SDD §5.2.
    """
    at = assessed_at or datetime.now(UTC)

    observations = _consented_observations(history, ruleset)
    deviations = _compute_deviations(observations, history.as_of, ruleset)
    domain_scores = _compute_domain_scores(deviations, ruleset)

    try:
        wsi = compute_wsi(domain_scores, ruleset.domains)
        insufficient_coverage = False
    except ManobalRiskError:
        # No domain met the coverage floor. This is "we cannot see this person",
        # not "this person is fine": we fall through at T0 but flag it, and the
        # acute override below still applies in full.
        wsi = 0.0
        insufficient_coverage = True

    raw_tier = Tier.T0 if insufficient_coverage else raw_tier_for(wsi, ruleset.tier_bounds)
    breaching = tuple(ds.domain for ds in domain_scores if ds.breached)

    gated_tier, corroborated = apply_corroboration_gate(
        raw_tier,
        breaching_domain_count=len(breaching),
        minimum=ruleset.corroboration_min_domains,
    )
    held_tier = apply_hysteresis(
        gated_tier,
        previous=history.previous_tier,
        consecutive_lower_cycles=history.consecutive_lower_cycles,
        required_cycles=ruleset.hysteresis_cycles,
    )
    final_tier, acute_override = apply_acute_override(held_tier, history.acute_triggers)

    contributing = _contributing_domains(domain_scores, final_tier)
    categories = tuple(DOMAIN_CATEGORY[d] for d in contributing)
    if acute_override:
        categories = (ACUTE_CATEGORY, *categories)

    assessment = RiskAssessment(
        subject_token=history.subject_token,
        assessed_at=at,
        tier=final_tier,
        tier_before_hysteresis=gated_tier,
        contributing_categories=categories,
        contributing_domains=contributing,
        domain_coverage=tuple(
            (ds.domain, ds.active) for ds in sorted(domain_scores, key=lambda d: d.domain.value)
        ),
        ruleset_version=ruleset.version,
        ruleset_sha256=ruleset.sha256,
        corroborated=corroborated,
        acute_override=acute_override,
        insufficient_coverage=insufficient_coverage,
    )
    trace = ScoringTrace(
        wsi=wsi,
        domain_scores=tuple(domain_scores),
        indicator_deviations=tuple(deviations),
        raw_tier=raw_tier,
        tier_before_hysteresis=gated_tier,
        active_domains=tuple(ds.domain for ds in domain_scores if ds.active),
        breaching_domains=breaching,
    )
    return assessment, trace


def _consented_observations(history: SubjectHistory, ruleset: Ruleset) -> list[Observation]:
    """Drop everything the subject has not consented to, before any maths runs.

    Filtering here rather than at the end is what makes coverage renormalisation
    honest: a withdrawn domain is genuinely absent from the calculation, so it
    lands at zero coverage and is excluded from the composite, exactly as if the
    subject had never enrolled in it.
    """
    return [
        o
        for o in history.observations
        if (domain := ruleset.domain_of(o.indicator_code)) is not None
        and domain in history.consented_domains
    ]


def _compute_deviations(
    observations: Sequence[Observation],
    as_of: date,
    ruleset: Ruleset,
) -> list[IndicatorDeviation]:
    by_code: dict[str, list[Observation]] = defaultdict(list)
    for observation in observations:
        if observation.observed_on <= as_of:
            by_code[observation.indicator_code].append(observation)

    staleness_cutoff = as_of - timedelta(days=ruleset.current_value_max_age_days - 1)
    deviations: list[IndicatorDeviation] = []

    for code, series in by_code.items():
        spec = ruleset.indicators.get(code)
        if spec is None:
            continue

        current = max(series, key=lambda o: o.observed_on)
        if current.observed_on < staleness_cutoff:
            # A stale indicator is not a zero-deviation indicator. Excluding it
            # lowers the domain's coverage, which is the honest representation of
            # "this feed has stopped reporting".
            continue

        baseline = compute_baseline(
            code,
            series,
            window_end=as_of,
            window_days=ruleset.baseline_window_days,
            min_observations=ruleset.baseline_min_observations,
        )
        deviation = compute_deviation(
            spec,
            baseline,
            observed_value=current.value,
            z_divisor=ruleset.z_divisor,
        )
        if deviation is not None:
            deviations.append(deviation)

    return deviations


def _compute_domain_scores(
    deviations: Iterable[IndicatorDeviation],
    ruleset: Ruleset,
) -> list[DomainScore]:
    grouped: dict[Domain, list[IndicatorDeviation]] = defaultdict(list)
    for deviation in deviations:
        grouped[deviation.domain].append(deviation)

    return [
        compute_domain_score(
            spec,
            grouped.get(domain, []),
            indicator_weights=ruleset.indicator_weights_for(domain),
            expected_indicator_count=ruleset.expected_indicator_count(domain),
            coverage_floor=ruleset.coverage_floor,
        )
        for domain, spec in ruleset.domains.items()
    ]


def _contributing_domains(
    domain_scores: Sequence[DomainScore],
    final_tier: Tier,
) -> tuple[Domain, ...]:
    """Which categories the officer is told about.

    Breaching domains, strongest first. At T1 — which only the individual ever
    sees — nothing has breached by definition, so the single most-deviated active
    domain is named instead, because "something in your sleep and recovery has
    shifted" is the whole content of a T1.
    """
    breaching = sorted(
        (ds for ds in domain_scores if ds.breached),
        key=lambda ds: (-ds.score, ds.domain.value),
    )
    if breaching:
        return tuple(ds.domain for ds in breaching)

    if final_tier >= Tier.T1:
        active = [ds for ds in domain_scores if ds.active and ds.score > 0.0]
        if active:
            leader = max(active, key=lambda ds: (ds.score, ds.domain.value))
            return (leader.domain,)

    return ()
