"""End-to-end: generated rows through the real engine and the real ruleset.

Nothing here is mocked. The observations are the ones that would be written to
``observations.jsonl``, the ruleset is the signed artefact in ``rulesets/``, and
the scoring path is ``manobal_risk.score_with_trace``. If the generator's output
does not load into the engine, this suite fails at import of the first history
rather than at some later adapter.

The tier assertions are stated as *distributions*, never per subject. A single
subject's tier depends on their draw; the claim the corpus has to support is
that the population the ground truth marks as declining lands materially higher
than the population it marks as well.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pytest

from manobal_risk import AcuteTriggerKind, Domain, Ruleset, SubjectHistory, score
from manobal_synth import GenerationConfig, build_dataset
from manobal_synth.config import ConsentProfile, MissingnessProfile

from .conftest import ScoredSubject, by_group
from .helpers import history_for, tier_share_at_or_above


def _wsi(subjects: Sequence[ScoredSubject]) -> float:
    return float(np.mean([subject.trace.wsi for subject in subjects]))


def test_observations_load_into_the_engine_unmodified(
    scored_cohort: Sequence[ScoredSubject],
) -> None:
    subject = scored_cohort[0]
    row = subject.records.observations[0]
    assert set(row.as_dict()) == {"subject_token", "indicator_code", "observed_on", "value"}
    assert isinstance(subject.trace.wsi, float)


def test_declining_subjects_reach_a_higher_tier_distribution_than_stable(
    scored_cohort: Sequence[ScoredSubject],
) -> None:
    declining = by_group(scored_cohort, "distress_active")
    stable = by_group(scored_cohort, "stable")
    declining_share = tier_share_at_or_above([s.tier for s in declining], "T1")
    stable_share = tier_share_at_or_above([s.tier for s in stable], "T1")
    assert declining_share >= 0.30, f"only {declining_share:.0%} of declining subjects reached T1"
    assert stable_share <= 0.06, f"{stable_share:.0%} of stable subjects reached T1"
    assert declining_share >= 5.0 * max(stable_share, 0.01)


def test_declining_subjects_carry_a_higher_composite(
    scored_cohort: Sequence[ScoredSubject],
) -> None:
    declining = by_group(scored_cohort, "distress_active")
    stable = by_group(scored_cohort, "stable")
    assert _wsi(declining) >= 2.0 * _wsi(stable)


def test_plateaued_declines_are_recorded_as_such_rather_than_scoring(
    scored_cohort: Sequence[ScoredSubject],
) -> None:
    """The K4 false-negative population, and why it is not a generator bug.

    A decline that saturated long before the window closed has moved the
    subject's own trailing median with it, so a baseline-of-one method cannot see
    it. Ground truth marks these subjects, and the corpus keeps them so that a
    recall figure can be reported honestly against the population that was
    actually detectable.
    """
    plateaued = by_group(scored_cohort, "distress_plateaued")
    assert plateaued, "the corpus contains no plateaued declines to measure against"
    assert tier_share_at_or_above([s.tier for s in plateaued], "T1") < 0.15
    assert all(s.records.ground_truth.distressed for s in plateaued)


def test_gaming_subjects_are_still_caught_by_objective_domains(
    scored_cohort: Sequence[ScoredSubject],
) -> None:
    """The corroboration argument, which is the reason the gate exists.

    A gaming subject suppresses D5 and D7 — the channels they control — while
    D1, D2 and D4 keep deteriorating. If suppressing self-report were enough to
    disappear, multi-domain corroboration would be buying nothing.
    """
    gaming = by_group(scored_cohort, "gaming_active")
    assert len(gaming) >= 3

    self_report = float(np.mean([s.domain_score("D5_self_report") for s in gaming]))
    objective = float(
        np.mean(
            [
                max(
                    s.domain_score("D1_workload"),
                    s.domain_score("D2_leave"),
                    s.domain_score("D4_physiological"),
                )
                for s in gaming
            ]
        )
    )
    assert self_report < 0.25, f"gaming cohort did not actually suppress D5 ({self_report:.3f})"
    assert objective >= 2.0 * self_report

    stable = by_group(scored_cohort, "stable")
    assert tier_share_at_or_above([s.tier for s in gaming], "T1") > tier_share_at_or_above(
        [s.tier for s in stable], "T1"
    )


def test_gaming_and_honest_declines_are_comparable_on_objective_domains(
    scored_cohort: Sequence[ScoredSubject],
) -> None:
    """Suppression must not weaken the objective evidence, only the self-report.

    Otherwise the gaming cohort would be an easier population rather than a
    differently-presenting one, and the corroboration claim would be untested.
    """
    gaming = by_group(scored_cohort, "gaming_active")
    honest = by_group(scored_cohort, "distress_active")
    gaming_d1 = float(np.mean([s.domain_score("D1_workload") for s in gaming]))
    honest_d1 = float(np.mean([s.domain_score("D1_workload") for s in honest]))
    assert gaming_d1 >= 0.6 * honest_d1


def test_acute_events_are_emitted_with_a_kind_and_a_timestamp(
    scored_cohort: Sequence[ScoredSubject],
) -> None:
    triggers = [row for s in scored_cohort for row in s.records.acute_triggers]
    assert triggers, "no acute triggers generated"
    # Compared against the enum's values rather than a hand-written list of
    # names. A generator that invented a trigger kind the engine does not
    # recognise would produce acute events nothing downstream can route.
    kinds = {row.kind for row in triggers}
    assert kinds <= {kind.value for kind in AcuteTriggerKind}
    assert all(row.occurred_at.tzinfo is not None for row in triggers)


def test_objective_domains_score_for_subjects_who_never_enrolled(
    ruleset: Ruleset,
) -> None:
    """D1/D2/D3 come from records the force already holds, so they need no opt-in.

    A corpus in which unenrolled personnel produced nothing at all would make the
    coverage-renormalisation path in SDD §4.5 untestable for the majority of the
    force, which under a 42% enrolment rate is most of it.
    """
    config = GenerationConfig(
        seed=31,
        personnel=60,
        duration_days=200,
        enrolment_rate=0.3,
        distress_cohort=0.4,
        consent_profile=ConsentProfile.REALISTIC,
        missingness=MissingnessProfile.REALISTIC,
    )
    unenrolled = [
        records
        for records in build_dataset(config).iter_subjects()
        if not records.ground_truth.enrolled
    ]
    assert unenrolled, "every subject enrolled; cannot test the objective-only path"

    for records in unenrolled[:10]:
        domains = set(records.ground_truth.consented_domains)
        assert domains == {"D1_workload", "D2_leave", "D3_organisational"}
        assert records.observations

    history = history_for(unenrolled[0], config.end_date)
    assessment = score(history, ruleset)
    assert assessment.subject_token == unenrolled[0].ground_truth.subject_token


@pytest.mark.parametrize("domain", ["D4_physiological", "D5_self_report", "D6_vocal_acoustic"])
def test_opt_in_domains_are_absent_without_consent(
    scored_cohort: Sequence[ScoredSubject],
    domain: str,
) -> None:
    from manobal_synth.indicators import INDICATORS

    codes = {code for code, spec in INDICATORS.items() if str(spec.domain) == domain}
    for subject in scored_cohort:
        if domain in subject.records.ground_truth.consented_domains:
            continue
        emitted = {row.indicator_code for row in subject.records.observations}
        assert not (emitted & codes)


def test_history_uses_the_engine_consent_type(scored_cohort: Sequence[ScoredSubject]) -> None:
    history = history_for(
        scored_cohort[0].records, scored_cohort[0].records.observations[-1].observed_on
    )
    assert isinstance(history, SubjectHistory)
    assert all(isinstance(domain, Domain) for domain in history.consented_domains)
