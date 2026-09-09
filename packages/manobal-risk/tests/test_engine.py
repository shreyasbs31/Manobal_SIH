"""End-to-end scoring — SDD §4.5, FR-3.3/3.4/3.5/3.7/3.9.

These are the tests that describe what the system actually does to a person.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from manobal_risk import score, score_with_trace
from manobal_risk.engine import ACUTE_CATEGORY
from manobal_risk.ruleset import Ruleset
from manobal_risk.types import (
    DOMAIN_CATEGORY,
    AcuteTrigger,
    AcuteTriggerKind,
    Domain,
    Observation,
    Tier,
)

from .builders import DEFAULT_AS_OF, build_history

ASSESSED_AT = datetime(2026, 6, 30, 2, 0, tzinfo=UTC)


def acute() -> AcuteTrigger:
    return AcuteTrigger(
        kind=AcuteTriggerKind.PHQ9_ITEM9,
        occurred_at=datetime(2026, 6, 30, 1, 0, tzinfo=UTC),
        source="instrument",
    )


class TestTierOutcomes:
    def test_a_subject_at_their_own_norm_is_stable(self, ruleset: Ruleset) -> None:
        history = build_history(ruleset, {Domain.SELF_REPORT: 0.0, Domain.WORKLOAD: 0.0})

        result = score(history, ruleset, assessed_at=ASSESSED_AT)

        assert result.tier is Tier.T0
        assert result.contributing_categories == ()
        assert result.is_actionable_by_officer is False

    def test_two_corroborating_domains_reach_elevated(self, ruleset: Ruleset) -> None:
        history = build_history(ruleset, {Domain.SELF_REPORT: 0.6, Domain.WORKLOAD: 0.6})

        result = score(history, ruleset, assessed_at=ASSESSED_AT)

        assert result.tier is Tier.T2
        assert result.corroborated is True
        assert set(result.contributing_categories) == {
            DOMAIN_CATEGORY[Domain.SELF_REPORT],
            DOMAIN_CATEGORY[Domain.WORKLOAD],
        }

    def test_strong_multi_domain_deviation_reaches_high(self, ruleset: Ruleset) -> None:
        history = build_history(
            ruleset,
            {Domain.SELF_REPORT: 0.85, Domain.WORKLOAD: 0.85, Domain.PHYSIOLOGICAL: 0.85},
        )

        result = score(history, ruleset, assessed_at=ASSESSED_AT)

        assert result.tier is Tier.T3
        assert result.corroborated is True

    def test_one_catastrophic_domain_alone_is_capped_at_watch(self, ruleset: Ruleset) -> None:
        """FR-3.4, and the single most consequential behaviour in the system.

        A person whose self-report score is as bad as the instrument allows, with
        nothing else corroborating, reaches T1 — which is visible to them and to
        nobody else. That suppresses some true positives on purpose.
        """
        history = build_history(ruleset, {Domain.SELF_REPORT: 1.0})

        result = score(history, ruleset, assessed_at=ASSESSED_AT)

        assert result.tier is Tier.T1
        assert result.corroborated is False
        assert result.is_actionable_by_officer is False

    def test_watch_tier_still_names_the_drifting_category_for_the_individual(
        self, ruleset: Ruleset
    ) -> None:
        history = build_history(ruleset, {Domain.PHYSIOLOGICAL: 1.0})

        result = score(history, ruleset, assessed_at=ASSESSED_AT)

        assert result.tier is Tier.T1
        assert result.contributing_categories == (DOMAIN_CATEGORY[Domain.PHYSIOLOGICAL],)

    def test_contributing_categories_are_ordered_by_severity(self, ruleset: Ruleset) -> None:
        history = build_history(
            ruleset,
            {Domain.SELF_REPORT: 0.6, Domain.WORKLOAD: 0.95, Domain.PHYSIOLOGICAL: 0.8},
        )

        result = score(history, ruleset, assessed_at=ASSESSED_AT)

        assert result.contributing_categories[0] == DOMAIN_CATEGORY[Domain.WORKLOAD]


class TestAcutePath:
    def test_a_trigger_forces_acute_from_a_stable_subject(self, ruleset: Ruleset) -> None:
        history = build_history(
            ruleset,
            {Domain.SELF_REPORT: 0.0, Domain.WORKLOAD: 0.0},
            acute_triggers=(acute(),),
        )

        result = score(history, ruleset, assessed_at=ASSESSED_AT)

        assert result.tier is Tier.T4
        assert result.acute_override is True

    def test_a_trigger_escalates_even_with_no_data_at_all(self, ruleset: Ruleset) -> None:
        """A person who has consented to nothing and contributed nothing still
        reaches the acute path the moment they answer PHQ-9 item 9 positively.
        The safety path cannot depend on coverage."""
        history = build_history(ruleset, {}, acute_triggers=(acute(),))

        result = score(history, ruleset, assessed_at=ASSESSED_AT)

        assert result.tier is Tier.T4
        assert result.insufficient_coverage is True

    def test_acute_cases_carry_a_safety_category_so_the_reason_is_never_blank(
        self, ruleset: Ruleset
    ) -> None:
        history = build_history(ruleset, {}, acute_triggers=(acute(),))

        result = score(history, ruleset, assessed_at=ASSESSED_AT)

        assert result.contributing_categories[0] == ACUTE_CATEGORY


class TestCoverage:
    def test_a_subject_with_no_visible_domain_is_insufficient_not_stable(
        self, ruleset: Ruleset
    ) -> None:
        history = build_history(ruleset, {})

        result = score(history, ruleset, assessed_at=ASSESSED_AT)

        assert result.insufficient_coverage is True
        assert result.tier is Tier.T0
        assert result.contributing_categories == ()

    def test_a_domain_below_the_coverage_floor_does_not_participate(
        self, ruleset: Ruleset
    ) -> None:
        history = build_history(
            ruleset,
            {Domain.SELF_REPORT: 0.9, Domain.PHYSIOLOGICAL: 0.9},
            indicator_fraction=0.3,
        )

        result = score(history, ruleset, assessed_at=ASSESSED_AT)

        assert result.insufficient_coverage is True
        assert dict(result.domain_coverage)[Domain.PHYSIOLOGICAL] is False

    def test_withdrawing_consent_removes_the_domain_entirely(self, ruleset: Ruleset) -> None:
        """FR-7.2: after withdrawal the subject must be scored as though the data
        had never been contributed, not as though it were zero."""
        levels = {Domain.SELF_REPORT: 0.9, Domain.PHYSIOLOGICAL: 0.9}
        consented = build_history(ruleset, levels)
        withdrawn = build_history(
            ruleset, levels, consented_domains=frozenset({Domain.SELF_REPORT})
        )

        _, consented_trace = score_with_trace(consented, ruleset, assessed_at=ASSESSED_AT)
        withdrawn_result, withdrawn_trace = score_with_trace(
            withdrawn, ruleset, assessed_at=ASSESSED_AT
        )

        assert Domain.PHYSIOLOGICAL in consented_trace.active_domains
        assert Domain.PHYSIOLOGICAL not in withdrawn_trace.active_domains
        assert dict(withdrawn_result.domain_coverage)[Domain.PHYSIOLOGICAL] is False

    def test_a_stale_feed_lowers_coverage_rather_than_reporting_normal(
        self, ruleset: Ruleset
    ) -> None:
        """FR-2.6. A wearable that stopped syncing three weeks ago must not be
        read as three weeks of healthy readings."""
        fresh = build_history(ruleset, {Domain.PHYSIOLOGICAL: 0.9, Domain.SELF_REPORT: 0.9})
        stale = build_history(
            ruleset,
            {Domain.PHYSIOLOGICAL: 0.9, Domain.SELF_REPORT: 0.9},
            as_of=DEFAULT_AS_OF - timedelta(days=40),
        )
        aged = stale.__class__(
            subject_token=stale.subject_token,
            as_of=DEFAULT_AS_OF,
            observations=stale.observations,
            consented_domains=stale.consented_domains,
        )

        _, fresh_trace = score_with_trace(fresh, ruleset, assessed_at=ASSESSED_AT)
        _, aged_trace = score_with_trace(aged, ruleset, assessed_at=ASSESSED_AT)

        assert Domain.PHYSIOLOGICAL in fresh_trace.active_domains
        assert aged_trace.active_domains == ()


class TestHysteresis:
    def test_a_recovering_subject_is_not_dropped_on_the_first_good_cycle(
        self, ruleset: Ruleset
    ) -> None:
        history = build_history(
            ruleset,
            {Domain.SELF_REPORT: 0.1, Domain.WORKLOAD: 0.1},
            previous_tier=Tier.T3,
            consecutive_lower_cycles=0,
        )

        result = score(history, ruleset, assessed_at=ASSESSED_AT)

        assert result.tier is Tier.T3

    def test_the_tier_falls_once_recovery_has_been_sustained(self, ruleset: Ruleset) -> None:
        history = build_history(
            ruleset,
            {Domain.SELF_REPORT: 0.1, Domain.WORKLOAD: 0.1},
            previous_tier=Tier.T3,
            consecutive_lower_cycles=2,
        )

        result = score(history, ruleset, assessed_at=ASSESSED_AT)

        assert result.tier is Tier.T0

    def test_deterioration_is_never_delayed(self, ruleset: Ruleset) -> None:
        history = build_history(
            ruleset,
            {Domain.SELF_REPORT: 0.9, Domain.WORKLOAD: 0.9},
            previous_tier=Tier.T0,
        )

        result = score(history, ruleset, assessed_at=ASSESSED_AT)

        assert result.tier is Tier.T3


class TestProvenanceAndReplay:
    def test_the_assessment_records_the_exact_ruleset_that_produced_it(
        self, ruleset: Ruleset
    ) -> None:
        """FR-3.6. Without the hash, a past decision cannot be reconstructed once
        the ruleset has moved on."""
        history = build_history(ruleset, {Domain.SELF_REPORT: 0.6, Domain.WORKLOAD: 0.6})

        result = score(history, ruleset, assessed_at=ASSESSED_AT)

        assert result.ruleset_version == ruleset.version
        assert result.ruleset_sha256 == ruleset.sha256
        assert len(result.ruleset_sha256) == 64

    def test_scoring_is_deterministic(self, ruleset: Ruleset) -> None:
        """FR-3.9 replayability rests entirely on this."""
        history = build_history(ruleset, {Domain.SELF_REPORT: 0.62, Domain.WORKLOAD: 0.58})

        first = score(history, ruleset, assessed_at=ASSESSED_AT)
        second = score(history, ruleset, assessed_at=ASSESSED_AT)

        assert first == second

    def test_observations_after_the_assessment_date_are_invisible(
        self, ruleset: Ruleset
    ) -> None:
        history = build_history(ruleset, {Domain.SELF_REPORT: 0.1, Domain.WORKLOAD: 0.1})
        future = history.__class__(
            subject_token=history.subject_token,
            as_of=history.as_of,
            observations=(
                *history.observations,
                Observation(
                    indicator_code="pss10_total",
                    observed_on=date(2027, 1, 1),
                    value=1_000_000.0,
                ),
            ),
            consented_domains=history.consented_domains,
        )

        assert score(history, ruleset, assessed_at=ASSESSED_AT) == score(
            future, ruleset, assessed_at=ASSESSED_AT
        )


class TestNoScoreEscapes:
    def test_the_assessment_type_declares_no_numeric_field(self) -> None:
        """FR-3.7 and SDD §5.2 modelling choice 2, enforced structurally.

        If someone adds ``wsi: float`` to RiskAssessment to make a dashboard
        easier, this fails. That is the point: the officer must be told which
        categories and what to do, never a number they can over-read as a
        probability of harm.
        """
        import dataclasses

        from manobal_risk.types import RiskAssessment

        numeric = [
            f.name
            for f in dataclasses.fields(RiskAssessment)
            if f.type in {"float", "int", "float | None", "int | None"}
        ]

        assert numeric == []

    def test_no_scorelike_token_appears_in_a_serialised_assessment(
        self, ruleset: Ruleset
    ) -> None:
        import dataclasses
        import json
        import re

        history = build_history(ruleset, {Domain.SELF_REPORT: 0.77, Domain.WORKLOAD: 0.83})
        result = score(history, ruleset, assessed_at=ASSESSED_AT)

        body = json.dumps(dataclasses.asdict(result), default=str)

        assert not re.search(r"\b(wsi|probability|percentile|confidence)\b", body, re.I)

    def test_the_trace_is_not_reachable_from_the_assessment(self, ruleset: Ruleset) -> None:
        history = build_history(ruleset, {Domain.SELF_REPORT: 0.6, Domain.WORKLOAD: 0.6})

        result, trace = score_with_trace(history, ruleset, assessed_at=ASSESSED_AT)

        assert not hasattr(result, "trace")
        assert not hasattr(result, "wsi")
        assert trace.wsi == pytest.approx(0.6)
