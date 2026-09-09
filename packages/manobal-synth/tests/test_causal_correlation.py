"""The load-bearing test: do the domains actually move together?

SDD Appendix A.3 is explicit that a generator producing uncorrelated domains
would make the corroboration gate untestable, because the gate's whole job is to
require two domains to agree before anything escalates. If D1 and D4 are
independent noise, a gate that demands corroboration and a gate that demands
nothing score identically and the design is unfalsifiable.

So this suite asserts two separate things, and the second matters more than the
first:

1. For subjects in an active decline the chain's expected signs hold — more duty
   goes with less sleep, less sleep goes with lower HRV, and so on.
2. Those associations are **markedly weaker in subjects who are not declining**.
   A generator that made every subject's domains move together would pass (1)
   while being useless: the engine would corroborate on everybody and the false
   positive rate measured against this corpus would be meaningless.

The comparison is deliberately made against stable subjects rather than against
zero. Some coupling in a healthy subject is real — a genuinely heavy fortnight
does cost sleep — and a generator that removed it would be modelling a force of
robots.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pytest

from manobal_synth.dataset import SubjectRecords

from .conftest import ScoredSubject, by_group
from .helpers import mean_finite, spearman

#: Only the trailing half of the run is examined. The early part of a
#: distressed subject's history is pre-onset and identical in character to a
#: stable subject's, so including it would dilute the contrast being measured
#: with data that is, by construction, not distressed yet.
WINDOW_DAYS = 180

#: (left, right, expected sign) for the chain links the SDD names.
CHAIN_LINKS = (
    ("duty_hours_7d", "sleep_duration_min", -1.0),
    ("duty_hours_7d", "hrv_rmssd_nightly", -1.0),
    ("sleep_duration_min", "hrv_rmssd_nightly", +1.0),
    ("sleep_duration_min", "ema_mood", +1.0),
    ("hrv_rmssd_nightly", "resting_hr_nightly", -1.0),
    ("ema_mood", "voice_f0_variability", +1.0),
)

#: How much stronger the association must be in declining subjects. A ratio
#: rather than an absolute gap, because the links differ by an order of
#: magnitude in how much of the variance they can carry.
MIN_SEPARATION_RATIO = 1.6


def _link_strength(
    subjects: Sequence[ScoredSubject],
    left: str,
    right: str,
) -> float:
    return mean_finite(
        spearman(
            subject.records.series.indicators[left][-WINDOW_DAYS:],
            subject.records.series.indicators[right][-WINDOW_DAYS:],
        )
        for subject in subjects
    )


@pytest.fixture(scope="module")
def declining(scored_cohort: Sequence[ScoredSubject]) -> tuple[ScoredSubject, ...]:
    return by_group(scored_cohort, "distress_active")


@pytest.fixture(scope="module")
def stable(scored_cohort: Sequence[ScoredSubject]) -> tuple[ScoredSubject, ...]:
    return by_group(scored_cohort, "stable")


def test_cohort_has_enough_of_each_group(
    declining: Sequence[ScoredSubject],
    stable: Sequence[ScoredSubject],
) -> None:
    assert len(declining) >= 15
    assert len(stable) >= 60


@pytest.mark.parametrize(("left", "right", "sign"), CHAIN_LINKS)
def test_chain_link_has_the_expected_sign_in_declining_subjects(
    declining: Sequence[ScoredSubject],
    left: str,
    right: str,
    sign: float,
) -> None:
    strength = _link_strength(declining, left, right)
    assert sign * strength >= 0.25, f"{left}~{right} = {strength:+.3f}"


@pytest.mark.parametrize(("left", "right", "sign"), CHAIN_LINKS)
def test_chain_link_is_stronger_in_declining_than_stable_subjects(
    declining: Sequence[ScoredSubject],
    stable: Sequence[ScoredSubject],
    left: str,
    right: str,
    sign: float,
) -> None:
    active = sign * _link_strength(declining, left, right)
    quiet = sign * _link_strength(stable, left, right)
    assert active >= MIN_SEPARATION_RATIO * max(quiet, 0.02), (
        f"{left}~{right}: declining {active:+.3f} vs stable {quiet:+.3f}"
    )


def test_distress_strain_leads_the_downstream_latents(
    declining: Sequence[ScoredSubject],
) -> None:
    """The injected trajectory must reach every stage, not just the first.

    Checked on the latents rather than the indicators because a latent carries no
    measurement noise: if the coupling is missing here it is missing in the model,
    not merely buried.
    """
    for latent in ("workload_strain", "recovery_deficit", "affect", "leave_seeking"):
        strengths = [
            spearman(
                subject.records.series.latents["distress_strain"][-WINDOW_DAYS:],
                subject.records.series.latents[latent][-WINDOW_DAYS:],
            )
            for subject in declining
        ]
        assert mean_finite(strengths) >= 0.35, latent


def test_stable_subjects_carry_no_distress_strain(
    stable: Sequence[ScoredSubject],
) -> None:
    for subject in stable:
        assert not subject.records.series.latents["distress_strain"].any()


def test_leave_seeking_follows_rather_than_leads_affect(
    declining: Sequence[ScoredSubject],
) -> None:
    """Direction of the D5 -> D2 edge, checked as a lead-lag asymmetry.

    A generator that drew both from a shared factor would show a symmetric
    cross-correlation. The SDD's chain says the person tries to get away *after*
    the mood has gone wrong, and a corpus used to justify that ordering should
    contain it.
    """
    lead, lag = [], []
    for subject in declining:
        affect = subject.records.series.latents["affect"]
        seeking = subject.records.series.latents["leave_seeking"]
        lead.append(spearman(affect[-WINDOW_DAYS:-14], seeking[-WINDOW_DAYS + 14 :]))
        lag.append(spearman(affect[-WINDOW_DAYS + 14 :], seeking[-WINDOW_DAYS:-14]))
    assert mean_finite(lead) > mean_finite(lag)


def test_unit_incidents_raise_stress_across_the_affected_unit(
    cohort: Sequence[SubjectRecords],
) -> None:
    exposed = [
        rec.series.latents["unit_pressure"].max()
        for rec in cohort
        if rec.series.latents["unit_pressure"].any()
    ]
    assert exposed, "no unit in the corpus experienced an incident"
    assert float(np.mean(exposed)) > 0.0
