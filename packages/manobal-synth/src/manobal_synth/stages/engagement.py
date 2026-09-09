"""Stage 7 — D7 engagement: check-in completion, app use, response latency.

The last link, and a meta-signal rather than a measurement: it is about the
*absence* of the other six. SDD §12.2 R6 names engagement collapse as the
counter to gaming, because withdrawing from the app is one of the few behaviours
a person cannot suppress by answering carefully.

This stage has a second job that no other stage has: what it produces is also
the availability mask for D5's daily check-ins. A subject who stops completing
check-ins has no ``ema_mood`` rows, so their D5 coverage falls, so D5 stops
participating in the composite. That is a real and slightly uncomfortable
property of SDD §4.5 — withdrawal reduces the very evidence that would justify
concern — and it is the mechanism the ``test_withdrawal_dilution`` suite in the
risk engine exists to bound. It has to be present here or that suite is testing
against data that cannot produce the condition.

Suppressors are treated as *engaged*. Somebody deliberately managing their
self-report keeps answering, because a person gaming the system has to stay
inside it. That leaves D7 with almost nothing to say about them, which is what
makes the objective domains carry the whole corroboration burden in the gaming
test — the hardest case, and the one worth testing.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..arrays import BoolArray, FloatArray
from ..person import PersonModel
from ..processes import bernoulli
from ..windows import carry_forward, lagged_smooth, rolling_count, rolling_sum

_AFFECT_TO_DISENGAGEMENT = 0.52
_CHURN_TO_DISENGAGEMENT = 0.34
_DISTRESS_TO_DISENGAGEMENT = 0.34
_DISENGAGEMENT_LAG_DAYS = 14

#: A suppressor's withdrawal, as a fraction of an honest subject's. Not zero —
#: staying perfectly engaged while everything else deteriorates would itself be
#: an anomaly, and the adversary being modelled is careful, not superhuman.
GAMING_ENGAGEMENT_RETENTION = 0.30

#: Proportional reduction in completion probability and in app sessions per unit
#: of disengagement, and the proportional stretch in response latency.
_COMPLETION_DECAY = 0.30
_SESSION_DECAY = 0.26
_LATENCY_STRETCH = 0.75

_COMPLETION_WINDOW = 28
_SESSION_WINDOW = 14
_LATENCY_MAX_DAYS = 30.0


@dataclass(frozen=True, slots=True)
class EngagementStage:
    indicators: dict[str, FloatArray]
    #: Days the subject completed the offered daily check-in. Consumed by the
    #: chain as the availability mask for the three D5 EMA indicators.
    checkin_completed: BoolArray


def engagement_stage(
    rng: np.random.Generator,
    person: PersonModel,
    affect: FloatArray,
    org_churn: FloatArray,
    distress_strain: FloatArray,
    instrument_days: BoolArray,
    *,
    gaming: bool,
) -> EngagementStage:
    """Generate check-in completion, app sessions and instrument latency."""
    n_days = len(affect)
    disengagement = (
        _AFFECT_TO_DISENGAGEMENT * lagged_smooth(affect, _DISENGAGEMENT_LAG_DAYS)
        + _CHURN_TO_DISENGAGEMENT * org_churn
        + _DISTRESS_TO_DISENGAGEMENT * distress_strain
    )
    if gaming:
        disengagement = disengagement * GAMING_ENGAGEMENT_RETENTION

    completed = bernoulli(
        rng,
        np.clip(
            person.trait("checkin_base_rate") * (1.0 - _COMPLETION_DECAY * disengagement),
            0.01,
            0.99,
        ),
    )
    sessions = rng.poisson(
        np.clip(person.trait("app_sessions_mean") * (1.0 - _SESSION_DECAY * disengagement), 0.0, 20.0)
    ).astype(np.float64)

    indicators = {
        "checkin_completion_rate_28d": rolling_count(completed, _COMPLETION_WINDOW)
        / np.minimum(np.arange(n_days, dtype=np.float64) + 1.0, float(_COMPLETION_WINDOW)),
        "app_session_count_14d": rolling_sum(sessions, _SESSION_WINDOW),
        "instrument_completion_latency_days": _latency(
            rng, person, disengagement, instrument_days
        ),
    }
    return EngagementStage(indicators=indicators, checkin_completed=completed)


def _latency(
    rng: np.random.Generator,
    person: PersonModel,
    disengagement: FloatArray,
    instrument_days: BoolArray,
) -> FloatArray:
    """Days between an instrument being offered and completed, held forward.

    Held forward for the same reason the instrument scores are: latency is an
    event property measured fortnightly, and a fortnightly series cannot satisfy
    the engine's twenty-one-observation baseline rule.
    """
    measured = person.trait("instrument_latency_base") * (
        1.0 + _LATENCY_STRETCH * disengagement
    ) + rng.normal(0.0, 0.45, size=len(disengagement))
    return carry_forward(np.clip(measured, 0.0, _LATENCY_MAX_DAYS), instrument_days)
