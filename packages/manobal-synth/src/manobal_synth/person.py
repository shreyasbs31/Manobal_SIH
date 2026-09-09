"""Per-person baselines — the reason this generator exists at all.

SDD §4.5 scores deviation from *the individual's own norm*, not from a population
norm, and §4.4 says so in the strongest terms available: "a jawan who has always
worked long hours is not flagged for working long hours; a jawan whose pattern
changes is". A generator that drew every indicator from one population
distribution would make that impossible to test, because there would be no
individual norm to deviate from.

So every subject carries their own level *and* their own dispersion for every
primitive in the model. A constable who habitually works fourteen-hour shifts
with a rock-steady roster and a constable who averages nine hours with wild
variance are both entirely normal, and each must be scored against themselves.
The traits below are sampled once per subject and never move; the time series is
generated around them. The direct consequence, asserted in
``test_personal_baseline.py``, is that a permanently heavy workload produces a
low deviation while a recent change in a light one produces a high deviation.

Dispersion is a trait in its own right, not a global constant, because the
robust-z denominator in SDD §4.5 step 2 is the subject's own MAD. Give everyone
the same noise and the epsilon floor stops mattering, and the floor is the
control that keeps a very stable person from being flagged for a trivial change.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

import numpy as np

from .population import RANK_LOAD_FACTOR, Subject
from .rng import substream, truncated_lognormal, truncated_normal


@dataclass(frozen=True, slots=True)
class Trait:
    """One sampled personal constant.

    ``sd`` is the between-person spread — how much people differ from each other.
    Traits whose name ends in ``_sd`` are themselves within-person spreads: how
    much this person differs from day to day. Keeping both in one table makes the
    distinction visible rather than buried in two places.
    """

    name: str
    mean: float
    sd: float
    lower: float
    upper: float
    lognormal: bool = False
    #: Traits scaled by the subject's rank band, because duty load is stratified
    #: by rank and a shared baseline would be a fiction.
    rank_scaled: bool = False


_TRAITS: tuple[Trait, ...] = (
    # Roster and workload primitives.
    Trait("shift_hours_mean", 9.4, 1.30, 6.5, 14.5, rank_scaled=True),
    Trait("shift_hours_sd", 1.05, 0.30, 0.30, 2.60),
    Trait("shift_start_mean", 7.5, 2.20, 0.0, 20.0),
    Trait("shift_start_sd", 1.35, 0.45, 0.20, 4.50),
    Trait("rest_denial_base", 0.26, 0.11, 0.02, 0.72, rank_scaled=True),
    # Sleep.
    Trait("sleep_duration_mean", 392.0, 34.0, 275.0, 500.0),
    Trait("sleep_duration_sd", 34.0, 8.0, 12.0, 70.0),
    Trait("sleep_efficiency_mean", 0.885, 0.035, 0.720, 0.965),
    Trait("sleep_efficiency_sd", 0.028, 0.008, 0.008, 0.065),
    Trait("sleep_onset_mean", 23.4, 1.10, 20.5, 27.0),
    Trait("sleep_onset_sd", 0.52, 0.17, 0.15, 1.50),
    # Autonomic and activity.
    Trait("hrv_rmssd_mean", 43.0, 11.0, 16.0, 90.0),
    Trait("hrv_rmssd_sd", 4.6, 1.30, 1.50, 12.0),
    Trait("resting_hr_mean", 61.0, 6.50, 44.0, 88.0),
    Trait("resting_hr_sd", 2.30, 0.65, 0.80, 6.50),
    Trait("daily_steps_mean", 8700.0, 2100.0, 3000.0, 18000.0),
    Trait("daily_steps_sd", 1350.0, 380.0, 400.0, 3800.0),
    Trait("spo2_min_mean", 93.6, 1.70, 86.0, 98.0),
    Trait("spo2_min_sd", 1.00, 0.28, 0.30, 2.80),
    # Daily check-in scales (1-5).
    Trait("ema_mood_mean", 3.72, 0.38, 2.20, 4.90),
    Trait("ema_mood_sd", 0.40, 0.11, 0.12, 1.00),
    Trait("ema_fatigue_mean", 2.55, 0.44, 1.20, 4.40),
    Trait("ema_fatigue_sd", 0.42, 0.12, 0.12, 1.10),
    Trait("ema_sleep_quality_mean", 3.48, 0.42, 1.60, 4.90),
    Trait("ema_sleep_quality_sd", 0.43, 0.12, 0.12, 1.10),
    # Instruments.
    Trait("pss10_mean", 14.6, 4.10, 3.0, 30.0),
    Trait("pss10_sd", 1.60, 0.45, 0.40, 4.50),
    Trait("phq9_mean", 4.20, 2.40, 0.0, 14.0),
    Trait("phq9_sd", 1.00, 0.30, 0.20, 3.20),
    Trait("gad7_mean", 3.60, 2.10, 0.0, 12.0),
    Trait("gad7_sd", 0.90, 0.28, 0.20, 3.00),
    # Prosody. Baselines vary strongly between speakers, which is precisely why
    # SDD §12.2 R9 weights D6 lowest — a population threshold on F0 variability
    # would be an accent detector.
    Trait("voice_f0_var_mean", 3.25, 0.62, 1.40, 6.00),
    Trait("voice_f0_var_sd", 0.30, 0.09, 0.08, 0.85),
    Trait("voice_speech_rate_mean", 4.25, 0.45, 2.60, 6.20),
    Trait("voice_speech_rate_sd", 0.20, 0.06, 0.05, 0.55),
    Trait("voice_pause_ratio_mean", 0.275, 0.045, 0.120, 0.500),
    Trait("voice_pause_ratio_sd", 0.024, 0.007, 0.005, 0.065),
    Trait("voice_jitter_mean", 0.0118, 0.0026, 0.0040, 0.0300),
    Trait("voice_jitter_sd", 0.0014, 0.0004, 0.0003, 0.0045),
    Trait("voice_shimmer_mean", 0.084, 0.017, 0.035, 0.180),
    Trait("voice_shimmer_sd", 0.0100, 0.0028, 0.0020, 0.0280),
    Trait("voice_loudness_mean_level", 0.625, 0.085, 0.300, 1.000),
    Trait("voice_loudness_sd", 0.040, 0.011, 0.008, 0.110),
    # Leave and organisational daily hazards. Log-normal: most personnel apply
    # rarely, a few apply often, and a normal draw would need clipping at zero.
    Trait("leave_apply_rate", 0.020, 0.45, 0.003, 0.090, lognormal=True),
    Trait("short_leave_share", 0.45, 0.12, 0.10, 0.85),
    Trait("leave_rejection_prob", 0.22, 0.10, 0.02, 0.70, rank_scaled=True),
    Trait("unplanned_absence_rate", 0.0045, 0.55, 0.0004, 0.0300, lognormal=True),
    Trait("transfer_request_rate", 0.0022, 0.55, 0.0002, 0.0150, lognormal=True),
    Trait("duty_swap_rate", 0.016, 0.45, 0.002, 0.080, lognormal=True),
    Trait("training_attend_prob", 0.62, 0.15, 0.10, 0.95),
    # Engagement.
    Trait("checkin_base_rate", 0.74, 0.16, 0.15, 0.99),
    Trait("app_sessions_mean", 1.05, 0.40, 0.10, 4.00),
    Trait("instrument_latency_base", 2.20, 0.90, 0.30, 8.00),
    # How strongly this person's downstream physiology and affect respond to the
    # same upstream load. Without it, two subjects on identical rosters would
    # show identical sleep loss, and the corroboration gate would never have to
    # cope with a subject whose body says less than their diary.
    Trait("reactivity", 1.00, 0.28, 0.35, 2.00),
    #: Non-wear propensity: some personnel are conscientious chargers, some are
    #: not, and wearable coverage is bimodal in every published cohort.
    Trait("non_wear_propensity", 1.00, 0.45, 0.15, 3.00),
)

TRAITS: Mapping[str, Trait] = MappingProxyType({trait.name: trait for trait in _TRAITS})


@dataclass(frozen=True, slots=True)
class PersonModel:
    """A subject's immutable behavioural constants."""

    subject_index: int
    subject_token: str
    traits: Mapping[str, float]
    #: Weekday on which this person's rest day normally falls. A fixed rest day
    #: is what makes ``consecutive_duty_days`` a meaningful run length rather
    #: than a random walk.
    rest_weekday: int

    def trait(self, name: str) -> float:
        return self.traits[name]


def build_person(seed: int, subject: Subject) -> PersonModel:
    """Sample one subject's traits from a substream addressed by their index."""
    rng = substream(seed, "person", subject.index)
    load = RANK_LOAD_FACTOR[subject.rank_band]
    values: dict[str, float] = {}
    for trait in _TRAITS:
        scale = load if trait.rank_scaled else 1.0
        values[trait.name] = _draw(rng, trait, scale)
    return PersonModel(
        subject_index=subject.index,
        subject_token=subject.subject_token,
        traits=MappingProxyType(values),
        rest_weekday=int(rng.integers(0, 7)),
    )


def _draw(rng: np.random.Generator, trait: Trait, scale: float) -> float:
    if trait.lognormal:
        return truncated_lognormal(
            rng, trait.mean * scale, trait.sd, trait.lower, trait.upper * max(scale, 1.0)
        )
    return truncated_normal(
        rng, trait.mean * scale, trait.sd, trait.lower, trait.upper * max(scale, 1.0)
    )
