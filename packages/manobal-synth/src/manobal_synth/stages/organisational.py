"""Stage 6 — D3 organisational: transfer, duty swap, training withdrawal.

The slowest-moving domain, and the ruleset weights it accordingly. Two of its
five indicators — ``deployment_intensity`` and ``family_separation_days`` — are
not driven by affect at all. They are properties of where the subject has been
posted, and they come straight from the deployment stage.

That dilution is intentional and it is worth being explicit about, because it
makes D3 a poor corroborator: a subject in genuine decline moves three of five
D3 indicators, and the domain's weighted mean is dragged towards the middle by
the two that describe their posting rather than their state. The generator
reproduces the effect rather than tidying it away, because if D3 corroborated
easily in synthetic data and not in production, every false-positive number
measured here would be wrong.

Withdrawal from optional activity is the interesting one. It is the only
indicator in the ruleset where *falling* is adverse in a purely behavioural
domain, and it is the closest organisational analogue of the D7 engagement
collapse — a person quietly stopping doing the things they used to do.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..arrays import BoolArray, FloatArray
from ..person import PersonModel
from ..processes import bernoulli
from ..windows import (
    lagged_smooth,
    participation_delta,
    rate_delta,
    rolling_count,
    rolling_sum,
    run_length,
)

_AFFECT_TO_CHURN = 0.50
_SEEKING_TO_CHURN = 0.38
_DISTRESS_TO_CHURN = 0.28
_CHURN_LAG_DAYS = 21

_TRANSFER_SENSITIVITY = 0.95
_SWAP_SENSITIVITY = 0.72
#: Withdrawal from optional activity, as a multiplicative reduction in the odds
#: of attending. Negative sign is applied at the call site.
_WITHDRAWAL_SENSITIVITY = 0.80

#: Two optional activities a week — sport, unit welfare events, voluntary
#: training. Frequent enough that a 28-day attendance rate is not dominated by
#: sampling noise, which is what makes the participation delta usable.
_ACTIVITY_PROBABILITY = 2.0 / 7.0

_TRANSFER_WINDOW = 180
_SWAP_SHORT_WINDOW = 28
_SWAP_LONG_WINDOW = 180
_PARTICIPATION_SHORT_WINDOW = 28
_PARTICIPATION_LONG_WINDOW = 180
_DEPLOYMENT_WINDOW = 365

_RATE_FLOOR = 1.0 / 365.0


@dataclass(frozen=True, slots=True)
class OrganisationalStage:
    indicators: dict[str, FloatArray]
    #: Parent of the engagement stage.
    org_churn: FloatArray


def organisational_stage(
    rng: np.random.Generator,
    person: PersonModel,
    affect: FloatArray,
    leave_seeking: FloatArray,
    distress_strain: FloatArray,
    intensity_weight: FloatArray,
    non_family_station: BoolArray,
) -> OrganisationalStage:
    """Generate organisational events and the five D3 indicators."""
    churn = (
        _AFFECT_TO_CHURN * lagged_smooth(affect, _CHURN_LAG_DAYS)
        + _SEEKING_TO_CHURN * lagged_smooth(leave_seeking, _CHURN_LAG_DAYS)
        + _DISTRESS_TO_CHURN * distress_strain
    )
    n_days = len(affect)

    transfers = bernoulli(
        rng,
        np.clip(
            person.trait("transfer_request_rate") * np.exp(_TRANSFER_SENSITIVITY * churn),
            0.0,
            0.3,
        ),
    )
    swaps = bernoulli(
        rng,
        np.clip(person.trait("duty_swap_rate") * np.exp(_SWAP_SENSITIVITY * churn), 0.0, 0.5),
    )
    offered = rng.random(n_days) < _ACTIVITY_PROBABILITY
    attended = offered & _attendance(rng, person, churn)

    indicators = {
        "transfer_request_count": rolling_count(transfers, _TRANSFER_WINDOW),
        "duty_swap_rate_delta": rate_delta(
            swaps, _SWAP_SHORT_WINDOW, _SWAP_LONG_WINDOW, _RATE_FLOOR
        ),
        "training_participation_delta": participation_delta(
            attended, offered, _PARTICIPATION_SHORT_WINDOW, _PARTICIPATION_LONG_WINDOW
        ),
        "deployment_intensity": rolling_sum(intensity_weight, _DEPLOYMENT_WINDOW),
        "family_separation_days": run_length(non_family_station),
    }
    return OrganisationalStage(indicators=indicators, org_churn=churn)


def _attendance(
    rng: np.random.Generator,
    person: PersonModel,
    churn: FloatArray,
) -> BoolArray:
    probability = person.trait("training_attend_prob") * np.exp(-_WITHDRAWAL_SENSITIVITY * churn)
    return bernoulli(rng, np.clip(probability, 0.0, 0.99))
