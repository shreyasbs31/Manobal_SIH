"""Shared fixtures for the risk-engine test suites."""

from __future__ import annotations

from datetime import date

from manobal_risk.types import Baseline


def make_baseline(
    code: str = "duty_hours_7d",
    *,
    median: float = 40.0,
    mad: float = 4.0,
    n_observations: int = 30,
    sufficient: bool = True,
    window_end: date = date(2026, 1, 30),
) -> Baseline:
    return Baseline(
        indicator_code=code,
        window_end=window_end,
        median=median,
        mad=mad,
        n_observations=n_observations,
        sufficient=sufficient,
    )
