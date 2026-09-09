"""Stochastic building blocks shared by the causal stages.

Two shapes recur. Slow autocorrelated drift — a fortnight of bad weeks, a
stretch of light duty — is an AR(1). Piecewise-constant regimes — a posting, a
block of annual leave — are block structures. Both are here so that each stage
module contains only its own causal content and not another copy of a filter.

Independent white noise appears nowhere as a *driver*. It is added at each stage
as measurement and idiosyncratic noise, but nothing downstream is driven by it,
which is the distinction Appendix A.3 draws between correlations that exist in
the data and correlations injected as independent noise.
"""

from __future__ import annotations

import numpy as np

from .arrays import BoolArray, FloatArray

#: Truncate the AR(1) impulse response once it falls below this. Convolving with
#: a truncated kernel is a hundred times cheaper than a Python recursion and the
#: difference is far below the noise it is modelling.
_KERNEL_FLOOR = 1e-3


def ar1(rng: np.random.Generator, n: int, phi: float, sd: float) -> FloatArray:
    """A stationary AR(1) series with the given lag-1 correlation.

    ``sd`` is the *stationary* standard deviation, not the innovation scale, so
    that changing ``phi`` to make a driver slower does not silently change how
    far it swings.
    """
    if n <= 0:
        return np.zeros(0, dtype=np.float64)
    if phi <= 0.0 or sd <= 0.0:
        return rng.normal(0.0, max(sd, 0.0), size=n).astype(np.float64, copy=False)

    innovation_sd = sd * float(np.sqrt(1.0 - phi * phi))
    length = min(n, int(np.ceil(np.log(_KERNEL_FLOOR) / np.log(phi))) + 1)
    kernel = np.power(phi, np.arange(length, dtype=np.float64))
    # Burn-in noise ahead of day zero so the series starts stationary rather than
    # at zero, which would make every subject look unusually settled in week one.
    noise = rng.normal(0.0, innovation_sd, size=n + length)
    return np.convolve(noise, kernel, mode="full")[length : length + n]


def block_boundaries(
    rng: np.random.Generator,
    n: int,
    min_length: int,
    max_length: int,
) -> tuple[int, ...]:
    """Start days of piecewise-constant regimes covering ``[0, n)``."""
    starts = [0]
    cursor = int(rng.integers(min_length, max_length + 1))
    while cursor < n:
        starts.append(cursor)
        cursor += int(rng.integers(min_length, max_length + 1))
    return tuple(starts)


def block_series(n: int, starts: tuple[int, ...], values: tuple[float, ...]) -> FloatArray:
    """Expand block values into a daily series."""
    series = np.zeros(n, dtype=np.float64)
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else n
        series[start:end] = values[position]
    return series


def scattered_spans(
    rng: np.random.Generator,
    n: int,
    *,
    spans_per_year: float,
    min_length: int,
    max_length: int,
) -> BoolArray:
    """A boolean mask of randomly placed multi-day spans.

    Used for annual leave blocks and for multi-day wearable dropouts, which are
    the same shape: a contiguous absence, several times a year, of unpredictable
    length. Modelling them as spans rather than as independent daily dropout is
    what makes the coverage tests meaningful — losing thirty scattered nights and
    losing one thirty-night block have very different effects on a ninety-day
    baseline.
    """
    mask = np.zeros(n, dtype=bool)
    expected = spans_per_year * n / 365.0
    count = int(rng.poisson(expected)) if expected > 0.0 else 0
    if count == 0:
        return mask
    starts = rng.integers(0, max(n, 1), size=count)
    lengths = rng.integers(min_length, max_length + 1, size=count)
    for start, length in zip(starts.tolist(), lengths.tolist(), strict=True):
        mask[start : min(start + length, n)] = True
    return mask


def bernoulli(rng: np.random.Generator, probabilities: FloatArray) -> BoolArray:
    return rng.random(len(probabilities)) < probabilities


def graded_response(
    drive: FloatArray,
    *,
    tolerance: float,
    floor: float = -1.0,
    ceiling: float = 4.0,
) -> FloatArray:
    """Pass a driver to the next stage through a tolerance band.

    This is the single most consequential shape in the generator and it is worth
    saying why it is not linear.

    People absorb ordinary variation. A week two hours longer than usual costs a
    constable nothing measurable; a month forty percent longer costs them their
    sleep. A linear transfer cannot express that, and modelling it linearly has a
    specific bad consequence: every subject's D1 and D4 series become strongly
    correlated purely through roster *noise*, so a healthy cohort shows the same
    cross-domain coupling as a deteriorating one, and the corroboration gate has
    nothing to discriminate on. That is precisely the failure Appendix A.3 warns
    about, arrived at from the opposite direction — correlations that exist for
    the wrong reason are as useless as correlations that do not exist.

    Implemented as ``x - t·tanh(x/t)``, which is smooth everywhere, cubic and
    therefore nearly flat inside the band, and asymptotically ``x - t`` outside
    it. The floor exists because relief saturates: a fortnight of leave does not
    buy back an unbounded amount of sleep.
    """
    band = max(tolerance, 1e-9)
    return np.clip(drive - band * np.tanh(drive / band), floor, ceiling)
