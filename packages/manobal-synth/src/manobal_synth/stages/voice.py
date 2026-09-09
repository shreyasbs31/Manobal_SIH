"""Stage 4 — D6 vocal-acoustic prosody.

Reduced pitch range, slower speech, longer pauses, more jitter and shimmer, lower
loudness. All six move off the affect latent, because psychomotor slowing is a
consequence of affect rather than a separate signal — which is why the ruleset
gives D6 the lowest weight and the highest corroboration bar: it is largely
telling us again, less reliably, what D5 already said.

Two properties are modelled deliberately.

Between-speaker variation in every one of these features dwarfs the within-speaker
change that distress produces. That is the entire argument for the personal
baseline in D6 and the reason SDD §12.2 R9 treats a population threshold on F0
variability as an accent detector. The trait table reflects it: baseline spread
across subjects is several times the daily spread within one.

A suppressor's prosody is only *partly* controllable. Somebody managing their
self-report can flatten a questionnaire completely and their pause ratio barely
at all, so gaming attenuates this stage far less than the last one — and D6 is
one of the channels that can still catch them, if they consented to it.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..arrays import BoolArray, FloatArray
from ..person import PersonModel
from ..windows import lagged_smooth

#: Voice check-ins are offered roughly three times a week. Over a ninety-day
#: baseline window that is comfortably above the engine's twenty-one-observation
#: floor — until non-response and non-consent take their share, which is when D6
#: drops below its coverage floor and stops participating.
CHECKIN_PROBABILITY = 3.0 / 7.0

_VOCAL_LAG_DAYS = 7
_AFFECT_TO_VOCAL = 0.78
_RECOVERY_TO_VOCAL = 0.16

#: Prosody responds to affect over days, not minutes; the same voice sample on a
#: better week sounds different. Attenuation for suppressors is mild.
GAMING_ATTENUATION = 0.62

_F0_VARIABILITY_DROP = 0.62
_SPEECH_RATE_DROP = 0.40
_PAUSE_RATIO_RISE = 0.050
_JITTER_RISE = 0.0030
_SHIMMER_RISE = 0.0215
_LOUDNESS_DROP = 0.082


@dataclass(frozen=True, slots=True)
class VoiceStage:
    indicators: dict[str, FloatArray]
    #: Days on which a voice check-in was recorded. Off-days carry no value at
    #: all — prosody cannot be carried forward the way an instrument score can,
    #: because it is a measurement of one utterance and not a standing state.
    checkin_days: BoolArray


def voice_stage(
    rng: np.random.Generator,
    person: PersonModel,
    affect: FloatArray,
    recovery_deficit: FloatArray,
    *,
    gaming: bool,
) -> VoiceStage:
    """Generate prosodic derivatives on the days a check-in was recorded."""
    n_days = len(affect)
    vocal = _AFFECT_TO_VOCAL * lagged_smooth(affect, _VOCAL_LAG_DAYS) + (
        _RECOVERY_TO_VOCAL * recovery_deficit
    )
    if gaming:
        vocal = vocal * GAMING_ATTENUATION

    features = {
        "voice_f0_variability": (
            person.trait("voice_f0_var_mean") - _F0_VARIABILITY_DROP * vocal,
            person.trait("voice_f0_var_sd"),
            (0.2, 12.0),
        ),
        "voice_speech_rate": (
            person.trait("voice_speech_rate_mean") - _SPEECH_RATE_DROP * vocal,
            person.trait("voice_speech_rate_sd"),
            (0.8, 9.0),
        ),
        "voice_pause_ratio": (
            person.trait("voice_pause_ratio_mean") + _PAUSE_RATIO_RISE * vocal,
            person.trait("voice_pause_ratio_sd"),
            (0.01, 0.90),
        ),
        "voice_jitter_local": (
            person.trait("voice_jitter_mean") + _JITTER_RISE * vocal,
            person.trait("voice_jitter_sd"),
            (0.0005, 0.08),
        ),
        "voice_shimmer_local": (
            person.trait("voice_shimmer_mean") + _SHIMMER_RISE * vocal,
            person.trait("voice_shimmer_sd"),
            (0.005, 0.45),
        ),
        "voice_loudness_mean": (
            person.trait("voice_loudness_mean_level") - _LOUDNESS_DROP * vocal,
            person.trait("voice_loudness_sd"),
            (0.02, 1.60),
        ),
    }
    indicators = {
        code: np.clip(level + rng.normal(0.0, noise_sd, size=n_days), *bounds)
        for code, (level, noise_sd, bounds) in features.items()
    }
    return VoiceStage(
        indicators=indicators,
        checkin_days=rng.random(n_days) < CHECKIN_PROBABILITY,
    )
