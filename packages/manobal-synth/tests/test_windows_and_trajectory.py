"""The two modules where a quiet bug would corrupt everything downstream.

``windows.py`` computes the trailing aggregates that *are* the indicators, and
``trajectory.py`` is the injected ground truth. A lookahead in the first or a
step change in the second would not raise anything — it would just produce a
corpus that made the risk engine look better than it is.
"""

from __future__ import annotations

import numpy as np
import pytest

from manobal_synth.config import DistressOnset
from manobal_synth.processes import ar1, graded_response
from manobal_synth.trajectory import (
    RAMP_JITTER,
    draw_onset_days,
    draw_ramp_days,
    draw_severity,
    is_deteriorating,
    onset_bounds,
    strain_curve,
)
from manobal_synth.windows import (
    carry_forward,
    fano_factor,
    masked_rolling_mean,
    masked_rolling_std,
    rate_delta,
    rolling_count,
    rolling_mean,
    rolling_sum,
    run_length,
)

WINDOW_FUNCTIONS = (rolling_sum, rolling_mean)


@pytest.mark.parametrize("function", WINDOW_FUNCTIONS)
def test_trailing_windows_cannot_see_the_future(function: object) -> None:
    """Perturb the last day; nothing before it may move.

    The single most important property in the module. A window that leaked one
    day of lookahead would make every indicator very slightly prophetic, and the
    resulting detection numbers would be unreproducible in production.
    """
    values = np.arange(40, dtype=np.float64)
    perturbed = values.copy()
    perturbed[-1] += 1000.0
    baseline = function(values, 7)  # type: ignore[operator]
    changed = function(perturbed, 7)  # type: ignore[operator]
    assert np.array_equal(baseline[:-1], changed[:-1])
    assert baseline[-1] != changed[-1]


def test_rolling_sum_uses_only_available_history_at_the_start() -> None:
    values = np.ones(5, dtype=np.float64)
    assert list(rolling_sum(values, 3)) == [1.0, 2.0, 3.0, 3.0, 3.0]


def test_rolling_count_counts_events_not_days() -> None:
    events = np.array([True, False, True, True, False], dtype=np.bool_)
    assert list(rolling_count(events, 3)) == [1.0, 1.0, 2.0, 2.0, 2.0]


def test_run_length_resets_on_a_false() -> None:
    flags = np.array([True, True, False, True, True, True], dtype=np.bool_)
    assert list(run_length(flags)) == [1.0, 2.0, 0.0, 1.0, 2.0, 3.0]


def test_masked_mean_ignores_masked_days() -> None:
    values = np.array([10.0, 0.0, 10.0, 0.0], dtype=np.float64)
    mask = np.array([True, False, True, False], dtype=np.bool_)
    assert masked_rolling_mean(values, mask, 4)[-1] == pytest.approx(10.0)


def test_masked_mean_falls_back_when_the_window_is_almost_empty() -> None:
    """The guard that stops a fortnight of leave reading as a workload collapse."""
    values = np.array([10.0, 12.0, 0.0, 0.0, 0.0], dtype=np.float64)
    mask = np.array([True, True, False, False, False], dtype=np.bool_)
    result = masked_rolling_mean(values, mask, 3, min_count=2, default=-1.0)
    assert result[-1] == -1.0
    assert result[1] == pytest.approx(11.0)


def test_masked_std_is_zero_for_a_constant_series() -> None:
    values = np.full(10, 7.0)
    mask = np.ones(10, dtype=np.bool_)
    assert masked_rolling_std(values, mask, 5)[-1] == pytest.approx(0.0)


def test_rate_delta_is_capped() -> None:
    events = np.zeros(200, dtype=np.bool_)
    events[-5:] = True
    assert rate_delta(events, 7, 180, 1.0 / 365.0, cap=4.0)[-1] == pytest.approx(4.0)


def test_rate_delta_is_zero_when_the_rate_is_unchanged() -> None:
    events = np.zeros(200, dtype=np.bool_)
    events[::10] = True
    assert abs(rate_delta(events, 60, 180, 1.0 / 365.0)[-1]) < 0.2


def test_fano_factor_separates_clustered_from_spread_events() -> None:
    spread = np.zeros(56, dtype=np.bool_)
    spread[::7] = True
    clustered = np.zeros(56, dtype=np.bool_)
    clustered[-8:-4] = True
    assert fano_factor(clustered, 28, 4)[-1] > fano_factor(spread, 28, 4)[-1]


