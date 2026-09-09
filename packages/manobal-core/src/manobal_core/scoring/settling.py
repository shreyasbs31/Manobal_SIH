"""Suppress tier rises caused by withdrawal rather than by distress.

ADR 0002 Option B. The engine computes a coverage-renormalised weighted mean
exactly as SDD §4.5 specifies, and that formula has an arithmetic property
nobody chose: removing a domain that was scoring *below* the mean raises the
mean of what is left. A person carrying real strain in two domains, whose two
calm domains were holding their composite under the T2 boundary, withdraws
consent for the calm two and lands at T3 — an immediate push to their welfare
officer, on the strength of nothing they did.

FR-3.3 promises that "opting out of a data type neither raises nor lowers a
person's tier". §7.7 promises withdrawal "without friction — one screen, no
justification, no notification to anyone, immediate effect". Neither is true
while a withdrawal can report you, and withdrawal that is a gamble is not
frictionless however few screens it takes.

**Why this lives here and not in the engine.** The engine is stateless and
scores one person at one moment from their history. It cannot see a consent
event, and giving it that visibility would make the scoring function depend on
governance state — untestable in isolation, and no longer replayable, which
§10.5 requires. The policy belongs in the orchestrator that has both the current
assessment and the previous one.

**Two carve-outs, and they are the load-bearing part.** This module's whole job
is to suppress a tier rise, so the question that matters is when it must not.
An acute signal is never suppressed: a policy that protects somebody's privacy
right up until it hides their crisis has traded one harm for a worse one. And a
rise that comes with a *newly breaching* category is never suppressed either,
because then the withdrawal is not the explanation — the person is genuinely
worse, and the coincidence of timing must not buy them invisibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Final

from manobal_risk.types import Tier

DEFAULT_SETTLING_PERIOD: Final = timedelta(days=14)
"""How long after a withdrawal the policy applies.

Long enough for the trailing baseline to re-establish over the narrower set of
domains, so that when protection lapses the composite reflects the person rather
than the transition. Short enough that it is a settling period and not a
permanent exemption, which would be a way to hide by withdrawing.
"""


class SettlingReason(StrEnum):
    """Why the policy did or did not intervene.

    Recorded on every assessment. §10.5 requires an auditor to be able to ask,
    months later, why a particular person was or was not shown to an officer,
    and "the policy decided" is not an answer.
    """

    COVERAGE_ONLY_INCREASE = "clamped: rise attributable only to reduced coverage"
    ACUTE_NEVER_SUPPRESSED = "not clamped: acute signals are never suppressed"
    NEW_ADVERSITY = "not clamped: a new category is breaching"
    NO_TIER_INCREASE = "not clamped: the tier did not rise"
    COVERAGE_NOT_REDUCED = "not clamped: coverage did not shrink"
    OUTSIDE_SETTLING_PERIOD = "not clamped: no recent withdrawal"
    NO_WITHDRAWAL = "not clamped: this person has never withdrawn consent"
    NO_PRIOR_ASSESSMENT = "not clamped: no previous assessment to compare against"


@dataclass(frozen=True, slots=True)
class ScoringOutcome:
    """The parts of an assessment this policy needs.

    Deliberately not the engine's ``RiskAssessment``: the policy needs only the
    tier, which categories were breaching and which were in scope. Passing the
    whole assessment would invite somebody to reach for the composite, which
    FR-3.7 does not let leave the engine in the first place.
    """

    tier: Tier
    breaching_categories: frozenset[str]
    covered_categories: frozenset[str]
    acute_override: bool = False


@dataclass(frozen=True, slots=True)
class SettlingDecision:
    """The tier to act on, and a full account of how it was arrived at."""

    tier: Tier
    engine_tier: Tier
    clamped: bool
    reason: SettlingReason
    withdrawn_categories: frozenset[str] = frozenset()


def apply_withdrawal_settling(
    *,
    current: ScoringOutcome,
    previous: ScoringOutcome | None,
    last_withdrawal_at: datetime | None,
    now: datetime,
    settling_period: timedelta = DEFAULT_SETTLING_PERIOD,
) -> SettlingDecision:
    """Decide the tier to act on, suppressing withdrawal-induced rises.

    The checks are ordered so that the safety carve-outs come first. Whatever
    else is true, an acute signal reaches an officer.
    """
    _reject_unusable_timestamp(last_withdrawal_at, now)

    def decide(
        tier: Tier,
        reason: SettlingReason,
        *,
        clamped: bool = False,
        lost: frozenset[str] = frozenset(),
    ) -> SettlingDecision:
        return SettlingDecision(
            tier=tier,
            engine_tier=current.tier,
            clamped=clamped,
            reason=reason,
            withdrawn_categories=lost,
        )

    # Safety first, and unconditionally. Nothing below this line can hide a
    # person in crisis, whatever their consent history looks like.
    if current.acute_override or current.tier is Tier.T4:
        return decide(current.tier, SettlingReason.ACUTE_NEVER_SUPPRESSED)

    if last_withdrawal_at is None:
        return decide(current.tier, SettlingReason.NO_WITHDRAWAL)

    if now - last_withdrawal_at > settling_period:
        return decide(current.tier, SettlingReason.OUTSIDE_SETTLING_PERIOD)

    if previous is None:
        return decide(current.tier, SettlingReason.NO_PRIOR_ASSESSMENT)

    if current.tier <= previous.tier:
        # The policy only ever suppresses rises. Clamping upward would turn it
        # into a floor that keeps somebody visible after they have recovered.
        return decide(current.tier, SettlingReason.NO_TIER_INCREASE)

    lost = previous.covered_categories - current.covered_categories
    if not lost:
        # Coverage is the same or wider, so dilution cannot be the explanation
        # for the rise; something about the person changed.
        return decide(current.tier, SettlingReason.COVERAGE_NOT_REDUCED)

    if not current.breaching_categories <= previous.breaching_categories:
        # A category is breaching now that was not before. The person is
        # genuinely worse, and the timing of their withdrawal must not buy them
        # invisibility.
        return decide(current.tier, SettlingReason.NEW_ADVERSITY, lost=lost)

    return decide(
        previous.tier,
        SettlingReason.COVERAGE_ONLY_INCREASE,
        clamped=True,
        lost=lost,
    )


def _reject_unusable_timestamp(moment: datetime | None, now: datetime) -> None:
    """Refuse a withdrawal timestamp that cannot be reasoned about.

    A naive timestamp compares wrongly against an aware ``now``; a future one
    would extend somebody's protection indefinitely. Both are bugs upstream, and
    both are quiet enough that failing loudly here is the only way anyone finds
    out.
    """
    if moment is None:
        return
    if moment.tzinfo is None:
        raise ValueError(
            f"The withdrawal timestamp {moment!r} carries no timezone; every "
            f"timestamp in this system is timezone-aware."
        )
    if moment > now:
        raise ValueError(
            f"The withdrawal timestamp {moment.isoformat()} is in the future "
            f"relative to {now.isoformat()}; refusing to settle against it."
        )
