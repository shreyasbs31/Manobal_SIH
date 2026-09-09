"""Rate limiting and anomaly detection on the resolve path (SDD §4.9, §7.2).

§7.2 states the intent plainly: "Exceeding `identity:resolve` is treated as a
security incident, not a usage problem. A welfare officer doing their job
resolves a handful of identities a week. An officer resolving thirty in an hour
is doing something else."

So this policy does two separable jobs, and conflating them would be a mistake:

*   it **refuses** work beyond the published limits, and
*   it **reports** patterns that are suspicious whether or not they were refused.

An out-of-unit resolution is the clearest case of the second without the first.
It is not forbidden — an officer covering another sub-unit during a transfer has
a legitimate reason — but it is exactly the shape a fishing expedition takes, so
it is always visible to the WDEC. Denying it would break real welfare work;
failing to report it would make the enclave's audit trail decorative.
"""

from __future__ import annotations

import pytest

from manobal_identity.grants.assertion import Operation
from manobal_identity.policy.resolution import (
    BREAK_GLASS_PER_DAY,
    RESOLVE_PER_DAY,
    RESOLVE_PER_HOUR,
    Anomaly,
    DenialReason,
    ResolutionCounts,
    evaluate_resolution,
)

OFFICER_UNIT = "12BN"
IN_SCOPE = "CENTRAL/WESTERN/12BN/ALPHA-COY"
OUT_OF_SCOPE = "CENTRAL/EASTERN/31BN/BRAVO-COY"


def counts(hour: int = 0, day: int = 0, break_glass: int = 0) -> ResolutionCounts:
    return ResolutionCounts(
        resolves_last_hour=hour, resolves_last_day=day, break_glass_last_day=break_glass
    )


def evaluate(
    *,
    operation: Operation = Operation.RESOLVE,
    tally: ResolutionCounts | None = None,
    subject_unit_path: str = IN_SCOPE,
):
    return evaluate_resolution(
        operation=operation,
        counts=tally or counts(),
        actor_unit_code=OFFICER_UNIT,
        subject_unit_path=subject_unit_path,
    )


class TestTheOrdinaryCase:
    def test_an_officer_resolving_within_their_unit_is_allowed_quietly(self) -> None:
        outcome = evaluate()
        assert outcome.allowed
        assert outcome.anomalies == ()
        assert not outcome.notify_wdec
        assert not outcome.flag_session

    def test_an_officer_may_resolve_right_up_to_the_hourly_limit(self) -> None:
        assert evaluate(tally=counts(hour=RESOLVE_PER_HOUR - 1)).allowed

    def test_a_deep_sub_unit_is_still_within_the_officers_scope(self) -> None:
        assert evaluate(subject_unit_path=IN_SCOPE).allowed

    def test_the_officers_own_unit_is_within_its_own_scope(self) -> None:
        assert evaluate(subject_unit_path="CENTRAL/WESTERN/12BN").allowed


class TestHourlyLimit:
    def test_the_sixth_resolution_in_an_hour_is_refused(self) -> None:
        outcome = evaluate(tally=counts(hour=RESOLVE_PER_HOUR))
        assert not outcome.allowed
        assert outcome.denial is DenialReason.HOURLY_LIMIT

    def test_breaching_the_limit_is_treated_as_a_security_incident(self) -> None:
        """§7.2: 429 + immediate WDEC alert + session flagged. All three."""
        outcome = evaluate(tally=counts(hour=RESOLVE_PER_HOUR))
        assert Anomaly.RATE_LIMIT_BREACHED in outcome.anomalies
        assert outcome.notify_wdec
        assert outcome.flag_session

    def test_a_bulk_deanonymisation_attempt_is_refused(self) -> None:
        """The thirty-in-an-hour officer from §7.2."""
        outcome = evaluate(tally=counts(hour=30, day=30))
        assert not outcome.allowed
        assert outcome.flag_session


class TestDailyLimit:
    def test_the_twenty_first_resolution_in_a_day_is_refused(self) -> None:
        outcome = evaluate(tally=counts(hour=0, day=RESOLVE_PER_DAY))
        assert not outcome.allowed
        assert outcome.denial is DenialReason.DAILY_LIMIT

    def test_the_daily_limit_binds_even_when_the_hour_is_quiet(self) -> None:
        """Twenty resolutions paced one an hour is still twenty resolutions."""
        assert not evaluate(tally=counts(hour=1, day=RESOLVE_PER_DAY)).allowed

    def test_breaching_the_daily_limit_also_alerts_the_wdec(self) -> None:
        outcome = evaluate(tally=counts(day=RESOLVE_PER_DAY))
        assert outcome.notify_wdec
        assert outcome.flag_session


