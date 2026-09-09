"""Stage 1 — D1 workload: duty hours, rest denial, roster volatility.

Deployment pressure and the injected distress strain arrive here as one
dimensionless *load*. Load does not become an indicator directly; it changes the
roster, and the indicators are then derived from the roster the way SDD §4.4
derives them from the HRMS delta. A longer shift, a rest day worked, a shift
start pushed around — those are the primitives, and ``duty_hours_7d`` is their
seven-day sum.

Deriving rather than sampling matters twice over. It keeps the five D1
indicators mutually consistent, so a subject cannot have rising weekly hours and
falling monthly hours. And it means the aggregates carry roughly a fifth of the
day-to-day dispersion of the primitives, so a slow deterioration is visible
against a personal baseline — which is the honest picture, because a real feature
store computes these the same way.

Why distress raises workload rather than the reverse: the causal direction in the
SDD runs from deployment to workload to everything else, and the distressed
cohort represents personnel whose *circumstances* are deteriorating. A second,
smaller share of the strain enters again at the affect stage, for the part of
distress that has nothing to do with duty.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..arrays import BoolArray, FloatArray
from ..person import PersonModel
from ..processes import bernoulli
from ..windows import (
    masked_rolling_std,
    rolling_count,
    rolling_mean,
    rolling_sum,
    run_length,
)
from .deployment import Exogenous

#: How much of the distress strain expresses itself as harder duty.
STRAIN_TO_LOAD = 1.15

#: Proportional rise in shift length per unit of load.
_HOURS_SENSITIVITY = 0.155
#: Multiplicative effect of load on the odds of a scheduled rest day being worked.
_DENIAL_SENSITIVITY = 0.80
#: Proportional inflation of shift-start dispersion per unit of load. This is the
#: circadian-disruption path: a busy unit does not merely work longer, it works
#: less predictably.
_START_VOLATILITY_SENSITIVITY = 0.60

_MIN_SHIFT_HOURS = 2.5
_MAX_SHIFT_HOURS = 22.0

#: Nominal duty days per week, used to turn a per-shift trait into the subject's
#: own expected weekly load. Referencing the person's own norm rather than a
#: population mean is what keeps a permanently heavy roster at zero strain.
_DUTY_DAY_SHARE = 6.0 / 7.0

#: A load of one is defined as a sixteen-percent rise in weekly hours above the
#: subject's own norm, so that downstream sensitivities can be read as "per
#: sixteen percent of extra duty".
_HOURS_STRAIN_SCALE = 0.16
_DENIAL_STRAIN_SCALE = 3.0
_DENIAL_STRAIN_WEIGHT = 0.35

_VOLATILITY_WINDOW = 28
_DENIAL_WINDOW = 28


@dataclass(frozen=True, slots=True)
class WorkloadStage:
    indicators: dict[str, FloatArray]
    #: Realised workload deviation from the subject's own norm. The parent of
    #: every physiological indicator downstream.
    strain: FloatArray
    on_duty: BoolArray
    rest_day: BoolArray


def workload_stage(
    rng: np.random.Generator,
    person: PersonModel,
    exogenous: Exogenous,
    distress_strain: FloatArray,
) -> WorkloadStage:
    """Generate the roster and the five D1 indicators from it."""
    n_days = len(exogenous.pressure)
    load = exogenous.pressure + STRAIN_TO_LOAD * distress_strain

    scheduled_rest = (np.arange(n_days) % 7) == person.rest_weekday
    denial_probability = np.clip(
        person.trait("rest_denial_base") * np.exp(_DENIAL_SENSITIVITY * load), 0.0, 0.95
    )
    rest_denied = scheduled_rest & ~exogenous.planned_leave & bernoulli(rng, denial_probability)
    on_duty = ~exogenous.planned_leave & (~scheduled_rest | rest_denied)

    duty_hours = _duty_hours(rng, person, load, on_duty)
    shift_start = _shift_start(rng, person, load, n_days)

    indicators = {
        "duty_hours_7d": rolling_sum(duty_hours, 7),
        "duty_hours_28d": rolling_sum(duty_hours, 28),
        "consecutive_duty_days": run_length(on_duty),
        "roster_volatility": masked_rolling_std(shift_start, on_duty, _VOLATILITY_WINDOW),
        "rest_denial_count": rolling_count(rest_denied, _DENIAL_WINDOW),
    }
    return WorkloadStage(
        indicators=indicators,
        strain=_workload_strain(person, duty_hours, indicators["rest_denial_count"]),
        on_duty=on_duty,
        rest_day=scheduled_rest & ~rest_denied,
    )


def _duty_hours(
    rng: np.random.Generator,
    person: PersonModel,
    load: FloatArray,
    on_duty: BoolArray,
) -> FloatArray:
    mean_hours = person.trait("shift_hours_mean")
    hours = mean_hours * (1.0 + _HOURS_SENSITIVITY * load)
    hours = hours + rng.normal(0.0, person.trait("shift_hours_sd"), size=len(load))
    return np.where(on_duty, np.clip(hours, _MIN_SHIFT_HOURS, _MAX_SHIFT_HOURS), 0.0)


def _shift_start(
    rng: np.random.Generator,
    person: PersonModel,
    load: FloatArray,
    n_days: int,
) -> FloatArray:
    spread = person.trait("shift_start_sd") * np.maximum(
        1.0 + _START_VOLATILITY_SENSITIVITY * load, 0.15
    )
    return person.trait("shift_start_mean") + spread * rng.normal(0.0, 1.0, size=n_days)


def _workload_strain(
    person: PersonModel,
    duty_hours: FloatArray,
    rest_denial_count: FloatArray,
) -> FloatArray:
    """Standardise realised duty against this subject's own expected load.

    Expressed against an analytic personal reference rather than against the
    run's own mean, so that no downstream stage can be driven by a statistic that
    depends on days it has not reached yet.
    """
    reference = person.trait("shift_hours_mean") * _DUTY_DAY_SHARE
    hours_term = (rolling_mean(duty_hours, 7) - reference) / (_HOURS_STRAIN_SCALE * reference)
    expected_denials = (_DENIAL_WINDOW / 7.0) * person.trait("rest_denial_base")
    denial_term = (rest_denial_count - expected_denials) / _DENIAL_STRAIN_SCALE
    return hours_term + _DENIAL_STRAIN_WEIGHT * denial_term
