from __future__ import annotations

from dataclasses import dataclass

TIER_RANK = {"T0": 0, "T1": 1, "T2": 2, "T3": 3, "T4": 4}
TIER_FROM_RANK = {rank: name for name, rank in TIER_RANK.items()}
MAD_SCALE = 1.4826


@dataclass(frozen=True)
class DomainState:
    name: str
    z: float
    ewma: float
    cusum: float
    coverage: float
    consented: bool
    participating: bool
    breached: bool
    weight: float


def scaled_mad(mad: float, floor: float) -> float:
    return max(mad * MAD_SCALE, floor)


def z_score(value: float, median: float, mad: float, floor: float, direction: float) -> float:
    return direction * (value - median) / scaled_mad(mad, floor)


def shrink_median(n: int, person_median: float, cohort_median: float, minimum: int = 21) -> float:
    if n >= minimum:
        return person_median
    weight = n / minimum
    return weight * person_median + (1.0 - weight) * cohort_median


def regime_blend(
    day_in_warmup: int,
    warmup_days: int,
    previous_median: float,
    cohort_median: float,
) -> float:
    if day_in_warmup >= warmup_days:
        return cohort_median
    previous_weight = 0.7 * (1.0 - day_in_warmup / warmup_days)
    return previous_weight * previous_median + (1.0 - previous_weight) * cohort_median


def zhat(z_value: float) -> float:
    clipped = z_value / 3.0
    if clipped < 0:
        return 0.0
    if clipped > 1:
        return 1.0
    return clipped


def ewma_step(current_zhat: float, previous: float, alpha: float = 0.3) -> float:
    return alpha * current_zhat + (1.0 - alpha) * previous


def cusum_step(previous: float, domain_z: float, k: float) -> float:
    return max(0.0, previous + domain_z - k)


def desesasonalise(value: float, weekday_effect: float, rotation_effect: float) -> float:
    return value - weekday_effect - rotation_effect


def domain_participates(coverage: float, consented: bool, minimum: float = 0.6) -> bool:
    return consented and coverage >= minimum


def renormalised_wsi(states: list[DomainState]) -> tuple[float, float, bool]:
    active = [state for state in states if state.participating]
    weight_sum = sum(state.weight for state in active)
    total_weight = sum(state.weight for state in states) or 1.0
    if weight_sum <= 0:
        return 0.0, 0.0, True
    wsi = sum(state.weight * state.z for state in active) / weight_sum
    share = weight_sum / total_weight
    return wsi, share, share < 0.5


def raw_tier(wsi: float, t1: float = 0.35, t2: float = 0.55, t3: float = 0.75) -> str:
    if wsi < t1:
        return "T0"
    if wsi < t2:
        return "T1"
    if wsi < t3:
        return "T2"
    return "T3"


def apply_corroboration(raw: str, breached: int, minimum: int = 2) -> str:
    if breached < minimum:
        return TIER_FROM_RANK[min(TIER_RANK[raw], TIER_RANK["T1"])]
    return raw


def apply_hysteresis(
    candidate: str,
    previous: str | None,
    lower_cycles: int,
    need: int = 2,
) -> tuple[str, int]:
    if previous is None:
        return candidate, 0
    if TIER_RANK[candidate] < TIER_RANK[previous]:
        next_cycles = lower_cycles + 1
        if next_cycles < need:
            return previous, next_cycles
        return candidate, 0
    return candidate, 0


def apply_acute(tier: str, acute: bool) -> str:
    return "T4" if acute else tier


def forecast_authority(tier: str, trajectory: str, corroborating: int) -> str:
    if trajectory == "rising" and tier == "T0":
        return "T1"
    if TIER_RANK[tier] > TIER_RANK["T1"] and corroborating < 2:
        return "T1"
    return tier


def score_generated_subjects(count: int = 80_000, seed: int = 80_000) -> dict[str, float | int]:
    """Score `count` synthetic subjects in memory (spec 8.9)."""
    import time

    import numpy as np

    if count < 1:
        raise ValueError("count must be at least 1")
    started = time.perf_counter()
    rng = np.random.default_rng(seed)
    values = rng.normal(10.0, 2.0, size=(count, 4)).astype(np.float64)
    median = 10.0
    mad = 1.2
    floor = 0.5
    direction = 1.0
    weights = np.array([0.30, 0.25, 0.25, 0.20], dtype=np.float64)
    z = direction * (values - median) / scaled_mad(mad, floor)
    wsi = (z * weights).sum(axis=1) / float(weights.sum())
    _tiers = np.where(wsi < 0.35, 0, np.where(wsi < 0.55, 1, np.where(wsi < 0.75, 2, 3)))
    names = ("workload", "sleep", "body", "voice")
    sample_states = [
        DomainState(
            name=names[index],
            z=z_score(float(values[0, index]), median, mad, floor, direction),
            ewma=0.0,
            cusum=0.0,
            coverage=1.0,
            consented=True,
            participating=True,
            breached=False,
            weight=float(weights[index]),
        )
        for index in range(4)
    ]
    python_wsi, _share, _limited = renormalised_wsi(sample_states)
    if abs(float(wsi[0]) - python_wsi) > 1e-6:
        raise RuntimeError("in-memory benchmark drifted from scoring.core")
    elapsed = time.perf_counter() - started
    return {"subjects": int(count), "seconds": float(elapsed), "tier_mass": int(_tiers.sum())}
