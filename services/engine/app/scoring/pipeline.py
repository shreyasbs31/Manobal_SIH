from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .changepoint import onset_from_change_points
from .core import (
    DomainState,
    apply_acute,
    apply_corroboration,
    apply_hysteresis,
    cusum_step,
    domain_participates,
    ewma_step,
    raw_tier,
    renormalised_wsi,
    shrink_median,
    z_score,
    zhat,
)
from .indicators import DOMAIN_INDICATORS, INDICATOR_DIRECTION, baseline_stats
from .ruleset import Ruleset, load_ruleset

DEFAULT_FLOORS = {
    "duty_hours_7d": 1.5,
    "consecutive_duty_days": 1.0,
    "sleep_minutes_7d": 15.0,
    "ema_mood_7d": 0.2,
}


@dataclass
class Assessment:
    token: str
    date: date
    wsi: float
    raw_tier: str
    final_tier: str
    corroborating_domains: list[str]
    trajectory: str
    forecast_p: float | None
    forecast_lo: float | None
    forecast_hi: float | None
    drivers: list[dict[str, str]]
    onset_date: date | None
    limited_data: bool
    ruleset_version: str
    model_version: str
    domain_states: list[DomainState] = field(default_factory=list)
    shadow_tier: str | None = None


def score_person_day(
    *,
    token: str,
    as_of: date,
    indicator_history: dict[str, list[tuple[date, float]]],
    consents: set[str],
    acute: bool = False,
    previous_tier: str | None = None,
    lower_cycles: int = 0,
    previous_wsi: list[tuple[date, float]] | None = None,
    cohort_priors: dict[str, float] | None = None,
    ruleset: Ruleset | None = None,
    shadow: Ruleset | None = None,
    coverage: dict[str, float] | None = None,
) -> Assessment:
    active = ruleset or load_ruleset("v1.0.0")
    states: list[DomainState] = []
    drivers: list[dict[str, str]] = []
    priors = cohort_priors or {}
    cov = coverage or {}
    ewma_prev: dict[str, float] = {}
    cusum_prev: dict[str, float] = {}
    for domain_name, indicators in DOMAIN_INDICATORS.items():
        rule = active.domains[domain_name]
        ewma_values: list[float] = []
        available = 0
        for indicator in indicators:
            series = indicator_history.get(indicator, [])
            values = [point[1] for point in series if point[0] <= as_of]
            if not values:
                continue
            available += 1
            median, mad, n = baseline_stats(values[-int(active.baseline["window_days"]) :])
            median = shrink_median(
                n,
                median,
                priors.get(indicator, median),
                int(active.baseline["minimum_observations"]),
            )
            floor = active.floors.get(indicator, DEFAULT_FLOORS.get(indicator, 0.1))
            direction = INDICATOR_DIRECTION[indicator]
            z_value = z_score(values[-1], median, mad, floor, direction)
            hat = zhat(z_value)
            ewma = ewma_step(hat, ewma_prev.get(indicator, hat))
            ewma_prev[indicator] = ewma
            ewma_values.append(ewma)
            if hat >= 0.45:
                drivers.append({"indicator": indicator, "z": f"{z_value:.2f}"})
        expected = len(indicators)
        domain_coverage = available / expected if expected else 0.0
        if cov.get(domain_name) is not None:
            domain_coverage = cov[domain_name]
        consented = rule.consent in consents
        participating = domain_participates(
            domain_coverage,
            consented,
            float(active.baseline["coverage_minimum"]),
        )
        domain_z = sum(ewma_values) / len(ewma_values) if ewma_values else 0.0
        cusum = cusum_step(cusum_prev.get(domain_name, 0.0), domain_z, rule.cusum_k)
        cusum_prev[domain_name] = cusum
        breached = participating and (domain_z >= rule.threshold or cusum >= rule.cusum_h)
        states.append(
            DomainState(
                name=domain_name,
                z=domain_z,
                ewma=domain_z,
                cusum=cusum,
                coverage=domain_coverage,
                consented=consented,
                participating=participating,
                breached=breached,
                weight=rule.weight,
            )
        )
    wsi, _share, limited = renormalised_wsi(states)
    raw = raw_tier(wsi, active.tiers["t1"], active.tiers["t2"], active.tiers["t3"])
    corroborating = [state.name for state in states if state.breached]
    candidate = apply_corroboration(raw, len(corroborating), active.minimum_corroborating_domains)
    held, _cycles = apply_hysteresis(
        candidate, previous_tier, lower_cycles, active.hysteresis_cycles
    )
    final = apply_acute(held, acute)
    history = [value for when, value in (previous_wsi or []) if when <= as_of]
    history.append(wsi)
    onset_index = onset_from_change_points(history, len(history) - 1) if wsi > 0.35 else None
    onset = None
    if onset_index is not None and previous_wsi:
        dates = [when for when, _value in previous_wsi if when <= as_of] + [as_of]
        if 0 <= onset_index < len(dates):
            onset = dates[onset_index]
    slope = 0.0
    if len(history) >= 14:
        slope = (history[-1] - history[-14]) / 14.0
    trajectory = "stable"
    if slope > 0.01:
        trajectory = "rising"
    elif slope < -0.01:
        trajectory = "falling"
    shadow_tier = None
    if shadow is not None:
        shadow_tier = score_person_day(
            token=token,
            as_of=as_of,
            indicator_history=indicator_history,
            consents=consents,
            acute=acute,
            previous_tier=previous_tier,
            lower_cycles=lower_cycles,
            previous_wsi=previous_wsi,
            cohort_priors=cohort_priors,
            ruleset=shadow,
            shadow=None,
            coverage=coverage,
        ).final_tier
    return Assessment(
        token=token,
        date=as_of,
        wsi=wsi,
        raw_tier=raw,
        final_tier=final,
        corroborating_domains=corroborating,
        trajectory=trajectory,
        forecast_p=None,
        forecast_lo=None,
        forecast_hi=None,
        drivers=drivers[:3],
        onset_date=onset,
        limited_data=limited,
        ruleset_version=active.version,
        model_version="none",
        domain_states=states,
        shadow_tier=shadow_tier,
    )
