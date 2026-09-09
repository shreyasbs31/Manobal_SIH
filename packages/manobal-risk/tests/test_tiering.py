"""Tier assignment — SDD §4.5 step 5, FR-3.4/3.5.

Four rules, applied in this order and no other:

    raw tier from WSI  ->  corroboration gate  ->  hysteresis  ->  acute override

The corroboration gate is the system's primary false-positive control, and the
acute override is its only override. Both are tested exhaustively because a
regression in either is a safety defect, not a bug.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from manobal_risk.ruleset import TierBounds
from manobal_risk.tiering import (
    apply_acute_override,
    apply_corroboration_gate,
    apply_hysteresis,
    raw_tier_for,
)
from manobal_risk.types import AcuteTrigger, AcuteTriggerKind, Tier

BOUNDS = TierBounds(t1=0.35, t2=0.55, t3=0.75)


class TestRawTier:
    @pytest.mark.parametrize(
        ("wsi", "expected"),
        [
            (0.0, Tier.T0),
            (0.34999, Tier.T0),
            (0.35, Tier.T1),
            (0.54999, Tier.T1),
            (0.55, Tier.T2),
            (0.74999, Tier.T2),
            (0.75, Tier.T3),
            (1.0, Tier.T3),
        ],
    )
    def test_boundaries_are_inclusive_at_the_lower_edge(self, wsi: float, expected: Tier) -> None:
        assert raw_tier_for(wsi, BOUNDS) is expected

    def test_raw_tier_never_reaches_t4(self) -> None:
        """T4 is reachable only through the acute override, never through a score."""
        assert raw_tier_for(1.0, BOUNDS) is Tier.T3

    def test_is_monotone_in_wsi(self) -> None:
        tiers = [raw_tier_for(w / 100, BOUNDS) for w in range(101)]
        assert tiers == sorted(tiers)


class TestCorroborationGate:
    def test_two_breaching_domains_let_the_raw_tier_stand(self) -> None:
        assert apply_corroboration_gate(Tier.T3, breaching_domain_count=2, minimum=2) == (
            Tier.T3,
            True,
        )

    def test_one_breaching_domain_is_capped_at_t1(self) -> None:
        """FR-3.4. One very bad PHQ-9, one terrible week of sleep, one spike in
        leave requests — none of them alone may raise a flag above T1."""
        assert apply_corroboration_gate(Tier.T3, breaching_domain_count=1, minimum=2) == (
            Tier.T1,
            False,
        )

    def test_zero_breaching_domains_is_capped_at_t1(self) -> None:
        assert apply_corroboration_gate(Tier.T2, breaching_domain_count=0, minimum=2) == (
            Tier.T1,
            False,
        )

    def test_the_gate_never_raises_a_tier(self) -> None:
        """It is a cap, not an adjustment. An uncorroborated T0 stays T0."""
        assert apply_corroboration_gate(Tier.T0, breaching_domain_count=0, minimum=2) == (
            Tier.T0,
            False,
        )

    def test_more_than_the_minimum_still_corroborates(self) -> None:
        assert apply_corroboration_gate(Tier.T3, breaching_domain_count=5, minimum=2) == (
            Tier.T3,
            True,
        )


class TestHysteresis:
    def test_a_rise_is_immediate(self) -> None:
        """FR-3.5 constrains decreases only. Deterioration is acted on at once."""
        assert apply_hysteresis(Tier.T3, previous=Tier.T1, consecutive_lower_cycles=0) is Tier.T3

    def test_a_fall_is_held_for_the_first_cycle(self) -> None:
        assert apply_hysteresis(Tier.T1, previous=Tier.T3, consecutive_lower_cycles=0) is Tier.T3

    def test_a_fall_is_still_held_on_the_second_cycle(self) -> None:
        assert apply_hysteresis(Tier.T1, previous=Tier.T3, consecutive_lower_cycles=1) is Tier.T3

    def test_a_fall_lands_once_two_consecutive_lower_cycles_have_passed(self) -> None:
        assert apply_hysteresis(Tier.T1, previous=Tier.T3, consecutive_lower_cycles=2) is Tier.T1

    def test_an_unchanged_tier_is_untouched(self) -> None:
        assert apply_hysteresis(Tier.T2, previous=Tier.T2, consecutive_lower_cycles=0) is Tier.T2

    def test_hysteresis_never_holds_a_person_above_an_acute_tier(self) -> None:
        """Falling from T4 obeys the same rule; the acute override re-applies
        afterwards if the trigger is still live."""
        assert apply_hysteresis(Tier.T2, previous=Tier.T4, consecutive_lower_cycles=2) is Tier.T2


class TestAcuteOverride:
    def _trigger(self) -> AcuteTrigger:
        return AcuteTrigger(
            kind=AcuteTriggerKind.PHQ9_ITEM9,
            occurred_at=datetime(2026, 9, 8, 18, 42, tzinfo=UTC),
            source="instrument",
        )

    def test_any_trigger_forces_t4(self) -> None:
        assert apply_acute_override(Tier.T0, (self._trigger(),)) == (Tier.T4, True)

    def test_no_trigger_leaves_the_tier_alone(self) -> None:
        assert apply_acute_override(Tier.T2, ()) == (Tier.T2, False)

    def test_the_override_beats_the_corroboration_gate(self) -> None:
        """SDD §4.5: the acute override bypasses everything above it, including
        the requirement for two corroborating domains."""
        gated, corroborated = apply_corroboration_gate(Tier.T3, breaching_domain_count=0, minimum=2)
        final, overridden = apply_acute_override(gated, (self._trigger(),))

        assert corroborated is False
        assert gated is Tier.T1
        assert final is Tier.T4
        assert overridden is True

    def test_the_override_beats_hysteresis(self) -> None:
        held = apply_hysteresis(Tier.T0, previous=Tier.T0, consecutive_lower_cycles=9)
        final, overridden = apply_acute_override(held, (self._trigger(),))

        assert final is Tier.T4
        assert overridden is True

    @pytest.mark.parametrize("kind", list(AcuteTriggerKind))
    def test_every_trigger_kind_escalates(self, kind: AcuteTriggerKind) -> None:
        trigger = AcuteTrigger(
            kind=kind, occurred_at=datetime(2026, 9, 8, tzinfo=UTC), source="test"
        )

        assert apply_acute_override(Tier.T0, (trigger,)) == (Tier.T4, True)
