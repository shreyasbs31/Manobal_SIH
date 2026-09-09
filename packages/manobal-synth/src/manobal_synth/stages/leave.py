"""Stage 5 — D2 leave: leave-seeking, burstiness, unplanned absence.

Leave-seeking sits downstream of affect and of workload, which is the order the
SDD's chain gives it: a person tries to get away *after* the duty and the mood
have gone wrong. That ordering is what makes D2 useful as a corroborating domain
for a subject who never enrolled — it is derived from the HRMS leave record, so
it is available for everyone on the strength, and it moves because affect moved
even though affect itself was never observed.

Rates respond multiplicatively. A constable who normally applies once a month
applying three times in a fortnight is the signal, and the same absolute increase
means something entirely different for somebody who applies weekly. The
indicators are then rate *changes* against the subject's own trailing 180 days,
per SDD §4.4, so the personal baseline is built into the indicator definition
before the engine even sees it.

Burstiness is modelled separately from volume, because they say different things.
Three short-leave requests spread over a month is a person managing their life;
three in one week is a person trying to get out. The Fano factor over four-day
bins is what separates them, so the generator drives clustering with its own
autocorrelated modulator rather than letting it fall out of a flat hazard.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..arrays import BoolArray, FloatArray
from ..person import PersonModel
from ..processes import ar1, bernoulli
from ..windows import fano_factor, lagged_smooth, rate_delta, rolling_count

_AFFECT_TO_SEEKING = 0.60
_WORKLOAD_TO_SEEKING = 0.26
_DISTRESS_TO_SEEKING = 0.45
_SEEKING_LAG_DAYS = 10

#: Multiplicative sensitivities of the three daily hazards. Unplanned absence
#: responds hardest: it is the point at which somebody stops asking.
_APPLY_SENSITIVITY = 0.85
_ABSENCE_SENSITIVITY = 1.30

#: Clustering modulator for short leave. Slow enough to produce runs of a week or
#: two, which is the timescale the four-day Fano bins can resolve.
_CLUSTER_PHI = 0.86
_CLUSTER_SD = 0.55
_CLUSTER_SENSITIVITY = 0.70

#: A unit under pressure grants less leave, so rejection rises with the same
#: deployment load that drove the application. Rejection is *not* fed back into
#: affect: the chain is acyclic by construction, and a feedback loop here would
#: make the injected ground truth impossible to state cleanly.
_REJECTION_SENSITIVITY = 0.30

_APPLY_SHORT_WINDOW = 28
_APPLY_LONG_WINDOW = 180
_REJECTION_WINDOW = 90
_ABSENCE_WINDOW = 28
_BURSTINESS_WINDOW = 28
_BURSTINESS_BIN_DAYS = 4

#: Floor on the long-run rate in the rate-delta denominator, in events per day.
#: Roughly one application a year: below that the ratio is measuring noise.
_RATE_FLOOR = 1.0 / 365.0

#: Ceilings on the daily hazards, in events per day. Even a subject in severe
#: decline does not apply for leave every other day; without these the
#: exponential response runs away at high strain and produces counts that no
#: HRMS extract would ever contain.
_APPLY_HAZARD_CAP = 0.18
_ABSENCE_HAZARD_CAP = 0.14


@dataclass(frozen=True, slots=True)
class LeaveStage:
    indicators: dict[str, FloatArray]
    #: Parent of the organisational stage: the same impulse that produces a leave
    #: application produces a transfer request a few weeks later.
    leave_seeking: FloatArray


def leave_stage(
    rng: np.random.Generator,
    person: PersonModel,
    affect: FloatArray,
    workload_strain: FloatArray,
    distress_strain: FloatArray,
    unit_pressure: FloatArray,
) -> LeaveStage:
    """Generate leave events and the four D2 indicators derived from them."""
    seeking = (
        _AFFECT_TO_SEEKING * lagged_smooth(affect, _SEEKING_LAG_DAYS)
        + _WORKLOAD_TO_SEEKING * lagged_smooth(workload_strain, _SEEKING_LAG_DAYS)
        + _DISTRESS_TO_SEEKING * distress_strain
    )

    applications = _applications(rng, person, seeking)
    short_leave = _short_leave(rng, person, seeking, applications)
    rejected = _rejections(rng, person, applications, unit_pressure)
    absences = _absences(rng, person, seeking)

    indicators = {
        "leave_apply_rate_delta": rate_delta(
            applications, _APPLY_SHORT_WINDOW, _APPLY_LONG_WINDOW, _RATE_FLOOR
        ),
        "short_leave_burstiness": fano_factor(
            short_leave, _BURSTINESS_WINDOW, _BURSTINESS_BIN_DAYS
        ),
        "leave_rejection_count": rolling_count(rejected, _REJECTION_WINDOW),
        "unplanned_absence_count": rolling_count(absences, _ABSENCE_WINDOW),
    }
    return LeaveStage(indicators=indicators, leave_seeking=seeking)


def _applications(
    rng: np.random.Generator,
    person: PersonModel,
    seeking: FloatArray,
) -> BoolArray:
    hazard = person.trait("leave_apply_rate") * np.exp(_APPLY_SENSITIVITY * seeking)
    return bernoulli(rng, np.clip(hazard, 0.0, _APPLY_HAZARD_CAP))


def _short_leave(
    rng: np.random.Generator,
    person: PersonModel,
    seeking: FloatArray,
    applications: BoolArray,
) -> BoolArray:
    cluster = ar1(rng, len(seeking), _CLUSTER_PHI, _CLUSTER_SD)
    share = person.trait("short_leave_share") * np.exp(_CLUSTER_SENSITIVITY * (cluster + seeking))
    return applications & bernoulli(rng, np.clip(share, 0.0, 0.98))


def _rejections(
    rng: np.random.Generator,
    person: PersonModel,
    applications: BoolArray,
    unit_pressure: FloatArray,
) -> BoolArray:
    probability = person.trait("leave_rejection_prob") * np.exp(
        _REJECTION_SENSITIVITY * unit_pressure
    )
    return applications & bernoulli(rng, np.clip(probability, 0.0, 0.95))


def _absences(
    rng: np.random.Generator,
    person: PersonModel,
    seeking: FloatArray,
) -> BoolArray:
    hazard = person.trait("unplanned_absence_rate") * np.exp(_ABSENCE_SENSITIVITY * seeking)
    return bernoulli(rng, np.clip(hazard, 0.0, _ABSENCE_HAZARD_CAP))
