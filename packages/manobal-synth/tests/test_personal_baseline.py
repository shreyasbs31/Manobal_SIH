"""Requirement: deviation is measured against the person, not the population.

This is the assumption the whole risk engine rests on, and it is the one a naive
generator gets wrong. If every subject were drawn around a shared mean, then a
constable who has worked ninety-hour weeks for a decade would score as
permanently distressed and the corpus would silently reward a population-norm
engine.

The test therefore builds two subjects by hand and feeds them to the real
deviation machinery: one whose workload has always been high, and one whose
workload has recently *become* high. The first must score near zero and the
second must not.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta

import numpy as np
import pytest

from manobal_risk import Domain, Observation, Ruleset, SubjectHistory, score_with_trace
from manobal_synth import GenerationConfig, build_dataset
from manobal_synth.config import ConsentProfile, MissingnessProfile
from manobal_synth.person import build_person
from manobal_synth.population import build_subjects, build_units

DAYS = 200
START = date(2025, 1, 1)
INDICATOR = "duty_hours_7d"


def _history(values: Sequence[float], ruleset: Ruleset) -> SubjectHistory:
    return SubjectHistory(
        subject_token="st_" + "a" * 26,
        as_of=START + timedelta(days=len(values) - 1),
        observations=tuple(
            Observation(INDICATOR, START + timedelta(days=day), float(value))
            for day, value in enumerate(values)
        ),
        consented_domains=frozenset(Domain(domain.value) for domain in ruleset.domains),
    )


def _workload_deviation(values: Sequence[float], ruleset: Ruleset) -> float:
    _, trace = score_with_trace(_history(values, ruleset), ruleset)
    matching = [d for d in trace.indicator_deviations if d.indicator_code == INDICATOR]
    assert matching, "the engine did not score the indicator at all"
    return matching[0].deviation


def test_permanently_high_workload_is_not_a_deviation(ruleset: Ruleset) -> None:
    rng = np.random.default_rng(1)
    always_high = 96.0 + rng.normal(0.0, 3.0, size=DAYS)
    assert _workload_deviation(always_high, ruleset) < 0.15


def test_recently_raised_workload_is_a_deviation(ruleset: Ruleset) -> None:
    rng = np.random.default_rng(1)
    values = 56.0 + rng.normal(0.0, 3.0, size=DAYS)
    values[-30:] += 40.0
    assert _workload_deviation(values, ruleset) > 0.5


def test_the_two_end_at_the_same_absolute_level(ruleset: Ruleset) -> None:
    """The contrast is history, not level — otherwise the test proves nothing."""
    rng = np.random.default_rng(1)
    always_high = 96.0 + rng.normal(0.0, 3.0, size=DAYS)
    recently_high = 56.0 + rng.normal(0.0, 3.0, size=DAYS)
    recently_high[-30:] += 40.0
    assert abs(always_high[-30:].mean() - recently_high[-30:].mean()) < 5.0


@pytest.mark.parametrize(
    "trait",
    ["shift_hours_mean", "sleep_duration_mean", "hrv_rmssd_mean", "resting_hr_mean"],
)
def test_generated_baselines_vary_between_people(trait: str) -> None:
    config = GenerationConfig(seed=5, personnel=120, duration_days=60)
    units = build_units(config)
    subjects = build_subjects(config, units)
    values = [build_person(config.seed, subject).trait(trait) for subject in subjects]
    spread = float(np.std(values)) / abs(float(np.mean(values)))
    assert spread > 0.04, f"{trait} is near-identical across the force"


def test_generated_baselines_are_stable_within_a_person() -> None:
    """A non-distressed subject's own level must not drift over the run.

    Drift would be indistinguishable from a slow decline to a trailing-median
    baseline, so a generator with drifting healthy subjects would manufacture the
    false positives it is supposed to measure.
    """
    config = GenerationConfig(
        seed=6,
        personnel=40,
        duration_days=540,
        distress_cohort=0.0,
        gaming_cohort=0.0,
        acute_events=0.0,
        consent_profile=ConsentProfile.FULL,
        missingness=MissingnessProfile.NONE,
    )
    for records in build_dataset(config).iter_subjects():
        series = records.series.indicators["sleep_duration_min"]
        first_quarter = float(np.median(series[:135]))
        last_quarter = float(np.median(series[-135:]))
        assert abs(last_quarter - first_quarter) < 25.0