def test_carry_forward_holds_the_last_present_value() -> None:
    values = np.array([1.0, 99.0, 99.0, 4.0], dtype=np.float64)
    present = np.array([True, False, False, True], dtype=np.bool_)
    assert list(carry_forward(values, present)) == [1.0, 1.0, 1.0, 4.0]


def test_graded_response_ignores_small_excursions_and_passes_large_ones() -> None:
    assert abs(graded_response(np.array([0.2]), tolerance=1.0)[0]) < 0.02
    assert graded_response(np.array([4.0]), tolerance=1.0)[0] > 2.9


def test_graded_response_is_monotone_and_symmetric_within_its_bounds() -> None:
    grid = np.linspace(-4.0, 4.0, 81)
    response = graded_response(grid, tolerance=1.0, floor=-4.0, ceiling=4.0)
    assert (np.diff(response) >= -1e-12).all()
    assert response[0] == pytest.approx(-response[-1])


def test_graded_response_saturates_relief_at_the_floor() -> None:
    """Relief is bounded but overload is not, which is why the default is asymmetric."""
    assert graded_response(np.array([-8.0]), tolerance=1.0, floor=-0.5)[0] == pytest.approx(-0.5)
    assert graded_response(np.array([8.0]), tolerance=1.0, floor=-0.5)[0] > 4.0 - 1e-9


def test_ar1_is_stationary_and_reproducible() -> None:
    left = ar1(np.random.default_rng(3), 4000, 0.8, 1.0)
    right = ar1(np.random.default_rng(3), 4000, 0.8, 1.0)
    assert np.array_equal(left, right)
    assert abs(float(left.mean())) < 0.3


def test_onset_bounds_leave_history_on_both_sides() -> None:
    lower, upper = onset_bounds(540)
    assert lower >= 30
    assert upper <= 540 - 30


@pytest.mark.parametrize("model", list(DistressOnset))
def test_onset_days_respect_the_bounds(model: DistressOnset) -> None:
    lower, upper = onset_bounds(540)
    days = draw_onset_days(np.random.default_rng(9), 500, 540, model)
    assert days.min() >= lower
    assert days.max() <= upper


def test_weibull_onset_is_later_than_uniform_onset() -> None:
    """Shape above one means an accumulating hazard, not a flat one."""
    rng = np.random.default_rng(9)
    weibull = draw_onset_days(rng, 2000, 540, DistressOnset.WEIBULL)
    uniform = draw_onset_days(rng, 2000, 540, DistressOnset.UNIFORM)
    assert float(np.median(weibull)) > float(np.median(uniform))


def test_no_onsets_requested_returns_an_empty_array() -> None:
    assert len(draw_onset_days(np.random.default_rng(1), 0, 540, DistressOnset.WEIBULL)) == 0


def test_ramp_lengths_scale_with_the_horizon() -> None:
    short = draw_ramp_days(np.random.default_rng(2), 200, 120)
    long = draw_ramp_days(np.random.default_rng(2), 200, 540)
    assert float(short.mean()) < float(long.mean())
    assert short.min() >= 14.0
    assert float(long.max() / long.min()) <= (RAMP_JITTER[1] / RAMP_JITTER[0]) + 0.01


def test_severity_is_positive_and_dispersed() -> None:
    severities = draw_severity(np.random.default_rng(4), 1000)
    assert severities.min() > 0.0
    assert float(np.std(severities)) > 0.1


def test_strain_is_zero_before_onset_and_rises_gradually() -> None:
    strain = strain_curve(400, onset_day=200, ramp_days=90.0, severity=2.0)
    assert not strain[:200].any()
    assert (np.diff(strain[200:]) >= -1e-12).all()
    # "Never a step change": no single day may carry a large share of the rise.
    assert float(np.diff(strain).max()) < 0.05 * float(strain.max())


def test_strain_keeps_creeping_after_the_ramp_saturates() -> None:
    strain = strain_curve(900, onset_day=50, ramp_days=60.0, severity=1.0)
    assert strain[-1] > strain[-200]


def test_deterioration_flag_distinguishes_active_from_plateaued() -> None:
    active = strain_curve(400, onset_day=340, ramp_days=90.0, severity=2.0)
    plateaued = strain_curve(400, onset_day=20, ramp_days=60.0, severity=2.0)
    assert is_deteriorating(active)
    assert not is_deteriorating(plateaued)


def test_a_subject_who_never_declined_is_not_deteriorating() -> None:
    assert not is_deteriorating(np.zeros(400, dtype=np.float64))