class TestOutOfUnitResolution:
    """§4.9: "any resolve outside the officer's unit triggers an immediate
    WDEC alert" — an alert, note, not a refusal."""

    def test_resolving_outside_the_officers_unit_is_permitted(self) -> None:
        assert evaluate(subject_unit_path=OUT_OF_SCOPE).allowed

    def test_resolving_outside_the_officers_unit_alerts_the_wdec(self) -> None:
        outcome = evaluate(subject_unit_path=OUT_OF_SCOPE)
        assert Anomaly.OUT_OF_UNIT in outcome.anomalies
        assert outcome.notify_wdec

    def test_an_out_of_unit_resolution_does_not_flag_the_session(self) -> None:
        """Flagging a session interrupts an officer's work. Reserve it for
        limit breaches, which are quantitative, not for a single cross-unit
        lookup that has an innocent explanation more often than not."""
        assert not evaluate(subject_unit_path=OUT_OF_SCOPE).flag_session

    def test_a_unit_code_that_merely_prefixes_another_is_not_a_match(self) -> None:
        """"12BN" must not be read as matching "12BN-DET". Substring matching
        on a path is how scope checks quietly become wrong."""
        outcome = evaluate(subject_unit_path="CENTRAL/WESTERN/12BN-DET/ALPHA")
        assert Anomaly.OUT_OF_UNIT in outcome.anomalies

    def test_an_unknown_subject_unit_is_treated_as_out_of_scope(self) -> None:
        """Fail closed: an empty path is not evidence of being in scope."""
        assert Anomaly.OUT_OF_UNIT in evaluate(subject_unit_path="").anomalies


class TestBreakGlass:
    def test_break_glass_always_alerts_the_wdec(self) -> None:
        """§4.9: break-glass "notifies the WDEC within 60 seconds" — every time,
        not only when it is excessive."""
        outcome = evaluate(operation=Operation.BREAK_GLASS)
        assert outcome.allowed
        assert Anomaly.BREAK_GLASS_USED in outcome.anomalies
        assert outcome.notify_wdec

    def test_break_glass_is_limited_to_two_a_day(self) -> None:
        outcome = evaluate(
            operation=Operation.BREAK_GLASS,
            tally=counts(break_glass=BREAK_GLASS_PER_DAY),
        )
        assert not outcome.allowed
        assert outcome.denial is DenialReason.BREAK_GLASS_LIMIT

    def test_break_glass_is_not_blocked_by_the_routine_resolve_limit(self) -> None:
        """This is the whole point of break-glass. An officer who has spent
        their hourly resolves and then encounters a T4 acute case must still be
        able to reach the person. The emergency path has its own, tighter
        limit and its own alarm; it does not inherit the routine one."""
        outcome = evaluate(
            operation=Operation.BREAK_GLASS, tally=counts(hour=30, day=30)
        )
        assert outcome.allowed

    def test_routine_resolves_are_not_blocked_by_break_glass_usage(self) -> None:
        outcome = evaluate(tally=counts(break_glass=BREAK_GLASS_PER_DAY))
        assert outcome.allowed

    def test_exceeding_break_glass_flags_the_session(self) -> None:
        outcome = evaluate(
            operation=Operation.BREAK_GLASS,
            tally=counts(break_glass=BREAK_GLASS_PER_DAY),
        )
        assert outcome.flag_session


class TestOutcomesAreAuditable:
    def test_a_denial_always_carries_a_reason(self) -> None:
        outcome = evaluate(tally=counts(hour=RESOLVE_PER_HOUR))
        assert outcome.denial is not None
        assert outcome.denial.value.startswith("MB-")

    def test_an_allowed_outcome_carries_no_denial_reason(self) -> None:
        assert evaluate().denial is None

    def test_a_refusal_is_still_reported_rather_than_silently_dropped(self) -> None:
        """A blocked bulk-deanonymisation attempt is the single most
        interesting event this service can produce. It must not be quieter
        than a successful resolution."""
        outcome = evaluate(tally=counts(hour=RESOLVE_PER_HOUR))
        assert outcome.notify_wdec

    def test_several_concerns_are_reported_together(self) -> None:
        """An officer over the limit *and* reaching outside their unit is a
        worse signal than either alone; the WDEC should see both."""
        outcome = evaluate(
            tally=counts(hour=RESOLVE_PER_HOUR), subject_unit_path=OUT_OF_SCOPE
        )
        assert {Anomaly.RATE_LIMIT_BREACHED, Anomaly.OUT_OF_UNIT} <= set(
            outcome.anomalies
        )


class TestPublishedLimitsMatchTheSpecification:
    @pytest.mark.parametrize(
        ("constant", "expected"),
        [(RESOLVE_PER_HOUR, 5), (RESOLVE_PER_DAY, 20), (BREAK_GLASS_PER_DAY, 2)],
    )
    def test_the_limits_are_the_ones_the_sdd_publishes(
        self, constant: int, expected: int
    ) -> None:
        """§7.2 publishes these numbers to officers. Drift between the document
        and the code is a governance failure, not a tuning decision."""
        assert constant == expected
