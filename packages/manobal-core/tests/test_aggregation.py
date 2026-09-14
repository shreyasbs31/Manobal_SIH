"""k-anonymised unit rollups (SDD §4.6, §4.8).

A commander sees a band and a category name, or they see that the figure was
withheld. They never see a headcount below *k*, an exact elevated count, or a
subject token. These tests pin both the pure decision and the stored outcome.
"""

from __future__ import annotations

import pytest
from django.utils import timezone

from manobal_core.apps.governance.aggregation import (
    SUPPRESSED_BELOW_K,
    SUPPRESSED_CHURN,
    band_elevated,
    decide_rollup,
    ensure_aggregate,
    public_aggregate_payload,
)
from manobal_core.apps.governance.enums import Tier
from manobal_core.apps.governance.models import RiskAssessmentRecord, Subject, Unit, UnitAggregate

from .scoring_helpers import make_subjects

pytestmark = pytest.mark.django_db

SLEEP = "sleep_and_recovery"


class TestBandsAndDecision:
    def test_counts_round_to_the_published_bands(self) -> None:
        assert band_elevated(0) == "0"
        assert band_elevated(3) == "1-4"
        assert band_elevated(7) == "5-9"
        assert band_elevated(12) == "10-19"
        assert band_elevated(20) == "20+"

    def test_a_unit_below_k_is_suppressed(self) -> None:
        rollup = decide_rollup(
            headcount=4,
            elevated=2,
            dominant_category=SLEEP,
            previous_elevated_band="",
            churn=0.0,
            k_threshold=10,
            max_churn=0.5,
        )
        assert rollup.suppressed is True
        assert rollup.suppression_reason == SUPPRESSED_BELOW_K
        assert rollup.elevated_band == ""
        assert rollup.dominant_category == ""

    def test_high_churn_is_suppressed_even_when_the_unit_is_large(self) -> None:
        rollup = decide_rollup(
            headcount=40,
            elevated=6,
            dominant_category=SLEEP,
            previous_elevated_band="1-4",
            churn=0.6,
            k_threshold=10,
            max_churn=0.5,
        )
        assert rollup.suppressed is True
        assert rollup.suppression_reason == SUPPRESSED_CHURN

    def test_a_stable_large_unit_publishes_a_band_and_a_trend(self) -> None:
        rollup = decide_rollup(
            headcount=20,
            elevated=6,
            dominant_category=SLEEP,
            previous_elevated_band="1-4",
            churn=0.1,
            k_threshold=10,
            max_churn=0.5,
        )
        assert rollup.suppressed is False
        assert rollup.elevated_band == "5-9"
        assert rollup.dominant_category == SLEEP
        assert rollup.trend_direction == "up"


class TestEnsureAggregate:
    def test_a_small_unit_is_stored_as_suppressed(self, unit_tree: dict[str, Unit]) -> None:
        make_subjects(unit_tree["company"], 3, established=True)
        aggregate = ensure_aggregate(unit_tree["company"])
        assert aggregate.suppressed is True
        assert aggregate.suppression_reason == SUPPRESSED_BELOW_K
        payload = public_aggregate_payload(aggregate)
        assert payload == {
            "unit": unit_tree["company"].code,
            "period_start": aggregate.period_start.isoformat(),
            "period_end": aggregate.period_end.isoformat(),
            "suppressed": True,
        }
        assert "headcount" not in payload
        assert "elevated_band" not in payload

    def test_a_large_new_cohort_is_suppressed_for_churn(
        self, unit_tree: dict[str, Unit]
    ) -> None:
        # Twelve people all arriving this week: headcount clears *k*, but the
        # membership turned over completely, which is the differencing attack.
        make_subjects(unit_tree["company"], 12, established=False)
        aggregate = ensure_aggregate(unit_tree["company"])
        assert aggregate.suppressed is True
        assert aggregate.suppression_reason == SUPPRESSED_CHURN

    def test_a_stable_unit_publishes_bands_not_counts(
        self, unit_tree: dict[str, Unit]
    ) -> None:
        people = make_subjects(unit_tree["company"], 12, established=True)
        for subject in people[:3]:
            _assessment(subject, Tier.T2, [SLEEP])
        aggregate = ensure_aggregate(unit_tree["company"])
        assert aggregate.suppressed is False
        assert aggregate.elevated_band == "1-4"
        assert aggregate.dominant_category == SLEEP
        payload = public_aggregate_payload(aggregate)
        assert payload["elevated_band"] == "1-4"
        assert payload["dominant_category"] == SLEEP
        assert "headcount" not in payload
        assert "subject_token" not in payload
        assert "briefing" in payload
        assert "1-4" in str(payload["briefing"])
        assert "tok_" not in str(payload["briefing"])

    def test_a_second_call_returns_the_stored_row(self, unit_tree: dict[str, Unit]) -> None:
        make_subjects(unit_tree["company"], 3, established=True)
        first = ensure_aggregate(unit_tree["company"])
        second = ensure_aggregate(unit_tree["company"])
        assert first.pk == second.pk
        assert UnitAggregate.objects.filter(unit=unit_tree["company"]).count() == 1


def _assessment(subject: Subject, tier: Tier, categories: list[str]) -> RiskAssessmentRecord:
    return RiskAssessmentRecord.objects.create(
        subject_token=subject.subject_token,
        assessed_at=timezone.now(),
        tier=tier,
        contributing_categories=categories,
        ruleset_version="1.0.0-test",
        ruleset_digest="b" * 64,
        domains_present=categories,
        coverage=1.0,
        pre_gate_tier=tier,
    )
