"""Personal baseline computation — SDD §4.5 step 1, FR-3.1.

The baseline is the whole modelling thesis: a jawan who has always worked long
hours is not flagged for working long hours; a jawan whose pattern *changes* is.
Everything downstream is a deviation from these numbers, so they are tested
first and hardest.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from manobal_risk.baseline import MAD_TO_SIGMA, compute_baseline, compute_baselines
from manobal_risk.types import Observation


def obs(day: int, value: float, code: str = "duty_hours_7d") -> Observation:
    return Observation(
        indicator_code=code,
        observed_on=date(2026, 1, 1) + timedelta(days=day),
        value=value,
    )


class TestComputeBaseline:
    def test_median_and_mad_of_a_constant_series(self) -> None:
        series = [obs(i, 40.0) for i in range(30)]

        result = compute_baseline("duty_hours_7d", series, window_end=date(2026, 1, 30))

        assert result.median == pytest.approx(40.0)
        assert result.mad == pytest.approx(0.0)
        assert result.n_observations == 30
        assert result.sufficient is True

    def test_mad_is_scaled_to_be_a_consistent_sigma_estimator(self) -> None:
        # Deviations from the median of [1..9] are [4,3,2,1,0,1,2,3,4]; MAD = 2.
        series = [obs(i, float(v)) for i, v in enumerate([1, 2, 3, 4, 5, 6, 7, 8, 9] * 3)]

        result = compute_baseline("duty_hours_7d", series, window_end=date(2026, 1, 30))

        assert result.median == pytest.approx(5.0)
        assert result.mad == pytest.approx(2.0 * MAD_TO_SIGMA)

    def test_median_resists_a_single_extreme_deployment(self) -> None:
        """SDD §4.5: a single 36-hour deployment must not drag the baseline and
        mask the very deviation we are trying to catch."""
        steady = [obs(i, 40.0) for i in range(29)]
        spike = [obs(29, 400.0)]

        result = compute_baseline("duty_hours_7d", steady + spike, window_end=date(2026, 1, 30))

        assert result.median == pytest.approx(40.0)

    def test_insufficient_below_the_minimum_observation_count(self) -> None:
        series = [obs(i, 40.0) for i in range(20)]

        result = compute_baseline(
            "duty_hours_7d", series, window_end=date(2026, 1, 30), min_observations=21
        )

        assert result.sufficient is False
        assert result.n_observations == 20

    def test_sufficient_exactly_at_the_minimum(self) -> None:
        series = [obs(i, 40.0) for i in range(21)]

        result = compute_baseline(
            "duty_hours_7d", series, window_end=date(2026, 1, 30), min_observations=21
        )

        assert result.sufficient is True

    def test_only_observations_inside_the_trailing_window_are_used(self) -> None:
        window_end = date(2026, 6, 30)
        inside = [obs(i, 10.0) for i in range(121, 181)]  # 2026-05-02 .. 2026-06-30
        outside = [obs(i, 999.0) for i in range(0, 60)]  # 2026-01-01 .. 2026-03-01

        result = compute_baseline(
            "duty_hours_7d", inside + outside, window_end=window_end, window_days=90
        )

        assert result.median == pytest.approx(10.0)
        assert result.n_observations == 60

    def test_observations_after_the_window_end_are_excluded(self) -> None:
        """Scoring on day N must not see day N+1. Otherwise a replay of a past
        assessment (FR-3.9) would not reproduce the original result."""
        window_end = date(2026, 2, 1)
        series = [obs(i, 10.0) for i in range(0, 31)] + [obs(i, 900.0) for i in range(40, 70)]

        result = compute_baseline("duty_hours_7d", series, window_end=window_end)

        assert result.median == pytest.approx(10.0)

    def test_empty_series_is_insufficient_not_an_error(self) -> None:
        result = compute_baseline("duty_hours_7d", [], window_end=date(2026, 1, 30))

        assert result.sufficient is False
        assert result.n_observations == 0
        assert result.mad == pytest.approx(0.0)

    def test_returns_a_frozen_value(self) -> None:
        result = compute_baseline(
            "duty_hours_7d", [obs(i, 1.0) for i in range(30)], window_end=date(2026, 1, 30)
        )

        with pytest.raises((AttributeError, TypeError)):
            result.median = 99.0  # type: ignore[misc]


class TestComputeBaselines:
    def test_groups_by_indicator_code(self) -> None:
        series = [obs(i, 40.0, "duty_hours_7d") for i in range(30)] + [
            obs(i, 5.0, "sleep_duration_min") for i in range(30)
        ]

        result = compute_baselines(series, window_end=date(2026, 1, 30))

        assert set(result) == {"duty_hours_7d", "sleep_duration_min"}
        assert result["duty_hours_7d"].median == pytest.approx(40.0)
        assert result["sleep_duration_min"].median == pytest.approx(5.0)

    def test_marks_thin_indicators_insufficient_without_dropping_them(self) -> None:
        series = [obs(i, 40.0, "duty_hours_7d") for i in range(30)] + [
            obs(i, 5.0, "spo2_nocturnal_min") for i in range(3)
        ]

        result = compute_baselines(series, window_end=date(2026, 1, 30))

        assert result["duty_hours_7d"].sufficient is True
        assert result["spo2_nocturnal_min"].sufficient is False
