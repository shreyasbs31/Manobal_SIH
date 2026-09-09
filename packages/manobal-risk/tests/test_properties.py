"""Property-based tests — SDD §9.1, mandatory on the risk engine.

Example-based tests check the cases we thought of. These check the cases we did
not. Every property here is a claim the rest of the system makes about the engine
in public: in the consent text, in the officer training, or in the compliance
mapping. If one of them stops holding, something the force has been told is true
has quietly become false.

One note on SDD §9.1's ``test_opting_out_never_changes_tier``. As literally
written it asserts that removing a domain's data cannot move the tier in either
direction. That cannot hold for a weighted mean — removing a high-scoring domain
lowers the mean and removing a low-scoring one raises it — and a test written to
pass would have to be vacuous. The guarantees that renormalisation *does* give
are stated precisely below, and docs/adr/0002 records the reasoning.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from manobal_risk import score, score_with_trace
from manobal_risk.ruleset import Ruleset
from manobal_risk.tiering import apply_hysteresis
from manobal_risk.types import AcuteTrigger, AcuteTriggerKind, Domain, Tier

from .builders import build_history

ASSESSED_AT = datetime(2026, 6, 30, 2, 0, tzinfo=UTC)

# A short history keeps generation cheap while still clearing the ruleset's
# 21-observation minimum.
HISTORY_DAYS = 25

PROPERTY_SETTINGS = settings(
    max_examples=75,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)

levels = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
domains = st.sampled_from(list(Domain))


@st.composite
def domain_levels(draw: st.DrawFn, min_domains: int = 0, max_domains: int = 7) -> dict:
    chosen = draw(
        st.lists(domains, min_size=min_domains, max_size=max_domains, unique=True)
    )
    return {domain: draw(levels) for domain in chosen}


class TestCompositeInvariants:
    @given(spec=domain_levels(min_domains=1))
    @PROPERTY_SETTINGS
    def test_wsi_stays_within_the_unit_interval(self, ruleset: Ruleset, spec: dict) -> None:
        history = build_history(ruleset, spec, history_days=HISTORY_DAYS)

        _, trace = score_with_trace(history, ruleset, assessed_at=ASSESSED_AT)

        assert 0.0 <= trace.wsi <= 1.0

    @given(spec=domain_levels(min_domains=1))
    @PROPERTY_SETTINGS
    def test_wsi_is_bounded_by_the_active_domain_scores(
        self, ruleset: Ruleset, spec: dict
    ) -> None:
        """A weighted mean cannot exceed its largest input. This is what stops a
        low-weight, low-evidence domain such as voice ever driving a tier on its
        own."""
        history = build_history(ruleset, spec, history_days=HISTORY_DAYS)

        _, trace = score_with_trace(history, ruleset, assessed_at=ASSESSED_AT)
        active = [ds.score for ds in trace.domain_scores if ds.active]
        assume(active)

        assert min(active) - 1e-9 <= trace.wsi <= max(active) + 1e-9

    @given(level=levels, subset_a=st.integers(1, 7), subset_b=st.integers(1, 7))
    @PROPERTY_SETTINGS
    def test_wsi_does_not_depend_on_how_many_domains_a_person_shares(
        self, ruleset: Ruleset, level: float, subset_a: int, subset_b: int
    ) -> None:
        """FR-3.3, stated precisely.

        Two people carrying the same adversity get the same composite index
        whether they contribute two domains or all seven. Without renormalisation
        the person who shared more would score higher purely for sharing, and
        declining to participate would be the rational move.
        """
        ordered = list(Domain)
        history_a = build_history(
            ruleset, dict.fromkeys(ordered[:subset_a], level), history_days=HISTORY_DAYS
        )
        history_b = build_history(
            ruleset, dict.fromkeys(ordered[:subset_b], level), history_days=HISTORY_DAYS
        )

        _, trace_a = score_with_trace(history_a, ruleset, assessed_at=ASSESSED_AT)
        _, trace_b = score_with_trace(history_b, ruleset, assessed_at=ASSESSED_AT)

        assert trace_a.wsi == pytest.approx(trace_b.wsi, abs=1e-9)

    @given(level=levels, subset_a=st.integers(2, 7), subset_b=st.integers(2, 7))
    @PROPERTY_SETTINGS
    def test_equal_adversity_yields_an_equal_tier_once_both_can_corroborate(
        self, ruleset: Ruleset, level: float, subset_a: int, subset_b: int
    ) -> None:
        """The comparative fairness guarantee: given the same adversity and
        enough domains for the gate to be satisfiable, breadth of participation
        does not change the outcome."""
        ordered = list(Domain)
        result_a = score(
            build_history(
                ruleset, dict.fromkeys(ordered[:subset_a], level), history_days=HISTORY_DAYS
            ),
            ruleset,
            assessed_at=ASSESSED_AT,
        )
        result_b = score(
            build_history(
                ruleset, dict.fromkeys(ordered[:subset_b], level), history_days=HISTORY_DAYS
            ),
            ruleset,
            assessed_at=ASSESSED_AT,
        )
        assume(result_a.corroborated == result_b.corroborated)

        assert result_a.tier is result_b.tier


class TestCorroborationGate:
    @given(level=levels, domain=domains)
    @PROPERTY_SETTINGS
    def test_no_single_domain_however_extreme_exceeds_watch(
        self, ruleset: Ruleset, level: float, domain: Domain
    ) -> None:
        """FR-3.4. The system's primary false-positive control, generalised over
        every domain and every possible severity."""
        history = build_history(ruleset, {domain: level}, history_days=HISTORY_DAYS)

        result = score(history, ruleset, assessed_at=ASSESSED_AT)

        assert result.tier <= Tier.T1
        assert result.corroborated is False

    @given(spec=domain_levels(min_domains=1), dropped=domains)
    @PROPERTY_SETTINGS
    def test_an_uncorroborated_person_cannot_become_visible_by_withdrawing_data(
        self, ruleset: Ruleset, spec: dict, dropped: Domain
    ) -> None:
        """The part of SDD §9.1's intent that is actually provable.

        Withdrawing a domain can only shrink the set of breaching domains, so an
        assessment that failed the corroboration gate still fails it afterwards
        and stays capped at T1 — which only the individual ever sees.

        The stronger claim, that withdrawal cannot move the tier at all, is false
        for a weighted mean and is characterised in
        ``test_withdrawal_dilution.py`` rather than asserted here.
        """
        full = build_history(ruleset, spec, history_days=HISTORY_DAYS)
        full_result = score(full, ruleset, assessed_at=ASSESSED_AT)
        assume(not full_result.corroborated)

        reduced = full.without_domain(dropped, ruleset.indicator_domains)
        reduced_result = score(reduced, ruleset, assessed_at=ASSESSED_AT)

        assert reduced_result.corroborated is False
        assert reduced_result.tier <= Tier.T1
        assert reduced_result.is_actionable_by_officer is False

    @given(spec=domain_levels(min_domains=1), dropped=domains)
    @PROPERTY_SETTINGS
    def test_withdrawing_a_domain_never_increases_the_corroborating_count(
        self, ruleset: Ruleset, spec: dict, dropped: Domain
    ) -> None:
        full = build_history(ruleset, spec, history_days=HISTORY_DAYS)
        reduced = full.without_domain(dropped, ruleset.indicator_domains)

        _, full_trace = score_with_trace(full, ruleset, assessed_at=ASSESSED_AT)
        _, reduced_trace = score_with_trace(reduced, ruleset, assessed_at=ASSESSED_AT)

        assert set(reduced_trace.breaching_domains) <= set(full_trace.breaching_domains)


class TestHysteresisProperties:
    @given(
        sequence=st.lists(st.sampled_from([Tier.T0, Tier.T1, Tier.T2, Tier.T3]), min_size=2)
    )
    @PROPERTY_SETTINGS
    def test_a_tier_never_falls_faster_than_the_ruleset_permits(
        self, ruleset: Ruleset, sequence: list[Tier]
    ) -> None:
        current = sequence[0]
        lower_cycles = 0

        for candidate in sequence[1:]:
            held = apply_hysteresis(
                candidate,
                previous=current,
                consecutive_lower_cycles=lower_cycles,
                required_cycles=ruleset.hysteresis_cycles,
            )
            if candidate < current:
                assert held == current or lower_cycles >= ruleset.hysteresis_cycles
                lower_cycles += 1
            else:
                lower_cycles = 0
            current = held

    @given(candidate=st.sampled_from(list(Tier)), previous=st.sampled_from(list(Tier)))
    @PROPERTY_SETTINGS
    def test_hysteresis_never_lowers_a_tier(
        self, ruleset: Ruleset, candidate: Tier, previous: Tier
    ) -> None:
        """It is a brake on descent, never an accelerator."""
        held = apply_hysteresis(
            candidate,
            previous=previous,
            consecutive_lower_cycles=0,
            required_cycles=ruleset.hysteresis_cycles,
        )

        assert held >= candidate


class TestAcuteOverrideProperties:
    @given(
        spec=domain_levels(),
        kind=st.sampled_from(list(AcuteTriggerKind)),
        previous=st.sampled_from(list(Tier)),
        lower_cycles=st.integers(0, 5),
    )
    @PROPERTY_SETTINGS
    def test_an_acute_trigger_always_wins(
        self,
        ruleset: Ruleset,
        spec: dict,
        kind: AcuteTriggerKind,
        previous: Tier,
        lower_cycles: int,
    ) -> None:
        """SDD §4.7. No combination of coverage, consent, corroboration or
        hysteresis can suppress an acute escalation."""
        history = build_history(
            ruleset,
            spec,
            history_days=HISTORY_DAYS,
            previous_tier=previous,
            consecutive_lower_cycles=lower_cycles,
            acute_triggers=(
                AcuteTrigger(kind=kind, occurred_at=ASSESSED_AT, source="property-test"),
            ),
        )

        result = score(history, ruleset, assessed_at=ASSESSED_AT)

        assert result.tier is Tier.T4
        assert result.acute_override is True


class TestOutputDiscipline:
    @given(spec=domain_levels(min_domains=1))
    @PROPERTY_SETTINGS
    def test_no_numeric_score_is_ever_serialisable_from_an_assessment(
        self, ruleset: Ruleset, spec: dict
    ) -> None:
        """FR-3.7 as a test rather than a convention (SDD §9.1)."""
        import dataclasses
        import json
        import re

        history = build_history(ruleset, spec, history_days=HISTORY_DAYS)
        result = score(history, ruleset, assessed_at=ASSESSED_AT)

        body = json.dumps(dataclasses.asdict(result), default=str)

        assert not re.search(r"\b(wsi|probability|percentile|confidence)\b", body, re.I)
        assert not re.search(r"\b(depress\w*|anxiet\w*|diagnos\w*|disorder)\b", body, re.I)

    @given(spec=domain_levels(min_domains=1))
    @PROPERTY_SETTINGS
    def test_reported_coverage_always_matches_the_domains_that_were_used(
        self, ruleset: Ruleset, spec: dict
    ) -> None:
        history = build_history(ruleset, spec, history_days=HISTORY_DAYS)

        result, trace = score_with_trace(history, ruleset, assessed_at=ASSESSED_AT)

        assert {d for d, active in result.domain_coverage if active} == set(
            trace.active_domains
        )

    @given(spec=domain_levels(min_domains=1))
    @PROPERTY_SETTINGS
    def test_scoring_the_same_input_twice_gives_the_same_answer(
        self, ruleset: Ruleset, spec: dict
    ) -> None:
        history = build_history(ruleset, spec, history_days=HISTORY_DAYS)

        assert score(history, ruleset, assessed_at=ASSESSED_AT) == score(
            history, ruleset, assessed_at=ASSESSED_AT
        )
