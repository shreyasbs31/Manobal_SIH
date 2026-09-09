"""Realistic missingness — ``--missingness realistic``.

Appendix A.3 singles this out: partial consent and realistic missingness are
"what actually breaks coverage renormalisation". A generator with uniform
dropout would not break it, because uniform dropout lowers every domain's
coverage by the same amount and the renormalised denominator in SDD §4.5 step 4
comes out unchanged. The failure mode only appears when the *shape* of the
missingness differs per channel, and it does, badly:

* **HRMS gaps** are shared. A failed nightly extract removes a day of D1, D2 and
  D3 for the entire force at once, which is the one missingness event that is
  correlated across subjects and therefore the one that can move an aggregate.
* **Wearable non-wear** is bimodal and clustered. Charging gaps are scattered
  single nights; leave and rest days are systematically under-worn; and a device
  left in a locker produces a contiguous week of nothing. Losing thirty
  scattered nights and losing one thirty-night block have very different effects
  on a ninety-day baseline, and only the second one pushes D4 under its floor.
* **Skipped check-ins** are not modelled here at all — they come out of the
  engagement stage, because withdrawal is a signal rather than an accident. That
  is the deliberate coupling: the subjects whose EMA rows go missing are
  disproportionately the subjects the system most wants to see.

The consequence, asserted in ``test_coverage.py``, is that per-domain coverage
varies widely across the force under the realistic profile and not at all under
``none``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .arrays import BoolArray
from .config import GenerationConfig, MissingnessProfile
from .person import PersonModel
from .processes import scattered_spans
from .rng import substream

#: Nightly extract failures across the whole force, and how long one lasts.
_HRMS_OUTAGES_PER_YEAR = 5.0
_HRMS_OUTAGE_MIN_DAYS = 1
_HRMS_OUTAGE_MAX_DAYS = 3

#: Per-subject record gaps: a service number mid-transfer, a quarantined batch
#: row, a unit that filed late.
_HRMS_SUBJECT_GAP_RATE = 0.018

#: Baseline probability of a single night's non-wear, scaled by the subject's own
#: non-wear propensity trait.
_CHARGING_GAP_RATE = 0.055
#: Non-wear is far more likely on leave and somewhat more likely on a rest day.
#: A force-issued device is a duty device in most people's minds.
_LEAVE_NON_WEAR_RATE = 0.58
_REST_DAY_NON_WEAR_RATE = 0.17

#: Multi-day dropouts — device in a locker, in for repair, or simply abandoned
#: for a fortnight.
_DROPOUT_SPANS_PER_YEAR = 3.2
_DROPOUT_MIN_DAYS = 2
_DROPOUT_MAX_DAYS = 11

#: Fraction of offered instrument administrations that go unanswered, and of
#: offered voice check-ins that are not recorded.
_INSTRUMENT_NON_RESPONSE = 0.14
_VOICE_NON_RESPONSE = 0.24


@dataclass(frozen=True, slots=True)
class SubjectMissingness:
    """Per-channel availability masks for one subject."""

    hrms_present: BoolArray
    wearable_worn: BoolArray
    instrument_answered: BoolArray
    voice_recorded: BoolArray


def force_hrms_outages(config: GenerationConfig) -> BoolArray:
    """Days on which the nightly HRMS extract failed for everybody.

    Drawn once per run and shared, because that is what makes it the only
    missingness event capable of moving a unit-level or sector-level aggregate.
    """
    if config.missingness is MissingnessProfile.NONE:
        return np.zeros(config.duration_days, dtype=bool)
    return scattered_spans(
        substream(config.seed, "hrms_outage"),
        config.duration_days,
        spans_per_year=_HRMS_OUTAGES_PER_YEAR,
        min_length=_HRMS_OUTAGE_MIN_DAYS,
        max_length=_HRMS_OUTAGE_MAX_DAYS,
    )


def subject_missingness(
    config: GenerationConfig,
    person: PersonModel,
    outages: BoolArray,
    planned_leave: BoolArray,
    rest_day: BoolArray,
) -> SubjectMissingness:
    """Draw one subject's availability masks across the four fallible channels."""
    n_days = config.duration_days
    if config.missingness is MissingnessProfile.NONE:
        present = np.ones(n_days, dtype=bool)
        return SubjectMissingness(
            hrms_present=present,
            wearable_worn=present,
            instrument_answered=present,
            voice_recorded=present,
        )

    rng = substream(config.seed, "missingness", person.subject_index)
    subject_gap = rng.random(n_days) < _HRMS_SUBJECT_GAP_RATE
    return SubjectMissingness(
        hrms_present=~outages & ~subject_gap,
        wearable_worn=_wear_mask(rng, person, planned_leave, rest_day),
        instrument_answered=rng.random(n_days) >= _INSTRUMENT_NON_RESPONSE,
        voice_recorded=rng.random(n_days) >= _VOICE_NON_RESPONSE,
    )


def _wear_mask(
    rng: np.random.Generator,
    person: PersonModel,
    planned_leave: BoolArray,
    rest_day: BoolArray,
) -> BoolArray:
    n_days = len(planned_leave)
    propensity = person.trait("non_wear_propensity")
    nightly = np.full(n_days, _CHARGING_GAP_RATE * propensity)
    nightly = np.where(rest_day, np.maximum(nightly, _REST_DAY_NON_WEAR_RATE), nightly)
    nightly = np.where(planned_leave, np.maximum(nightly, _LEAVE_NON_WEAR_RATE), nightly)

    dropouts = scattered_spans(
        rng,
        n_days,
        spans_per_year=_DROPOUT_SPANS_PER_YEAR * propensity,
        min_length=_DROPOUT_MIN_DAYS,
        max_length=_DROPOUT_MAX_DAYS,
    )
    return (rng.random(n_days) >= np.clip(nightly, 0.0, 0.98)) & ~dropouts
