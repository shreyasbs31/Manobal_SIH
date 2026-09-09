"""Fixtures for the SDD §9.6 disparate-impact gate.

A parity gate that has never been observed to fail is not a control, it is a
decoration. These tests assert that the two profiles do opposite things: under
``neutral`` a four-fifths-rule check on rank band passes, and under ``skewed``
the same check on the same code path fails. The second assertion is the valuable
one — it is the evidence that the gate can bite.
"""

from __future__ import annotations

from collections import Counter

import pytest

from manobal_synth import GenerationConfig, build_dataset
from manobal_synth.config import FairnessProfile
from manobal_synth.fairness import NEUTRAL, SKEWED, subgroup_rates
from manobal_synth.population import RankBand

#: The four-fifths rule: the least-selected group must reach 80% of the rate of
#: the most-selected one.
FOUR_FIFTHS = 0.8


def _distress_rate_by_rank(profile: FairnessProfile) -> dict[str, float]:
    config = GenerationConfig(
        seed=515,
        personnel=1600,
        # One day of history: this measures cohort *assignment*, which happens
        # before any series is generated, so paying for 540 days of chain would
        # buy nothing.
        duration_days=40,
        distress_cohort=0.25,
        gaming_cohort=0.0,
        acute_events=0.0,
        fairness_profile=profile,
    )
    dataset = build_dataset(config)
    totals: Counter[str] = Counter()
    distressed: Counter[str] = Counter()
    for subject, cohort in zip(dataset.subjects_meta, dataset.cohorts, strict=True):
        band = str(subject.rank_band)
        totals[band] += 1
        distressed[band] += int(cohort.distressed)
    return {
        band: distressed[band] / count
        for band, count in totals.items()
        # Gazetted officers are a fraction of a percent of the force; at this
        # sample size their rate is a coin flip and would make either profile
        # look arbitrary.
        if count >= 40
    }


def _impact_ratio(rates: dict[str, float]) -> float:
    values = [rate for rate in rates.values() if rate > 0.0]
    assert values, "no subgroup had any distressed subjects"
    return min(values) / max(values)


def test_neutral_profile_passes_the_four_fifths_rule() -> None:
    ratio = _impact_ratio(_distress_rate_by_rank(FairnessProfile.NEUTRAL))
    assert ratio >= FOUR_FIFTHS, f"neutral fixture shows a rank disparity ({ratio:.2f})"


def test_skewed_profile_fails_the_four_fifths_rule() -> None:
    ratio = _impact_ratio(_distress_rate_by_rank(FairnessProfile.SKEWED))
    assert ratio < FOUR_FIFTHS, f"skewed fixture is not skewed enough to fail ({ratio:.2f})"


def test_skew_runs_in_the_declared_direction() -> None:
    rates = _distress_rate_by_rank(FairnessProfile.SKEWED)
    assert rates[str(RankBand.CONSTABLE)] > rates[str(RankBand.SI)]


@pytest.mark.parametrize("profile", list(FairnessProfile))
def test_overall_distress_rate_stays_close_to_the_requested_fraction(
    profile: FairnessProfile,
) -> None:
    """Skew redistributes risk between subgroups; it must not inflate the total.

    Otherwise ``--fairness-profile skewed`` would silently also mean "more
    distress", and any comparison between the two corpora would confound the
    two effects.
    """
    rates = _distress_rate_by_rank(profile)
    assert 0.15 <= sum(rates.values()) / len(rates) <= 0.40


def test_neutral_multipliers_are_all_one() -> None:
    assert set(NEUTRAL.rank_band.values()) == {1.0}
    assert NEUTRAL.sector_alternating == (1.0, 1.0)


def test_subgroup_rates_selects_by_profile() -> None:
    assert subgroup_rates(FairnessProfile.NEUTRAL) is NEUTRAL
    assert subgroup_rates(FairnessProfile.SKEWED) is SKEWED
