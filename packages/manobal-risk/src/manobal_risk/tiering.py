"""Tier assignment — SDD §4.5 step 5, FR-3.4/3.5.

Applied strictly in this order:

    raw tier from WSI  ->  corroboration gate  ->  hysteresis  ->  acute override

Each step is a separate pure function so that each can be tested in isolation and
so that the order is visible at the call site in :mod:`manobal_risk.engine`
rather than buried inside one long conditional.
"""

from __future__ import annotations

from collections.abc import Sequence

from .ruleset import TierBounds
from .types import AcuteTrigger, Tier


def raw_tier_for(wsi: float, bounds: TierBounds) -> Tier:
    """Map the composite index onto a tier, before any gate is applied.

    T4 is deliberately unreachable here. No score, however extreme, produces an
    acute tier — only a safety-critical trigger does (SDD §4.7).
    """
    if wsi >= bounds.t3:
        return Tier.T3
    if wsi >= bounds.t2:
        return Tier.T2
    if wsi >= bounds.t1:
        return Tier.T1
    return Tier.T0


def apply_corroboration_gate(
    raw_tier: Tier,
    *,
    breaching_domain_count: int,
    minimum: int,
) -> tuple[Tier, bool]:
    """Cap the tier at T1 unless at least ``minimum`` domains breached (FR-3.4).

    This is the primary false-positive control. One very bad PHQ-9, one week of
    terrible sleep, one spike in leave requests — none of them alone raises a
    flag above T1.

    It will suppress some true positives, and that is the correct trade. In a
    hierarchical uniformed setting a false positive is not a harmless extra
    conversation: it teaches a unit that the system flags people wrongly, and
    once that belief takes hold no amount of later accuracy recovers
    participation.

    Returns ``(tier, corroborated)``. The gate only ever lowers a tier.
    """
    corroborated = breaching_domain_count >= minimum
    if corroborated:
        return raw_tier, True
    return min(raw_tier, Tier.T1), False


def apply_hysteresis(
    candidate: Tier,
    *,
    previous: Tier,
    consecutive_lower_cycles: int,
    required_cycles: int = 2,
) -> Tier:
    """Hold a falling tier until it has stayed down for ``required_cycles``.

    FR-3.5 constrains decreases only. Deterioration is acted on immediately;
    recovery has to be demonstrated. The asymmetry is intentional — the cost of
    reacting slowly to improvement is an unnecessary conversation, and the cost
    of reacting slowly to decline is not.
    """
    if candidate < previous and consecutive_lower_cycles < required_cycles:
        return previous
    return candidate


def apply_acute_override(
    tier: Tier,
    acute_triggers: Sequence[AcuteTrigger],
) -> tuple[Tier, bool]:
    """Force T4 when a safety-critical trigger is present (SDD §4.7).

    This is the only override in the system. It bypasses the corroboration gate,
    hysteresis, the batch queue and — outside this module, in the alerting path —
    the subject's refusal of contact, on the legal basis of vital interest under
    DPDP Act 2023 §7(c)-(d). Every instance is logged under a distinct audit
    category and reviewed by the WDEC.

    Returns ``(tier, overridden)``.
    """
    if acute_triggers:
        return Tier.T4, True
    return tier, False
