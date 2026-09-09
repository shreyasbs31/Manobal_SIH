"""The injected distress trajectory — ``--distress-cohort``, ``--distress-onset``.

This module is the ground truth. Everything the risk engine is later asked to
find enters the data here, and it enters as a *shape over time*, never as a flag
on a row.

Three modelling decisions carry the weight.

**Onset is a truncated Weibull.** ``--distress-onset weibull`` is the SDD's
wording. A Weibull with shape above one puts little mass at the very beginning
and a long tail, which matches an accumulating hazard: the risk of decline grows
with time in a hard posting. Truncation rather than clipping keeps every
distressed subject with at least thirty days of clean pre-onset history — so a
personal baseline can form before anything moves — and at least twenty-one days
of post-onset observation, so nothing is injected that could not in principle be
seen.

**The decline is a gradual ramp, never a step.** Severity follows a Weibull CDF
in elapsed days since onset, so it starts almost flat, accelerates, then eases.
A step change would be trivially detectable by any change-point method and would
tell us nothing about whether a trailing-median personal baseline can find a
slow slide, which is the question the whole risk engine rests on.

**The decline is still progressing at the end of the window.** After the ramp
saturates a slow creep continues, and the ramp length is scaled to the
observation horizon. This is deliberate and it is the one place where the
generator makes a modelling assumption that deserves stating out loud: a
deterioration that plateaued a year ago is *invisible* to a baseline-of-one
system by construction, because the subject's own trailing median has moved with
them. That is a real limitation of SDD §4.5, not an artefact to hide, and the
generator reproduces it — early-onset subjects here genuinely do fade back
towards their own new normal and are recorded in ground truth as no longer
deteriorating, which is what makes them usable as the false-negative population
for K4.
"""

from __future__ import annotations

import numpy as np

from .arrays import FloatArray, IntArray
from .config import DistressOnset

#: Shape above one: an accumulating hazard rather than a constant one.
ONSET_SHAPE = 1.6
#: Scale as a fraction of the run. Places the median onset around 55% of the way
#: through, leaving a mix of long-established and recent declines at the end.
ONSET_SCALE_FRACTION = 0.62
MIN_PRE_ONSET_DAYS = 30
MIN_OBSERVED_DAYS = 21

#: Ramp shape 2.2 gives a decline that is convex for most of its length. That
#: convexity is what a trailing-median baseline can actually resolve: on a purely
#: linear slide the median absolute deviation grows with the trend and the robust
#: z-score saturates around 1.35 no matter how steep the slide gets.
RAMP_SHAPE = 2.2
RAMP_REFERENCE_FRACTION = 0.42
RAMP_MIN_DAYS = 45.0
RAMP_MAX_DAYS = 200.0
RAMP_JITTER = (0.55, 1.05)

#: Additional severity per year once the ramp has saturated. Untreated decline
#: does not simply stop, and without this an early-onset subject would be exactly
#: flat and therefore exactly invisible.
CREEP_PER_YEAR = 0.20

SEVERITY_MEDIAN = 0.90
SEVERITY_LOG_SD = 0.30
SEVERITY_MIN = 0.35
SEVERITY_MAX = 1.70

#: Rise in severity over the trailing four weeks above which a subject counts as
#: actively deteriorating at the end of the window.
DETERIORATION_WINDOW_DAYS = 28
DETERIORATION_THRESHOLD = 0.04


def onset_bounds(duration_days: int) -> tuple[float, float]:
    """Earliest and latest onset day that leave usable history on both sides."""
    latest = float(max(duration_days - MIN_OBSERVED_DAYS, MIN_PRE_ONSET_DAYS + 1))
    return float(MIN_PRE_ONSET_DAYS), latest


