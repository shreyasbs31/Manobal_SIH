"""Core value types for the MANOBAL risk engine (SDD §4.5).

Every type here is frozen. The engine is a pure function of (history, ruleset);
it holds no mutable state, performs no I/O, and has no database driver, HTTP
client or identity credential in its dependency tree. That absence is the
mechanism behind SDD §3.2 rule 1 — the risk engine is not trusted to decline a
path to Zone 3, it is *unable* to take one.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from enum import IntEnum, StrEnum
from typing import Self


class Domain(StrEnum):
    """The seven signal domains of SDD §4.4/§4.5."""

    WORKLOAD = "D1_workload"
    LEAVE = "D2_leave"
    ORGANISATIONAL = "D3_organisational"
    PHYSIOLOGICAL = "D4_physiological"
    SELF_REPORT = "D5_self_report"
    VOCAL_ACOUSTIC = "D6_vocal_acoustic"
    ENGAGEMENT = "D7_engagement"


#: Officer-facing category names. The engine emits these, never the Dxx codes and
#: never a number (FR-3.7). An officer is told "sleep and recovery", not "D4=0.81".
DOMAIN_CATEGORY: dict[Domain, str] = {
    Domain.WORKLOAD: "workload_and_duty",
    Domain.LEAVE: "leave_and_time_off",
    Domain.ORGANISATIONAL: "work_pattern_changes",
    Domain.PHYSIOLOGICAL: "sleep_and_recovery",
    Domain.SELF_REPORT: "self_reported_wellbeing",
    Domain.VOCAL_ACOUSTIC: "voice_check_in",
    Domain.ENGAGEMENT: "app_engagement",
}


class Tier(IntEnum):
    """Welfare tiers (SDD §4.5).

    Ordered so that ``min(raw_tier, Tier.T1)`` for the corroboration gate and
    ``final_tier < previous_tier`` for hysteresis read exactly as the spec writes
    them.
    """

    T0 = 0  # Stable — within personal norm. Nobody is told.
    T1 = 1  # Watch — single-domain drift. Only the individual is told.
    T2 = 2  # Elevated — >= 2 domains corroborating. UWO daily digest.
    T3 = 3  # High — strong multi-domain deviation. UWO immediate push.
    T4 = 4  # Acute — safety-critical. Overrides everything.

    @property
    def label(self) -> str:
        return {
            Tier.T0: "stable",
            Tier.T1: "watch",
            Tier.T2: "elevated",
            Tier.T3: "high",
            Tier.T4: "acute",
        }[self]


class AcuteTriggerKind(StrEnum):
    """The four inputs to M8 acute escalation (SDD §4.7)."""

    PHQ9_ITEM9 = "phq9_item9_positive"
    CRISIS_LANGUAGE = "crisis_language_detected"
    EXPLICIT_SOS = "explicit_sos"
    CRITICAL_INCIDENT = "critical_incident_direct_involvement"


class Direction(IntEnum):
    """Which way an indicator has to move before it is adverse.

    Rising overtime is adverse; rising HRV is not. Encoded as ``d_i`` in SDD §4.5
    step 2.
    """

    RISING_IS_ADVERSE = 1
    FALLING_IS_ADVERSE = -1


@dataclass(frozen=True, slots=True)
class Observation:
    """One indicator value on one day for one subject."""

    indicator_code: str
    observed_on: date
    value: float


@dataclass(frozen=True, slots=True)
class AcuteTrigger:
    kind: AcuteTriggerKind
    occurred_at: datetime
    source: str


@dataclass(frozen=True, slots=True)
class Baseline:
    """A subject's own established norm for one indicator (SDD §4.5 step 1).

    ``mad`` is already scaled by 1.4826 so that it is a consistent estimator of
    the standard deviation for normally distributed data.
    """

    indicator_code: str
    window_end: date
    median: float
    mad: float
    n_observations: int
    sufficient: bool


@dataclass(frozen=True, slots=True)
class IndicatorDeviation:
    """A single indicator's squared-off deviation from its own baseline."""

    indicator_code: str
    domain: Domain
    deviation: float  # z-hat in [0, 1]
    observed_value: float
    baseline: Baseline


