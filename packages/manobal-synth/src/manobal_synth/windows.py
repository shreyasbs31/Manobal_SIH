"""Trailing-window aggregation — the SDD §4.4 derived-indicator definitions.

Most of the thirty-six indicators the risk engine consumes are not raw
measurements, they are trailing-window aggregates: a 7-day sum of duty hours, a
28-day standard deviation of shift starts, a 28-day-against-180-day rate change.
Deriving them here from generated daily primitives, rather than sampling the
aggregate directly, is what makes the synthetic corpus internally consistent —
``duty_hours_28d`` really is four times the 7-day sum on average because both are
computed from the same roster.

It also has a large effect on detectability, and the effect is the honest one. A
28-day mean of a noisy primitive has roughly a fifth of that primitive's
day-to-day dispersion, so a slow deterioration shows up against a personal
baseline far more clearly in an aggregate than in a single night's reading. A
generator that sampled the aggregates directly with nightly-scale noise would
make the engine look blind.

Every window is *causal and expanding*: day ``t`` sees days ``t-w+1 .. t`` and
nothing later, and short windows at the start of the run use whatever history
exists. Leaking a future value here would silently invalidate every backtest
built on the output.
"""

from __future__ import annotations

import numpy as np

from .arrays import BoolArray, FloatArray, IntArray


def _window_lower_bounds(n: int, window: int) -> IntArray:
    index = np.arange(n, dtype=np.int64)
    return np.maximum(index + 1 - window, 0)


def rolling_sum(values: FloatArray, window: int) -> FloatArray:
    """Trailing sum over ``window`` days, expanding while history is short."""
    cumulative = np.concatenate((np.zeros(1), np.cumsum(values)))
    lower = _window_lower_bounds(len(values), window)
    return (cumulative[1:] - cumulative[lower]).astype(np.float64, copy=False)


def rolling_count(flags: BoolArray, window: int) -> FloatArray:
    return rolling_sum(flags.astype(np.float64), window)


def rolling_mean(values: FloatArray, window: int) -> FloatArray:
    n = len(values)
    lower = _window_lower_bounds(n, window)
    span = (np.arange(n, dtype=np.float64) + 1.0) - lower
    return rolling_sum(values, window) / span


def masked_rolling_mean(
    values: FloatArray,
    mask: BoolArray,
    window: int,
    *,
    min_count: int = 1,
    default: float = 0.0,
) -> FloatArray:
    """Trailing mean over the days where ``mask`` holds.

    Days where the mask is false are absent, not zero. Rest days must not drag a
    mean shift-start time towards midnight.

    ``min_count`` and ``default`` matter more than they look. A window in which
    almost every day is masked out produces a mean of one or two observations,
    and a caller that standardises that mean against a personal reference gets an
    enormous spurious deviation. Falling back to a caller-supplied default is
    what stops a fortnight of leave from reading as the largest workload
    excursion in a subject's history.
    """
    weights = mask.astype(np.float64)
    total = rolling_sum(values * weights, window)
    count = rolling_sum(weights, window)
    mean = total / np.maximum(count, 1.0)
    return np.where(count >= float(min_count), mean, default)


def masked_rolling_std(values: FloatArray, mask: BoolArray, window: int) -> FloatArray:
    """Trailing population standard deviation over the masked days.

    Returns zero where fewer than two observations fall in the window: a single
    reading has no dispersion, and reporting one would let a subject with almost
    no data appear to have a stable roster.
    """
    weights = mask.astype(np.float64)
    observed = values * weights
    count = rolling_sum(weights, window)
    safe = np.maximum(count, 1.0)
    mean = rolling_sum(observed, window) / safe
    mean_square = rolling_sum(observed * values, window) / safe
    variance = np.maximum(mean_square - mean * mean, 0.0)
    return np.where(count >= 2.0, np.sqrt(variance), 0.0)


