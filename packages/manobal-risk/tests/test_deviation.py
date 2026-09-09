"""Indicator deviation — SDD §4.5 step 2, FR-3.2.

    z = ((x - mu) / max(sigma, eps)) * d      z_hat = clip(z / 3, 0, 1)

Two properties matter more than the arithmetic: an indicator moving in the
*benign* direction must contribute zero rather than a negative offset that could
mask an adverse indicator elsewhere, and the epsilon floor must stop a very
stable person being flagged for a trivial absolute change.
"""

from __future__ import annotations

from datetime import date

import pytest

from manobal_risk.deviation import compute_deviation
from manobal_risk.ruleset import IndicatorSpec
from manobal_risk.types import Baseline, Direction, Domain


def baseline(median: float = 40.0, mad: float = 4.0, sufficient: bool = True) -> Baseline:
    return Baseline(
        indicator_code="duty_hours_7d",
        window_end=date(2026, 1, 30),
        median=median,
        mad=mad,
        n_observations=30,
        sufficient=sufficient,
    )


def spec(direction: Direction = Direction.RISING_IS_ADVERSE, epsilon: float = 1.0) -> IndicatorSpec:
    return IndicatorSpec(
        code="duty_hours_7d",
        domain=Domain.WORKLOAD,
        direction=direction,
        epsilon=epsilon,
    )


class TestComputeDeviation:
    def test_value_at_the_baseline_median_deviates_zero(self) -> None:
        result = compute_deviation(spec(), baseline(), observed_value=40.0, z_divisor=3.0)

        assert result is not None
        assert result.deviation == pytest.approx(0.0)

    def test_three_sigma_adverse_saturates_at_one(self) -> None:
        result = compute_deviation(spec(), baseline(), observed_value=52.0, z_divisor=3.0)

        assert result is not None
        assert result.deviation == pytest.approx(1.0)

    def test_one_and_a_half_sigma_adverse_is_half(self) -> None:
        result = compute_deviation(spec(), baseline(), observed_value=46.0, z_divisor=3.0)

        assert result is not None
        assert result.deviation == pytest.approx(0.5)

    def test_beyond_three_sigma_clips_rather_than_dominating(self) -> None:
        """Clipping is what stops one catastrophic indicator swamping a domain
        mean and back-dooring the corroboration gate."""
        result = compute_deviation(spec(), baseline(), observed_value=4000.0, z_divisor=3.0)

        assert result is not None
        assert result.deviation == pytest.approx(1.0)

    def test_movement_in_the_benign_direction_clips_to_zero(self) -> None:
        """Not negative. A person sleeping unusually well must not earn credit
        that offsets a genuine workload deviation."""
        result = compute_deviation(spec(), baseline(), observed_value=10.0, z_divisor=3.0)

        assert result is not None
        assert result.deviation == pytest.approx(0.0)

    def test_falling_is_adverse_inverts_the_sign(self) -> None:
        falling = spec(direction=Direction.FALLING_IS_ADVERSE)

        adverse = compute_deviation(falling, baseline(), observed_value=28.0, z_divisor=3.0)
        benign = compute_deviation(falling, baseline(), observed_value=52.0, z_divisor=3.0)

        assert adverse is not None and adverse.deviation == pytest.approx(1.0)
        assert benign is not None and benign.deviation == pytest.approx(0.0)

    def test_epsilon_floors_the_denominator_for_a_very_stable_subject(self) -> None:
        """With MAD ~ 0, a raw z-score is undefined or enormous. The floor means
        a person whose duty hours never vary is not flagged for a one-hour change."""
        rock_steady = baseline(median=40.0, mad=0.0)

        result = compute_deviation(
            spec(epsilon=6.0), rock_steady, observed_value=41.0, z_divisor=3.0
        )

        assert result is not None
        assert result.deviation == pytest.approx(1.0 / 18.0)

    def test_epsilon_is_a_floor_not_a_replacement(self) -> None:
        """When the observed MAD exceeds epsilon, the subject's own variability
        wins — that is the point of a baseline of one."""
        wide = baseline(median=40.0, mad=30.0)

        result = compute_deviation(spec(epsilon=1.0), wide, observed_value=70.0, z_divisor=3.0)

        assert result is not None
        assert result.deviation == pytest.approx(1.0 / 3.0)

    def test_insufficient_baseline_yields_no_deviation(self) -> None:
        """FR-3.1: below the minimum observation count the indicator is excluded,
        not defaulted to zero. Defaulting to zero would silently claim a person
        is fine when we simply have not watched them long enough."""
        result = compute_deviation(
            spec(), baseline(sufficient=False), observed_value=999.0, z_divisor=3.0
        )

        assert result is None

    def test_deviation_is_always_within_the_unit_interval(self) -> None:
        for value in (-1e9, -10.0, 0.0, 40.0, 41.0, 1e9):
            result = compute_deviation(spec(), baseline(), observed_value=value, z_divisor=3.0)
            assert result is not None
            assert 0.0 <= result.deviation <= 1.0

    def test_carries_its_provenance(self) -> None:
        """FR-3.9 replayability: a deviation must say which baseline produced it."""
        b = baseline()

        result = compute_deviation(spec(), b, observed_value=46.0, z_divisor=3.0)

        assert result is not None
        assert result.indicator_code == "duty_hours_7d"
        assert result.domain is Domain.WORKLOAD
        assert result.observed_value == pytest.approx(46.0)
        assert result.baseline == b