def draw_onset_days(
    rng: np.random.Generator,
    count: int,
    duration_days: int,
    model: DistressOnset,
) -> IntArray:
    """Draw onset days for ``count`` distressed subjects."""
    lower, upper = onset_bounds(duration_days)
    if count == 0:
        return np.zeros(0, dtype=np.int64)
    if model is DistressOnset.UNIFORM:
        draws = rng.uniform(lower, upper, size=count)
    else:
        draws = _truncated_weibull(rng, count, duration_days, lower, upper)
    return np.floor(draws).astype(np.int64)


def _truncated_weibull(
    rng: np.random.Generator,
    count: int,
    duration_days: int,
    lower: float,
    upper: float,
) -> FloatArray:
    """Inverse-CDF sampling from a Weibull truncated to ``[lower, upper]``.

    Inverting the CDF rather than rejecting draws keeps the number of random
    values consumed independent of the bounds, which is what stops a change in
    ``--duration-days`` from perturbing every later substream.
    """
    scale = max(ONSET_SCALE_FRACTION * duration_days, 1.0)

    def cdf(x: float) -> float:
        return 1.0 - float(np.exp(-((x / scale) ** ONSET_SHAPE)))

    low, high = cdf(lower), cdf(upper)
    quantiles = rng.uniform(low, high, size=count)
    return scale * np.power(-np.log1p(-quantiles), 1.0 / ONSET_SHAPE)


def draw_ramp_days(rng: np.random.Generator, count: int, duration_days: int) -> FloatArray:
    """Draw per-subject ramp lengths, scaled to the observation horizon.

    Scaling to the horizon is what keeps a 540-day run and a 120-day smoke run
    both producing declines that are mid-slide at the end rather than either
    invisible or instantaneous.
    """
    reference = float(np.clip(RAMP_REFERENCE_FRACTION * duration_days, RAMP_MIN_DAYS, RAMP_MAX_DAYS))
    jitter = rng.uniform(RAMP_JITTER[0], RAMP_JITTER[1], size=count)
    return np.maximum(reference * jitter, 14.0)


def draw_severity(rng: np.random.Generator, count: int) -> FloatArray:
    """Draw per-subject terminal severity, in units of the full domain effect.

    Log-normal so that most declines are moderate and a few are severe. A
    cohort in which everyone declines equally would make the tier distribution a
    step function and hide whether the engine's thresholds discriminate at all.
    """
    draws = SEVERITY_MEDIAN * np.exp(rng.normal(0.0, SEVERITY_LOG_SD, size=count))
    return np.clip(draws, SEVERITY_MIN, SEVERITY_MAX)


def strain_curve(
    n_days: int,
    *,
    onset_day: int,
    ramp_days: float,
    severity: float,
) -> FloatArray:
    """The subject's daily distress strain, zero before onset.

    Returned in "domain effect units": 1.0 means the full modelled deterioration
    for every downstream indicator. Each stage of the causal chain scales this by
    its own sensitivity.
    """
    days = np.arange(n_days, dtype=np.float64)
    elapsed = np.maximum(days - float(onset_day), 0.0)
    ramp = max(ramp_days, 1.0)
    progress = 1.0 - np.exp(-np.power(elapsed / ramp, RAMP_SHAPE))
    creep = CREEP_PER_YEAR * np.maximum(elapsed - ramp, 0.0) / 365.0
    started = days >= float(onset_day)
    return (severity * (progress + creep) * started).astype(np.float64, copy=False)


def flat_strain(n_days: int) -> FloatArray:
    return np.zeros(n_days, dtype=np.float64)


def is_deteriorating(strain: FloatArray) -> bool:
    """Whether the trajectory is still worsening at the end of the window.

    Recorded in ground truth so that a false-negative measurement can separate
    "the engine missed an active decline" from "the decline finished a year ago
    and the subject's own baseline has absorbed it".
    """
    if len(strain) <= DETERIORATION_WINDOW_DAYS:
        return bool(strain[-1] > DETERIORATION_THRESHOLD)
    rise = float(strain[-1] - strain[-1 - DETERIORATION_WINDOW_DAYS])
    return rise > DETERIORATION_THRESHOLD
