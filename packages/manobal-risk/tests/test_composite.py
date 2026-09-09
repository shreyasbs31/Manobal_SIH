"""Domain aggregation and the composite WSI — SDD §4.5 steps 3-4, FR-3.3.

    WSI = sum_{d in A} w_d * Z_d / sum_{d in A} w_d      A = {d : coverage_d >= 0.6}

Coverage renormalisation is the control that makes voluntary participation
survivable: a person who declines wearables must not be scored differently *for
declining*. The tests below pin down exactly what that guarantee is and — just
as importantly — what it is not. See docs/adr/0002 for why the literal invariant
written in SDD §9.1 cannot hold for a weighted mean.
"""

from __future__ import annotations

import pytest

from manobal_risk.composite import compute_domain_score, compute_wsi
from manobal_risk.errors import ManobalRiskError
from manobal_risk.ruleset import DomainSpec
from manobal_risk.types import Domain, DomainScore, IndicatorDeviation

from .helpers import make_baseline

WEIGHTS = {
    Domain.SELF_REPORT: DomainSpec(Domain.SELF_REPORT, weight=0.22, corroboration_threshold=0.50),
    Domain.WORKLOAD: DomainSpec(Domain.WORKLOAD, weight=0.18, corroboration_threshold=0.55),
    Domain.PHYSIOLOGICAL: DomainSpec(
        Domain.PHYSIOLOGICAL, weight=0.18, corroboration_threshold=0.55
    ),
}


def deviation(code: str, domain: Domain, value: float) -> IndicatorDeviation:
    return IndicatorDeviation(
        indicator_code=code,
        domain=domain,
        deviation=value,
        observed_value=0.0,
        baseline=make_baseline(code),
    )


def scored(
    domain: Domain, score: float, *, coverage: float = 1.0, active: bool = True
) -> DomainScore:
    spec = WEIGHTS.get(domain) or DomainSpec(domain, weight=0.1, corroboration_threshold=0.55)
    return DomainScore(
        domain=domain,
        score=score,
        coverage=coverage,
        contributing_indicators=("x",),
        breached=score >= spec.corroboration_threshold,
        active=active,
    )


class TestComputeDomainScore:
    def test_is_the_weighted_mean_of_its_indicators(self) -> None:
        devs = [
            deviation("a", Domain.WORKLOAD, 0.2),
            deviation("b", Domain.WORKLOAD, 0.8),
        ]

        result = compute_domain_score(
            WEIGHTS[Domain.WORKLOAD],
            devs,
            indicator_weights={"a": 1.0, "b": 3.0},
            expected_indicator_count=2,
            coverage_floor=0.6,
        )

        assert result.score == pytest.approx((0.2 * 1 + 0.8 * 3) / 4)

    def test_coverage_is_usable_indicators_over_expected_indicators(self) -> None:
        result = compute_domain_score(
            WEIGHTS[Domain.WORKLOAD],
            [deviation("a", Domain.WORKLOAD, 0.5), deviation("b", Domain.WORKLOAD, 0.5)],
            indicator_weights={"a": 1.0, "b": 1.0},
            expected_indicator_count=5,
            coverage_floor=0.6,
        )

        assert result.coverage == pytest.approx(0.4)
        assert result.active is False

    def test_a_domain_at_the_coverage_floor_is_active(self) -> None:
        result = compute_domain_score(
            WEIGHTS[Domain.WORKLOAD],
            [deviation(c, Domain.WORKLOAD, 0.5) for c in "abc"],
            indicator_weights=dict.fromkeys("abc", 1.0),
            expected_indicator_count=5,
            coverage_floor=0.6,
        )

        assert result.coverage == pytest.approx(0.6)
        assert result.active is True

    def test_a_domain_with_no_usable_indicators_scores_zero_and_is_inactive(self) -> None:
        result = compute_domain_score(
            WEIGHTS[Domain.WORKLOAD],
            [],
            indicator_weights={},
            expected_indicator_count=5,
            coverage_floor=0.6,
        )

        assert result.score == pytest.approx(0.0)
        assert result.coverage == pytest.approx(0.0)
        assert result.active is False

    def test_breach_is_evaluated_against_the_domains_own_threshold(self) -> None:
        below = compute_domain_score(
            WEIGHTS[Domain.WORKLOAD],
            [deviation("a", Domain.WORKLOAD, 0.54)],
            indicator_weights={"a": 1.0},
            expected_indicator_count=1,
            coverage_floor=0.6,
        )
        at = compute_domain_score(
            WEIGHTS[Domain.WORKLOAD],
            [deviation("a", Domain.WORKLOAD, 0.55)],
            indicator_weights={"a": 1.0},
            expected_indicator_count=1,
            coverage_floor=0.6,
        )

        assert below.breached is False
        assert at.breached is True

    def test_an_inactive_domain_never_counts_as_breaching(self) -> None:
        """A domain we could barely see must not be allowed to supply one of the
        two corroborating signals — that would defeat the gate with thin data."""
        result = compute_domain_score(
            WEIGHTS[Domain.WORKLOAD],
            [deviation("a", Domain.WORKLOAD, 1.0)],
            indicator_weights={"a": 1.0},
            expected_indicator_count=10,
            coverage_floor=0.6,
        )

        assert result.active is False
        assert result.breached is False


