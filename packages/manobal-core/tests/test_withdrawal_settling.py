"""Withdrawing consent must not report you (ADR 0002 Option B, FR-3.3, §7.7).

The engine computes a coverage-renormalised weighted mean, and a mean has an
arithmetic consequence nobody chose: dropping a domain that was scoring *calm*
raises the average of what remains. ADR 0002 works the counterexample through —
a person sitting quietly at T1 withdraws wearable and self-report consent, and
lands at T3, an immediate push to their welfare officer. Nothing about them
changed. They turned off a device.

FR-3.3 says "opting out of a data type neither raises nor lowers a person's
tier" and §7.7 promises withdrawal "without friction — one screen, no
justification, no notification to anyone". Both are false while that holds, and
the first person it happens to will tell their unit that turning off the
wearable got them reported.

This policy is the fix, in the service layer, leaving the engine untouched. The
tests below fix its shape, and two of them matter more than the rest: the one
that says an acute signal is never suppressed, and the one that says genuine
new deterioration is never suppressed. A policy that protects privacy by hiding
somebody in crisis has traded one harm for a worse one.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from manobal_core.scoring.settling import (
    ScoringOutcome,
    SettlingReason,
    apply_withdrawal_settling,
)
from manobal_risk.types import Tier

NOW = datetime(2026, 3, 20, 2, 0, tzinfo=UTC)
SETTLING = timedelta(days=14)

WORKLOAD = "duty_load"
LEAVE = "leave_pattern"
SLEEP = "sleep_and_recovery"
MOOD = "self_reported_wellbeing"


def outcome(
    tier: Tier,
    *,
    breaching: set[str] | None = None,
    coverage: set[str] | None = None,
    acute: bool = False,
) -> ScoringOutcome:
    return ScoringOutcome(
        tier=tier,
        breaching_categories=frozenset(breaching or set()),
        covered_categories=frozenset(coverage or {WORKLOAD, LEAVE, SLEEP, MOOD}),
        acute_override=acute,
    )


#: The exact scenario from ADR 0002 §4: two adverse domains, two calm ones
#: diluting the mean below the T2 boundary.
BEFORE_WITHDRAWAL = outcome(
    Tier.T1,
    breaching={WORKLOAD, LEAVE},
    coverage={WORKLOAD, LEAVE, SLEEP, MOOD},
)

#: The same person after withdrawing wearable and self-report consent. The calm
#: domains are gone, the mean is now 0.9, and the engine says T3.
AFTER_WITHDRAWAL = outcome(
    Tier.T3,
    breaching={WORKLOAD, LEAVE},
    coverage={WORKLOAD, LEAVE},
)


def settle(
    current: ScoringOutcome,
    previous: ScoringOutcome | None = BEFORE_WITHDRAWAL,
    *,
    withdrawn_at: datetime | None = NOW - timedelta(days=1),
    now: datetime = NOW,
):
    return apply_withdrawal_settling(
        current=current,
        previous=previous,
        last_withdrawal_at=withdrawn_at,
        now=now,
        settling_period=SETTLING,
    )


class TestTheAdrScenario:
    def test_withdrawing_calm_domains_does_not_report_a_quiet_person(self) -> None:
        """ADR 0002 §4, end to end. This is the whole reason the module exists."""
        decision = settle(AFTER_WITHDRAWAL)
        assert decision.tier is Tier.T1
        assert decision.clamped
        assert decision.reason is SettlingReason.COVERAGE_ONLY_INCREASE

    def test_the_engine_result_is_preserved_for_the_audit_record(self) -> None:
        """The WDEC must be able to see that a clamp happened and what it hid.
        A suppression that leaves no trace is indistinguishable from a bug."""
        decision = settle(AFTER_WITHDRAWAL)
        assert decision.engine_tier is Tier.T3
        assert decision.tier is Tier.T1


class TestAcuteIsNeverSuppressed:
    """The carve-out that makes this policy safe to ship.

    Everything else here suppresses a tier rise. If that logic could swallow an
    acute signal, the policy would keep somebody's privacy intact right up until
    it killed them.
    """

    def test_an_acute_override_reaches_the_officer_during_settling(self) -> None:
        acute = outcome(
            Tier.T4, breaching={WORKLOAD, LEAVE}, coverage={WORKLOAD, LEAVE}, acute=True
        )
        decision = settle(acute)
        assert decision.tier is Tier.T4
        assert not decision.clamped
        assert decision.reason is SettlingReason.ACUTE_NEVER_SUPPRESSED

    def test_t4_is_never_clamped_even_without_the_override_flag(self) -> None:
        """Belt and braces: the tier alone is enough to disable the policy."""
        decision = settle(outcome(Tier.T4, breaching={WORKLOAD, LEAVE}, coverage={WORKLOAD, LEAVE}))
        assert decision.tier is Tier.T4
        assert not decision.clamped


class TestGenuineDeteriorationIsNeverSuppressed:
    def test_a_newly_breaching_category_defeats_the_clamp(self) -> None:
        """Coverage shrank *and* the person got worse. The second fact wins:
        the rise is no longer attributable solely to reduced coverage."""
        worse = outcome(
            Tier.T3,
            breaching={WORKLOAD, LEAVE, SLEEP},
            coverage={WORKLOAD, LEAVE, SLEEP},
        )
        decision = settle(worse)
        assert decision.tier is Tier.T3
        assert not decision.clamped
        assert decision.reason is SettlingReason.NEW_ADVERSITY

    def test_a_rise_with_unchanged_coverage_is_real_and_passes_through(self) -> None:
        """No domain was withdrawn, so dilution cannot be the explanation."""
        decision = settle(
            outcome(
                Tier.T3,
                breaching={WORKLOAD, LEAVE},
                coverage=BEFORE_WITHDRAWAL.covered_categories,
            )
        )
        assert decision.tier is Tier.T3
        assert not decision.clamped

    def test_deterioration_after_the_settling_period_passes_through(self) -> None:
        decision = settle(AFTER_WITHDRAWAL, withdrawn_at=NOW - timedelta(days=30))
        assert decision.tier is Tier.T3
        assert not decision.clamped
        assert decision.reason is SettlingReason.OUTSIDE_SETTLING_PERIOD


class TestTheClampOnlyEverSuppressesRises:
    def test_a_falling_tier_is_never_raised_back_up(self) -> None:
        """The policy suppresses increases. It must not become a floor that
        keeps somebody visible after they have recovered."""
        improved = outcome(Tier.T0, breaching=set(), coverage={WORKLOAD, LEAVE})
        decision = settle(improved)
        assert decision.tier is Tier.T0
        assert not decision.clamped

    def test_an_unchanged_tier_passes_through(self) -> None:
        same = outcome(Tier.T1, breaching={WORKLOAD, LEAVE}, coverage={WORKLOAD, LEAVE})
        assert settle(same).tier is Tier.T1

    def test_the_clamp_never_exceeds_the_engine_tier(self) -> None:
        """Clamping to the previous tier must not *raise* anyone either."""
        decision = settle(
            outcome(Tier.T2, breaching={WORKLOAD}, coverage={WORKLOAD}),
            previous=outcome(Tier.T3, breaching={WORKLOAD, LEAVE}),
        )
        assert decision.tier is Tier.T2


class TestWhenThePolicyDoesNotApply:
    def test_a_person_who_never_withdrew_is_untouched(self) -> None:
        decision = settle(AFTER_WITHDRAWAL, withdrawn_at=None)
        assert decision.tier is Tier.T3
        assert not decision.clamped
        assert decision.reason is SettlingReason.NO_WITHDRAWAL

    def test_a_first_ever_assessment_is_untouched(self) -> None:
        """With no previous outcome there is nothing to attribute a rise to."""
        decision = settle(AFTER_WITHDRAWAL, previous=None)
        assert decision.tier is Tier.T3
        assert not decision.clamped
        assert decision.reason is SettlingReason.NO_PRIOR_ASSESSMENT

    def test_coverage_that_grew_is_not_a_withdrawal_effect(self) -> None:
        """Somebody who *added* a data source and then rose did not get there
        by dilution, whatever else happened in the settling window."""
        broader = outcome(
            Tier.T3,
            breaching={WORKLOAD, LEAVE},
            coverage={WORKLOAD, LEAVE, SLEEP, MOOD, "app_engagement"},
        )
        decision = settle(broader)
        assert not decision.clamped


class TestBoundaries:
    def test_the_settling_period_is_inclusive_at_its_edge(self) -> None:
        decision = settle(AFTER_WITHDRAWAL, withdrawn_at=NOW - SETTLING)
        assert decision.clamped

    def test_a_withdrawal_one_moment_past_the_edge_no_longer_settles(self) -> None:
        decision = settle(AFTER_WITHDRAWAL, withdrawn_at=NOW - SETTLING - timedelta(seconds=1))
        assert not decision.clamped

    def test_a_withdrawal_timestamped_in_the_future_is_rejected(self) -> None:
        """Clock skew or a bad backfill should not extend anyone's protection
        indefinitely, nor silently disable it."""
        with pytest.raises(ValueError, match="future"):
            settle(AFTER_WITHDRAWAL, withdrawn_at=NOW + timedelta(hours=1))

    def test_a_naive_timestamp_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="timezone"):
            settle(AFTER_WITHDRAWAL, withdrawn_at=datetime(2026, 3, 19))  # noqa: DTZ001


class TestEveryDecisionIsExplainable:
    def test_every_outcome_carries_a_reason(self) -> None:
        """§10.5: an auditor asks months later why somebody was or was not
        shown. "The policy decided" is not an answer."""
        for current, previous, withdrawn in [
            (AFTER_WITHDRAWAL, BEFORE_WITHDRAWAL, NOW - timedelta(days=1)),
            (AFTER_WITHDRAWAL, BEFORE_WITHDRAWAL, None),
            (AFTER_WITHDRAWAL, None, NOW - timedelta(days=1)),
            (BEFORE_WITHDRAWAL, BEFORE_WITHDRAWAL, NOW - timedelta(days=1)),
        ]:
            decision = settle(current, previous, withdrawn_at=withdrawn)
            assert isinstance(decision.reason, SettlingReason)

    def test_a_clamp_names_the_categories_that_disappeared(self) -> None:
        """So the WDEC can see that the suppression was about coverage, and
        which coverage, without re-deriving it from two assessments."""
        decision = settle(AFTER_WITHDRAWAL)
        assert decision.withdrawn_categories == frozenset({SLEEP, MOOD})
