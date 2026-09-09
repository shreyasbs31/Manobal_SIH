"""Stage 0 — posting, rotation and deployment pressure.

The head of the chain, and the only stage with no parent. Everything downstream
is a response to what this module produces, plus the injected distress strain and
each stage's own noise.

Deployment pressure is deliberately *mean-reverting around zero*, not around a
population level. The absolute harshness of a subject's posting is already in
their personal traits — somebody permanently in a high-intensity posting simply
has a heavier baseline — so what belongs here is only the part that *changes*:
rotation between postings, weeks that run hot, and incidents. That split is the
whole reason a person who has always worked long hours does not look distressed.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..arrays import BoolArray, FloatArray
from ..config import DeploymentModel
from ..population import (
    FAMILY_STATION_PROBABILITY,
    POSTING_INTENSITY,
    PostingClass,
    Unit,
)
from ..processes import ar1, block_boundaries, block_series, scattered_spans

#: Lag-1 correlation and stationary spread of the "how hot is this week" driver.
#: Slow enough to produce runs of hard weeks, fast enough that it contributes
#: little rank correlation over a ninety-day window — which is what keeps the
#: stable cohort's cross-domain correlations weak, as they should be.
_PRESSURE_PHI = 0.82
_PRESSURE_SD = 0.24

#: Posting tours. Rotation is the largest legitimate step change in the data and
#: the generator keeps it, because the corroboration gate has to cope with a
#: subject whose workload genuinely jumped for an innocent reason.
_TOUR_MIN_DAYS = 110
_TOUR_MAX_DAYS = 230

#: Probability that a tour is served in the subject's own unit's posting class
#: rather than on a deputation somewhere else.
_HOME_POSTING_SHARE = 0.62

#: Annual leave. Long blocks, a couple of times a year.
_LEAVE_SPANS_PER_YEAR = 1.8
_LEAVE_MIN_DAYS = 8
_LEAVE_MAX_DAYS = 22

#: Pressure offset per posting class, applied as a deviation from the mix mean so
#: that a subject who never rotates carries an offset of roughly zero.
_CLASS_PRESSURE: dict[PostingClass, float] = {
    PostingClass.HIGH_INTENSITY: 0.62,
    PostingClass.MODERATE: 0.10,
    PostingClass.STATIC: -0.34,
}


@dataclass(frozen=True, slots=True)
class Exogenous:
    """Everything about a subject's circumstances that no earlier stage caused."""

    #: Daily deviation in deployment pressure, roughly zero-mean.
    pressure: FloatArray
    #: Weighted days for the D3 ``deployment_intensity`` indicator.
    intensity_weight: FloatArray
    #: Whether the subject is at a non-family station on each day.
    non_family_station: BoolArray
    #: Rostered-off blocks of annual leave. Generated here rather than in the
    #: leave stage because planned leave is roster policy, and letting the leave
    #: stage decide it would put a cycle in the chain.
    planned_leave: BoolArray


def exogenous_drivers(
    rng: np.random.Generator,
    n_days: int,
    unit: Unit,
    model: DeploymentModel,
    incident_pressure: FloatArray,
) -> Exogenous:
    """Draw a subject's posting history and daily deployment pressure."""
    starts = block_boundaries(rng, n_days, _TOUR_MIN_DAYS, _TOUR_MAX_DAYS)
    classes = _tour_classes(rng, unit, model, len(starts))

    offsets = tuple(_CLASS_PRESSURE[posting] for posting in classes)
    intensity = tuple(POSTING_INTENSITY[posting] for posting in classes)
    non_family = tuple(
        0.0 if _at_family_station(rng, unit, posting) else 1.0 for posting in classes
    )

    pressure = (
        block_series(n_days, starts, offsets)
        + ar1(rng, n_days, _PRESSURE_PHI, _PRESSURE_SD)
        + incident_pressure
    )
    planned_leave = scattered_spans(
        rng,
        n_days,
        spans_per_year=_LEAVE_SPANS_PER_YEAR,
        min_length=_LEAVE_MIN_DAYS,
        max_length=_LEAVE_MAX_DAYS,
    )
    return Exogenous(
        pressure=pressure,
        intensity_weight=block_series(n_days, starts, intensity),
        non_family_station=block_series(n_days, starts, non_family) > 0.5,
        planned_leave=planned_leave,
    )


def _tour_classes(
    rng: np.random.Generator,
    unit: Unit,
    model: DeploymentModel,
    count: int,
) -> tuple[PostingClass, ...]:
    classes = tuple(PostingClass)
    weights = _model_weights(model)
    home = rng.random(count) < _HOME_POSTING_SHARE
    away = rng.choice(len(classes), size=count, p=weights)
    return tuple(
        unit.posting_class if home[position] else classes[int(away[position])]
        for position in range(count)
    )


def _model_weights(model: DeploymentModel) -> np.ndarray:
    if model is DeploymentModel.STATIC_GUARD:
        weights = np.array([0.08, 0.27, 0.65], dtype=np.float64)
    else:
        weights = np.array([0.35, 0.40, 0.25], dtype=np.float64)
    return weights / weights.sum()


def _at_family_station(rng: np.random.Generator, unit: Unit, posting: PostingClass) -> bool:
    """Whether a tour of this class places the subject with their family.

    A unit designated a family station raises the odds but does not guarantee
    them, because a deputation out of a family station still separates a person
    from their household — which is the thing ``family_separation_days``
    measures.
    """
    base = FAMILY_STATION_PROBABILITY[posting]
    adjusted = min(base * (1.35 if unit.family_station else 0.75), 0.95)
    return bool(rng.random() < adjusted)
