"""Builders that construct subject histories with *known* domain scores.

The engine tests need to assert tier outcomes, which means they need histories
whose domain scores are exact rather than approximately plausible. Working
backwards from the deviation formula gives that:

    z_hat = clip(((x - mu) / max(mad, eps)) * d / z_divisor, 0, 1)

Emit a flat historical series (so ``mu`` is the flat value and ``mad`` is zero,
making the denominator exactly ``eps``), then place the current observation at
``mu + d * z_divisor * level * eps``. The indicator's deviation is then exactly
``level``, every indicator in a domain shares that level, and so the domain score
is exactly ``level`` too.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, timedelta

from manobal_risk.ruleset import Ruleset
from manobal_risk.types import AcuteTrigger, Domain, Observation, SubjectHistory, Tier

DEFAULT_AS_OF = date(2026, 6, 30)
BASE_VALUE = 100.0


def observations_for_domain(
    ruleset: Ruleset,
    domain: Domain,
    level: float,
    *,
    as_of: date = DEFAULT_AS_OF,
    history_days: int = 60,
    indicator_fraction: float = 1.0,
) -> list[Observation]:
    """Emit a history whose deviation for every indicator in ``domain`` is ``level``.

    ``indicator_fraction`` covers only part of the domain's indicators, which is
    how the coverage-floor tests starve a domain without removing it entirely.
    """
    specs = ruleset.indicators_for(domain)
    take = max(0, round(len(specs) * indicator_fraction))
    observations: list[Observation] = []

    for spec in sorted(specs, key=lambda s: s.code)[:take]:
        for offset in range(history_days, 0, -1):
            observations.append(
                Observation(
                    indicator_code=spec.code,
                    observed_on=as_of - timedelta(days=offset),
                    value=BASE_VALUE,
                )
            )
        current = BASE_VALUE + int(spec.direction) * ruleset.z_divisor * level * spec.epsilon
        observations.append(
            Observation(indicator_code=spec.code, observed_on=as_of, value=current)
        )

    return observations


def build_history(
    ruleset: Ruleset,
    levels: Mapping[Domain, float],
    *,
    subject_token: str = "st_test_subject",
    as_of: date = DEFAULT_AS_OF,
    consented_domains: frozenset[Domain] | None = None,
    acute_triggers: tuple[AcuteTrigger, ...] = (),
    previous_tier: Tier = Tier.T0,
    consecutive_lower_cycles: int = 0,
    indicator_fraction: float = 1.0,
    history_days: int = 60,
) -> SubjectHistory:
    """Build a subject whose domain scores are exactly ``levels``.

    Domains absent from ``levels`` contribute no observations at all, which is
    what a subject who never opted into wearables actually looks like.
    """
    observations: list[Observation] = []
    for domain, level in levels.items():
        observations.extend(
            observations_for_domain(
                ruleset,
                domain,
                level,
                as_of=as_of,
                history_days=history_days,
                indicator_fraction=indicator_fraction,
            )
        )

    return SubjectHistory(
        subject_token=subject_token,
        as_of=as_of,
        observations=tuple(observations),
        consented_domains=(
            consented_domains if consented_domains is not None else frozenset(levels)
        ),
        acute_triggers=acute_triggers,
        previous_tier=previous_tier,
        consecutive_lower_cycles=consecutive_lower_cycles,
    )