@dataclass(frozen=True, slots=True)
class DomainScore:
    """One domain's aggregate deviation, plus how much of it we could actually see."""

    domain: Domain
    score: float  # Z_{s,d} in [0, 1]
    coverage: float  # fraction of the domain's indicators that were usable
    contributing_indicators: tuple[str, ...]
    breached: bool  # score >= this domain's corroboration threshold
    #: Whether the domain met the ruleset's coverage floor and therefore
    #: participates in the composite (SDD §4.5 step 4). Decided by the ruleset at
    #: scoring time, not by a constant on this type.
    active: bool


@dataclass(frozen=True, slots=True)
class SubjectHistory:
    """Everything the engine is allowed to know about one subject.

    Note what is absent: no name, no service number, no rank, no unit, no contact
    detail. The engine cannot leak an identity it was never given.
    """

    subject_token: str
    as_of: date
    observations: tuple[Observation, ...]
    #: Domains the subject has an active consent for. A domain absent here is
    #: dropped before scoring, which is what makes coverage renormalisation the
    #: load-bearing control it is meant to be.
    consented_domains: frozenset[Domain]
    acute_triggers: tuple[AcuteTrigger, ...] = ()
    previous_tier: Tier = Tier.T0
    #: Consecutive completed cycles in which the raw tier sat below the current
    #: tier's lower boundary. Hysteresis needs two (SDD §4.5 step 5).
    consecutive_lower_cycles: int = 0

    def without_domain(self, domain: Domain, indicator_domains: Mapping[str, Domain]) -> Self:
        """Return a copy as though the subject had never contributed ``domain``.

        Used by the coverage-renormalisation property tests (SDD §9.1) and by the
        consent-withdrawal recompute path (FR-7.2), which must re-score a subject
        as if the withdrawn data type had never existed.
        """
        return type(self)(
            subject_token=self.subject_token,
            as_of=self.as_of,
            observations=tuple(
                o
                for o in self.observations
                if indicator_domains.get(o.indicator_code) is not domain
            ),
            consented_domains=self.consented_domains - {domain},
            acute_triggers=self.acute_triggers,
            previous_tier=self.previous_tier,
            consecutive_lower_cycles=self.consecutive_lower_cycles,
        )


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    """The engine's only output.

    **There is no numeric field on this type, and there must never be one.**
    SDD §5.2 modelling choice 2 and FR-3.7 are enforced here and in the database
    schema rather than by discipline in the serialiser: you cannot leak a number
    that was never stored. ``test_assessment_exposes_no_numeric_score`` fails the
    build if anyone adds one.
    """

    subject_token: str
    assessed_at: datetime
    tier: Tier
    #: Gated tier after corroboration and before hysteresis. Persisted as
    #: ``pre_gate_tier`` so the next cycle can count consecutive lower nights.
    #: A ``Tier`` is a name, not a score — the privacy gate allows it.
    tier_before_hysteresis: Tier
    #: Officer-facing category names, ordered by contribution. Names only.
    contributing_categories: tuple[str, ...]
    #: Machine-readable domain identifiers for internal routing (intervention
    #: lookup, aggregation). Still names, still not numbers.
    contributing_domains: tuple[Domain, ...]
    #: Which domains had adequate coverage. Booleans, not fractions — a coverage
    #: fraction is a number an officer could over-read.
    domain_coverage: tuple[tuple[Domain, bool], ...]
    ruleset_version: str
    ruleset_sha256: str
    corroborated: bool
    acute_override: bool
    insufficient_coverage: bool

    @property
    def is_actionable_by_officer(self) -> bool:
        """T0 tells nobody; T1 tells only the individual (SDD §4.5 tier semantics)."""
        return self.tier >= Tier.T2


@dataclass(frozen=True, slots=True)
class ScoringTrace:
    """The numbers, kept out of :class:`RiskAssessment` on purpose.

    Available only via :func:`manobal_risk.engine.score_with_trace`, which exists
    for three consumers and no others: the property test suite, the
    observation-mode backtest harness (SDD §12.2 R5), and quarterly threshold
    recalibration (SDD §10.5). It is never serialised to any API, never persisted,
    and never logged.
    """

    wsi: float
    domain_scores: tuple[DomainScore, ...]
    indicator_deviations: tuple[IndicatorDeviation, ...]
    raw_tier: Tier
    tier_before_hysteresis: Tier
    active_domains: tuple[Domain, ...]
    breaching_domains: tuple[Domain, ...]
