"""Enrolment and per-domain consent — ``--enrolment-rate``, ``--consent-profile``.

The shape of this module is the point. Three of the seven domains are derived
from the nightly HRMS delta: duty rosters, leave applications, transfer requests.
The force already holds those records, so D1, D2 and D3 are present for every
person on the strength whether or not they ever open the app. The other four
require an affirmative act — installing the app, wearing the device, answering
the instrument, recording a voice check-in — and each is declined separately.

Modelling that correctly is what makes coverage renormalisation testable. If
consent were uniform, every subject would have the same seven-domain coverage and
the renormalised denominator in SDD §4.5 step 4 would never differ from the fixed
one, so the control that stops opting out from being the rational way to stay off
an officer's queue would never be exercised.

Take-up is not uniform across the force either. Junior ranks enrol less and
decline biometrics more — an anti-coercion design that produces a real,
measurable participation gap (SDD §12.4 K6), which the fairness fixtures need to
have something to say about.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

import numpy as np

from manobal_risk import Domain

from .config import ConsentProfile, GenerationConfig
from .indicators import OBJECTIVE_DOMAINS
from .population import RankBand, Subject
from .rng import substream

#: Conditional on enrolling, the probability of granting each opt-in domain.
#: Self-report is close to universal because it is the reason people enrol;
#: biometrics halve it, and voice — the most intrusive and least understood
#: channel — is declined by roughly seven in ten.
_GRANT_PROBABILITY: Mapping[Domain, float] = MappingProxyType(
    {
        Domain.SELF_REPORT: 0.94,
        Domain.PHYSIOLOGICAL: 0.55,
        Domain.VOCAL_ACOUSTIC: 0.31,
        Domain.ENGAGEMENT: 1.0,
    }
)

#: Enrolment multiplier by rank. Documented as a fixture, not a finding: the
#: gradient exists so that the K6 equity target has a gap to measure.
_ENROLMENT_BY_RANK: Mapping[RankBand, float] = MappingProxyType(
    {
        RankBand.CONSTABLE: 0.88,
        RankBand.HEAD_CONSTABLE: 0.97,
        RankBand.ASI: 1.06,
        RankBand.SI: 1.12,
        RankBand.INSPECTOR: 1.20,
        RankBand.GAZETTED: 1.26,
    }
)


@dataclass(frozen=True, slots=True)
class ConsentState:
    """One subject's enrolment and the domains they actually contribute."""

    enrolled: bool
    #: Day of the run on which enrolment took effect. Consent granted midway
    #: through means the domain has no history before it, which is a distinct
    #: coverage problem from having declined outright.
    enrolled_on_day: int
    granted: frozenset[Domain]

    @property
    def scoreable_domains(self) -> frozenset[Domain]:
        """Everything the engine may look at, opt-in and objective together."""
        return frozenset(OBJECTIVE_DOMAINS) | self.granted


def assign_consent(
    config: GenerationConfig,
    subjects: Sequence[Subject],
) -> tuple[ConsentState, ...]:
    """Decide enrolment and per-domain consent for the whole force."""
    if config.consent_profile is ConsentProfile.FULL:
        return tuple(_fully_consented() for _ in subjects)

    rng = substream(config.seed, "consent")
    count = len(subjects)
    enrolment_draws = rng.random(count)
    grant_draws = rng.random((count, len(_GRANT_PROBABILITY)))
    join_draws = rng.random(count)
    domains = tuple(_GRANT_PROBABILITY)

    states: list[ConsentState] = []
    for index, subject in enumerate(subjects):
        rate = config.enrolment_rate * _ENROLMENT_BY_RANK[subject.rank_band]
        enrolled = bool(enrolment_draws[index] < min(rate, 1.0))
        states.append(
            _state_for(
                enrolled=enrolled,
                domains=domains,
                draws=grant_draws[index],
                join_fraction=float(join_draws[index]),
                duration_days=config.duration_days,
            )
        )
    return tuple(states)


def _state_for(
    *,
    enrolled: bool,
    domains: tuple[Domain, ...],
    draws: np.ndarray,
    join_fraction: float,
    duration_days: int,
) -> ConsentState:
    if not enrolled:
        return ConsentState(enrolled=False, enrolled_on_day=0, granted=frozenset())
    granted = frozenset(
        domain
        for position, domain in enumerate(domains)
        if float(draws[position]) < _GRANT_PROBABILITY[domain]
    )
    # Enrolment is squeezed into the first fifth of the run so that most
    # consented subjects have enough history for a baseline. A rollout in which
    # everyone joins on day one would never exercise the "consented recently,
    # cannot be scored yet" path that the pilot's first weeks are made of.
    return ConsentState(
        enrolled=True,
        enrolled_on_day=int(join_fraction * max(duration_days // 5, 1)),
        granted=granted,
    )


def _fully_consented() -> ConsentState:
    return ConsentState(
        enrolled=True,
        enrolled_on_day=0,
        granted=frozenset(_GRANT_PROBABILITY),
    )