def run_length(flags: BoolArray) -> FloatArray:
    """Consecutive true days ending on each day — "days since the last rest day"."""
    index = np.arange(len(flags), dtype=np.int64)
    last_false = np.maximum.accumulate(np.where(flags, -1, index))
    return (index - last_false).astype(np.float64)


def rate_delta(
    events: BoolArray,
    short_days: int,
    long_days: int,
    floor: float,
    *,
    cap: float = 4.0,
) -> FloatArray:
    """Short-window rate against long-window rate, as a proportional change.

    ``floor`` keeps a subject who has never applied for leave from producing an
    unbounded ratio the first time they do. Expressed as a proportion rather than
    a difference of rates because the SDD defines these indicators as a *change in
    frequency*, and a constable applying twice as often as usual is the signal
    regardless of whether their usual is monthly or weekly.

    ``cap`` bounds the top. Once somebody is applying five times their usual rate
    the distinction between five and fifty is noise in a rare-event count, and an
    uncapped ratio would let a single sparse baseline dominate the robust
    z-score for the whole domain.
    """
    short_rate = rolling_count(events, short_days) / float(short_days)
    long_rate = rolling_count(events, long_days) / float(long_days)
    return np.minimum(short_rate / np.maximum(long_rate, floor) - 1.0, cap)


def participation_delta(
    attended: BoolArray,
    offered: BoolArray,
    short_days: int,
    long_days: int,
) -> FloatArray:
    """Recent attendance rate minus long-run attendance rate.

    A difference of proportions, not a ratio: attendance is already normalised,
    and withdrawal from 0.8 to 0.4 should read the same as 0.4 to 0.0.
    """
    recent = masked_rolling_mean(attended.astype(np.float64), offered, short_days)
    established = masked_rolling_mean(attended.astype(np.float64), offered, long_days)
    return recent - established


def fano_factor(events: BoolArray, window: int, bin_days: int) -> FloatArray:
    """Variance-over-mean of binned event counts — burstiness, not volume.

    Bins the trailing window into ``bin_days`` blocks and reports the dispersion
    of the block counts. Three short leave requests spread across a month and
    three in one week produce the same 28-day count and very different Fano
    factors, and it is the clustering the SDD asks D2 to notice.
    """
    counts = events.astype(np.float64)
    bins = max(1, window // bin_days)
    cumulative = [rolling_sum(counts, i * bin_days) for i in range(bins + 1)]
    binned = np.stack([cumulative[i + 1] - cumulative[i] for i in range(bins)])
    mean = binned.mean(axis=0)
    variance = binned.var(axis=0)
    result = np.where(mean > 0.0, variance / np.maximum(mean, 1e-9), 0.0)
    return result.astype(np.float64, copy=False)


def carry_forward(values: FloatArray, present: BoolArray) -> FloatArray:
    """Hold the last observed value forward over days with no fresh measurement.

    Instruments are administered fortnightly, not daily, yet the risk engine
    requires twenty-one observations inside a ninety-day window before it will
    trust a baseline. A fortnightly instrument can never meet that bar as a
    sparse series. Carrying the last administered score forward is what M4's
    nightly feature derivation actually produces — the indicator is "this
    subject's current PSS-10", which has a value on every day after the first
    administration — so the generator emits it the same way.

    Days before the first measurement stay at the leading value rather than zero.
    """
    index = np.arange(len(values), dtype=np.int64)
    last_present = np.maximum.accumulate(np.where(present, index, -1))
    first = int(np.argmax(present)) if present.any() else 0
    source = np.where(last_present < 0, first, last_present)
    return values[source].astype(np.float64, copy=False)


def lagged_smooth(values: FloatArray, window: int) -> FloatArray:
    """Trailing mean, used wherever one stage of the chain drives the next.

    Sleep does not respond to today's shift; it responds to the week behind it.
    Every downstream stage reads a smoothed, strictly-trailing view of its parent
    so that the lag structure in the generated data is real rather than
    simultaneous.
    """
    return rolling_mean(values, window)
