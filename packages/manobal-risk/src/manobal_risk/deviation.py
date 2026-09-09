"""Indicator deviation — SDD §4.5 step 2, FR-3.2.

    z     = ((x - mu) / max(sigma, eps)) * d
    z_hat = clip(z / 3, 0, 1)

``d`` encodes which direction is adverse; ``eps`` is a per-indicator floor on the
denominator.
"""

from __future__ import annotations

from .ruleset import IndicatorSpec
from .types import Baseline, IndicatorDeviation


def compute_deviation(
    spec: IndicatorSpec,
    baseline: Baseline,
    *,
    observed_value: float,
    z_divisor: float,
) -> IndicatorDeviation | None:
    """Score one indicator against the subject's own baseline.

    Returns ``None`` when the baseline is insufficient, which removes the
    indicator from its domain's coverage rather than contributing a misleading
    zero.

    Two choices in the clip are deliberate:

    * The lower bound is 0, not -1. An indicator moving in the *benign*
      direction contributes nothing; it does not earn credit that offsets an
      adverse indicator elsewhere. Sleeping well this week does not cancel out a
      collapse in self-reported mood.
    * The upper bound is 1. One catastrophic indicator cannot swamp its domain's
      mean and back-door the corroboration gate, which is the control the whole
      false-positive story rests on.
    """
    if not baseline.sufficient:
        return None

    sigma = max(baseline.mad, spec.epsilon)
    if sigma <= 0.0:
        # Unreachable via a validated ruleset (epsilon must be > 0), but a
        # division by zero in the safety-critical path is not something to leave
        # to the validator alone.
        return None

    z = ((observed_value - baseline.median) / sigma) * int(spec.direction)
    squashed = min(max(z / z_divisor, 0.0), 1.0)

    return IndicatorDeviation(
        indicator_code=spec.code,
        domain=spec.domain,
        deviation=squashed,
        observed_value=observed_value,
        baseline=baseline,
    )