class TestComputeWsi:
    def test_renormalises_over_active_domains_only(self) -> None:
        scores = [
            scored(Domain.SELF_REPORT, 0.8),
            scored(Domain.WORKLOAD, 0.4),
            scored(Domain.PHYSIOLOGICAL, 0.0, coverage=0.2, active=False),
        ]

        wsi = compute_wsi(scores, WEIGHTS)

        assert wsi == pytest.approx((0.22 * 0.8 + 0.18 * 0.4) / (0.22 + 0.18))

    def test_declining_a_domain_does_not_dilute_the_score(self) -> None:
        """The core FR-3.3 guarantee. Without renormalisation the denominator
        would stay at 1.0 and opting out would mechanically lower the WSI, making
        opt-out an effective way to hide."""
        with_wearable = compute_wsi(
            [
                scored(Domain.SELF_REPORT, 0.8),
                scored(Domain.WORKLOAD, 0.8),
                scored(Domain.PHYSIOLOGICAL, 0.8),
            ],
            WEIGHTS,
        )
        without_wearable = compute_wsi(
            [
                scored(Domain.SELF_REPORT, 0.8),
                scored(Domain.WORKLOAD, 0.8),
                scored(Domain.PHYSIOLOGICAL, 0.0, coverage=0.0, active=False),
            ],
            WEIGHTS,
        )

        assert with_wearable == pytest.approx(0.8)
        assert without_wearable == pytest.approx(0.8)

    def test_two_subjects_with_equal_adversity_score_equally_regardless_of_coverage(self) -> None:
        """The anti-penalty property stated precisely: what is invariant is the
        comparison between subjects, not the effect of deleting one person's data."""
        broad = compute_wsi(
            [
                scored(Domain.SELF_REPORT, 0.6),
                scored(Domain.WORKLOAD, 0.6),
                scored(Domain.PHYSIOLOGICAL, 0.6),
            ],
            WEIGHTS,
        )
        narrow = compute_wsi([scored(Domain.WORKLOAD, 0.6)], WEIGHTS)

        assert broad == pytest.approx(narrow)

    def test_is_bounded_by_the_active_domain_scores(self) -> None:
        scores = [
            scored(Domain.SELF_REPORT, 0.9),
            scored(Domain.WORKLOAD, 0.1),
            scored(Domain.PHYSIOLOGICAL, 0.5),
        ]

        wsi = compute_wsi(scores, WEIGHTS)

        assert 0.1 <= wsi <= 0.9

    def test_no_active_domain_raises_rather_than_returning_zero(self) -> None:
        """Returning 0.0 would assert 'this person is fine'. We do not know that;
        we know we cannot see them. The engine must say so, and the caller marks
        the assessment insufficient_coverage."""
        with pytest.raises(ManobalRiskError):
            compute_wsi([scored(Domain.WORKLOAD, 0.9, coverage=0.1, active=False)], WEIGHTS)

    def test_a_domain_absent_from_the_weight_table_is_ignored(self) -> None:
        scores = [scored(Domain.WORKLOAD, 0.5), scored(Domain.ENGAGEMENT, 1.0)]

        wsi = compute_wsi(scores, WEIGHTS)

        assert wsi == pytest.approx(0.5)
