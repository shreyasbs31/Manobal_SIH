"""Stage 3 — D5 self-report: affect, then what the subject chooses to say about it.

The affect latent is the hinge of the whole chain. It is driven by the recovery
deficit from D4, by sustained workload from D1, and by a direct component
carrying the part of distress that duty never touched. Everything below this
stage — prosody, leave-seeking, transfer requests, app withdrawal — is downstream
of affect, which is why suppressing self-report cannot make a person look well.

That is the ``--gaming-cohort`` mechanism, and it lives here in three lines.
A suppressor's *affect* is unchanged; only the reported value is flattened
towards their own healthy baseline. Their sleep still fragments, their HRV still
falls, they still apply for leave and ask for a transfer. SDD §12.2 R6 claims
multi-domain corroboration defeats single-channel gaming; this is the fixture
that lets the claim be tested instead of asserted.

Instruments are administered fortnightly and the derived indicator is carried
forward daily — see ``windows.carry_forward`` for why the risk engine's
twenty-one-observation rule makes that the only workable representation.

**Calibration note.** The sensitivities below are set so that the modelled
severity range spans the ruleset's whole tier range: a moderate decline reaches
T1, a severe one reaches T3. That is a deliberate choice about what the corpus is
*for*. A generator whose most severe case topped out at T1 would leave the
digest, case-assignment and escalation paths with no data to run on, and every
number in the SDD's v1.0 ruleset is a calibration target rather than a validated
constant (see the artefact's own header).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..arrays import BoolArray, FloatArray
from ..person import PersonModel
from ..processes import ar1
from ..windows import carry_forward, lagged_smooth

#: Weights of affect's three parents.
_RECOVERY_TO_AFFECT = 0.42
_WORKLOAD_TO_AFFECT = 0.30
#: The non-occupational share of distress. Larger than the workload term because
#: a decline driven purely by duty would make D1 a sufficient statistic for
#: everything, and the corroboration gate would be measuring one signal twice.
_DISTRESS_TO_AFFECT = 1.15
_AFFECT_LAG_DAYS = 14

#: Mood has its own weather independent of duty. Autocorrelated rather than white
#: so that a bad fortnight looks like a bad fortnight.
_AFFECT_NOISE_PHI = 0.90
_AFFECT_NOISE_SD = 0.22

#: Instrument responses per unit of affect. PSS-10 moves most because it measures
#: perceived stress directly; PHQ-9 and GAD-7 move less because they are asking
#: about a narrower construct.
_PSS10_PER_AFFECT = 6.6
_PHQ9_PER_AFFECT = 5.1
_GAD7_PER_AFFECT = 4.3

#: Five-point daily scales.
_MOOD_PER_AFFECT = 0.82
_FATIGUE_PER_AFFECT = 0.92
_SLEEP_QUALITY_PER_AFFECT = 0.80
#: Fatigue also tracks acute sleep debt, not just affect — a person can be
#: exhausted and in good spirits, and D5 should be able to say so.
_FATIGUE_PER_SLEEP_DEBT = 0.16

#: Fortnightly, matching PHQ-9's two-week reference period.
INSTRUMENT_INTERVAL_DAYS = 14

#: What a suppressor's reported affect is multiplied by. Not zero: a subject who
#: reported an implausibly perfect score every fortnight would be detectable as
#: an outlier on the self-report channel alone, which is not the adversary the
#: corroboration gate is designed against.
GAMING_SUPPRESSION = 0.14
#: Suppressors also drift their reports slightly *below* their own baseline, the
#: way a person managing an impression overshoots towards "fine".
GAMING_UNDERSHOOT = 0.25


@dataclass(frozen=True, slots=True)
class SelfReportStage:
    indicators: dict[str, FloatArray]
    #: Days on which an instrument was actually administered. Carried-forward
    #: days are still emitted, but the missingness model needs to know which
    #: rows are fresh measurements to be able to drop an administration.
    instrument_days: BoolArray
    #: Affect as it truly is, before suppression. Every later stage reads this,
    #: which is exactly why gaming does not propagate.
    affect: FloatArray


def self_report_stage(
    rng: np.random.Generator,
    person: PersonModel,
    workload_strain: FloatArray,
    recovery_deficit: FloatArray,
    sleep_debt: FloatArray,
    distress_strain: FloatArray,
    *,
    gaming: bool,
) -> SelfReportStage:
    """Generate affect, then the reported instruments and daily check-ins."""
    n_days = len(distress_strain)
    reactivity = person.trait("reactivity")
    affect = reactivity * (
        _RECOVERY_TO_AFFECT * recovery_deficit
        + _WORKLOAD_TO_AFFECT * lagged_smooth(workload_strain, _AFFECT_LAG_DAYS)
        + _DISTRESS_TO_AFFECT * distress_strain
    ) + ar1(rng, n_days, _AFFECT_NOISE_PHI, _AFFECT_NOISE_SD)

    reported = _reported_affect(affect, gaming=gaming)
    instrument_days = _administration_days(rng, n_days)
    indicators = _daily_indicators(rng, person, reported, sleep_debt)
    indicators.update(_instrument_indicators(rng, person, reported, instrument_days))

    return SelfReportStage(
        indicators=indicators,
        instrument_days=instrument_days,
        affect=affect,
    )


def _reported_affect(affect: FloatArray, *, gaming: bool) -> FloatArray:
    if not gaming:
        return affect
    return GAMING_SUPPRESSION * affect - GAMING_UNDERSHOOT


def _administration_days(rng: np.random.Generator, n_days: int) -> BoolArray:
    """Fortnightly administration with a per-subject phase and a few days' jitter.

    Jitter matters: a force where every instrument lands on the same day would
    make the carried-forward series identical across subjects and hide the
    coverage effect of one missed administration.
    """
    phase = int(rng.integers(0, INSTRUMENT_INTERVAL_DAYS))
    days = np.arange(n_days)
    jitter = rng.integers(-2, 3, size=n_days)
    return ((days - phase + jitter) % INSTRUMENT_INTERVAL_DAYS) == 0


def _daily_indicators(
    rng: np.random.Generator,
    person: PersonModel,
    reported: FloatArray,
    sleep_debt: FloatArray,
) -> dict[str, FloatArray]:
    n_days = len(reported)
    mood = (
        person.trait("ema_mood_mean")
        - _MOOD_PER_AFFECT * reported
        + rng.normal(0.0, person.trait("ema_mood_sd"), size=n_days)
    )
    fatigue = (
        person.trait("ema_fatigue_mean")
        + _FATIGUE_PER_AFFECT * reported
        + _FATIGUE_PER_SLEEP_DEBT * sleep_debt
        + rng.normal(0.0, person.trait("ema_fatigue_sd"), size=n_days)
    )
    quality = (
        person.trait("ema_sleep_quality_mean")
        - _SLEEP_QUALITY_PER_AFFECT * reported
        + rng.normal(0.0, person.trait("ema_sleep_quality_sd"), size=n_days)
    )
    return {
        "ema_mood": np.clip(mood, 1.0, 5.0),
        "ema_fatigue": np.clip(fatigue, 1.0, 5.0),
        "ema_sleep_quality": np.clip(quality, 1.0, 5.0),
    }


def _instrument_indicators(
    rng: np.random.Generator,
    person: PersonModel,
    reported: FloatArray,
    instrument_days: BoolArray,
) -> dict[str, FloatArray]:
    """Score the three instruments on administration days and hold them forward.

    The affect they score is the fortnight behind the administration, not the
    day of it, because that is the reference period the instruments ask about.
    """
    window = lagged_smooth(reported, INSTRUMENT_INTERVAL_DAYS)
    n_days = len(reported)
    scored = {
        "pss10_total": (
            person.trait("pss10_mean") + _PSS10_PER_AFFECT * window,
            person.trait("pss10_sd"),
            (0.0, 40.0),
        ),
        "phq9_total": (
            person.trait("phq9_mean") + _PHQ9_PER_AFFECT * window,
            person.trait("phq9_sd"),
            (0.0, 27.0),
        ),
        "gad7_total": (
            person.trait("gad7_mean") + _GAD7_PER_AFFECT * window,
            person.trait("gad7_sd"),
            (0.0, 21.0),
        ),
    }
    indicators: dict[str, FloatArray] = {}
    for code, (level, noise_sd, bounds) in scored.items():
        measured = np.clip(level + rng.normal(0.0, noise_sd, size=n_days), *bounds)
        indicators[code] = carry_forward(measured, instrument_days)
    return indicators
