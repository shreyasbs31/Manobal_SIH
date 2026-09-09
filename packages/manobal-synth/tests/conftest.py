"""Shared fixtures.

Generating and scoring a cohort is the expensive part of this suite, so the
cohort fixtures are session-scoped and shared between the causal-correlation and
risk-engine suites. Both need the same corpus and neither mutates it — every
generated type in this package is frozen.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

from manobal_risk import Ruleset, ScoringTrace, load_ruleset, score_with_trace
from manobal_synth import GenerationConfig, build_dataset
from manobal_synth.config import ConsentProfile, MissingnessProfile
from manobal_synth.dataset import SubjectRecords

from .helpers import history_for

RULESET_PATH = Path(__file__).resolve().parents[3] / "rulesets" / "manobal-ruleset-1.0.0.yaml"

#: Cohort size for the statistical suites. Large enough that the correlation and
#: tier-share assertions are not dominated by sampling noise, small enough that
#: the whole suite stays under a minute.
COHORT_PERSONNEL = 220
COHORT_DURATION_DAYS = 540
COHORT_SEED = 20260908


@dataclass(frozen=True, slots=True)
class ScoredSubject:
    """A generated subject and what the real engine made of it."""

    records: SubjectRecords
    tier: str
    trace: ScoringTrace

    @property
    def group(self) -> str:
        """Ground-truth bucket.

        Actively-declining and plateaued subjects are separated because they are
        different populations: only the former is something a trailing-median
        baseline could detect, and mixing them makes every recall figure a
        statement about the onset distribution instead of about the engine.
        """
        truth = self.records.ground_truth
        if not truth.distressed:
            return "stable"
        prefix = "gaming" if truth.gaming else "distress"
        return f"{prefix}_{'active' if truth.deteriorating_at_end else 'plateaued'}"

    def domain_score(self, domain: str) -> float:
        for score in self.trace.domain_scores:
            if str(score.domain) == domain:
                return score.score
        return 0.0


@pytest.fixture(scope="session")
def ruleset() -> Ruleset:
    assert RULESET_PATH.is_file(), f"ruleset artefact missing at {RULESET_PATH}"
    # Signature verification is manobal-risk's concern and is covered there.
    return load_ruleset(RULESET_PATH, require_signature=False)


@pytest.fixture(scope="session")
def cohort_config() -> GenerationConfig:
    return GenerationConfig(
        seed=COHORT_SEED,
        personnel=COHORT_PERSONNEL,
        duration_days=COHORT_DURATION_DAYS,
        distress_cohort=0.30,
        # Well above the 2% the SDD example uses. Roughly half of any injected
        # cohort has plateaued by the end of the window, so a realistic gaming
        # fraction would leave single figures of actively-suppressing subjects
        # and the corroboration assertion would be measuring noise.
        gaming_cohort=0.10,
        acute_events=0.01,
        # Full consent and realistic missingness: the causal and tiering suites
        # are asking whether the signal exists, not whether consent removes it.
        # test_missingness_consent.py varies both of those on its own corpus.
        consent_profile=ConsentProfile.FULL,
        missingness=MissingnessProfile.REALISTIC,
    )


@pytest.fixture(scope="session")
def cohort(cohort_config: GenerationConfig) -> tuple[SubjectRecords, ...]:
    return tuple(build_dataset(cohort_config).iter_subjects())


@pytest.fixture(scope="session")
def scored_cohort(
    cohort: Sequence[SubjectRecords],
    cohort_config: GenerationConfig,
    ruleset: Ruleset,
) -> tuple[ScoredSubject, ...]:
    as_of = cohort_config.end_date
    scored = []
    for records in cohort:
        assessment, trace = score_with_trace(history_for(records, as_of), ruleset)
        scored.append(ScoredSubject(records=records, tier=assessment.tier.name, trace=trace))
    return tuple(scored)


def by_group(scored: Sequence[ScoredSubject], group: str) -> tuple[ScoredSubject, ...]:
    return tuple(subject for subject in scored if subject.group == group)
