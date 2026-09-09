"""Personal baselines — SDD §4.5 step 1, FR-3.1.

    mu    = median(x)
    sigma = 1.4826 * MAD(x)

over a trailing 90-day window with a minimum of 21 observations.

Median and MAD rather than mean and standard deviation because duty data is
bursty and heavy-tailed: a single 36-hour deployment would drag a mean baseline
upward and mask the very deviation the system exists to catch.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import date, timedelta

import numpy as np

from .types import Baseline, Observation

#: Scales the median absolute deviation into a consistent estimator of sigma for
#: normally distributed data, so that downstream thresholds can be reasoned about
#: in familiar standard-deviation units.
MAD_TO_SIGMA = 1.4826

DEFAULT_WINDOW_DAYS = 90
DEFAULT_MIN_OBSERVATIONS = 21


def compute_baseline(
    indicator_code: str,
    observations: Iterable[Observation],
    *,
    window_end: date,
    window_days: int = DEFAULT_WINDOW_DAYS,
    min_observations: int = DEFAULT_MIN_OBSERVATIONS,
) -> Baseline:
    """Establish one subject's own norm for one indicator.

    Observations after ``window_end`` are excluded. That is not defensive
    tidiness: without it, replaying a past assessment (FR-3.9) would see data the
    original run could not have seen and would produce a different answer.

    A window with too few observations returns ``sufficient=False`` rather than
    raising. The indicator is then excluded from scoring entirely — never
    defaulted to zero, which would assert that a person is fine when the truth is
    that we have not watched them long enough to know.
    """
    window_start = window_end - timedelta(days=window_days - 1)
    values = [
        o.value
        for o in observations
        if o.indicator_code == indicator_code and window_start <= o.observed_on <= window_end
    ]

    n = len(values)
    if n == 0:
        return Baseline(
            indicator_code=indicator_code,
            window_end=window_end,
            median=0.0,
            mad=0.0,
            n_observations=0,
            sufficient=False,
        )

    arr = np.asarray(values, dtype=float)
    median = float(np.median(arr))
    mad = float(np.median(np.abs(arr - median))) * MAD_TO_SIGMA

    return Baseline(
        indicator_code=indicator_code,
        window_end=window_end,
        median=median,
        mad=mad,
        n_observations=n,
        sufficient=n >= min_observations,
    )


def compute_baselines(
    observations: Iterable[Observation],
    *,
    window_end: date,
    window_days: int = DEFAULT_WINDOW_DAYS,
    min_observations: int = DEFAULT_MIN_OBSERVATIONS,
) -> dict[str, Baseline]:
    """Compute a baseline per indicator code present in ``observations``.

    Indicators with too little history are returned marked insufficient rather
    than omitted, so that callers can distinguish "this person has no wearable"
    from "this person has a wearable we have only seen for three days" — a
    distinction that matters for the coverage calculation.
    """
    grouped: dict[str, list[Observation]] = defaultdict(list)
    for observation in observations:
        grouped[observation.indicator_code].append(observation)

    return {
        code: compute_baseline(
            code,
            series,
            window_end=window_end,
            window_days=window_days,
            min_observations=min_observations,
        )
        for code, series in grouped.items()
    }
