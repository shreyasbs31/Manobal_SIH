"""The indicator registry — which codes exist, and where each one comes from.

The codes are not this package's to choose. They are declared by the signed
ruleset artefact, and ``test_registry.py`` asserts that this table and
``rulesets/manobal-ruleset-1.0.0.yaml`` agree exactly on codes and domains. If
someone adds an indicator to the ruleset without teaching the generator to
produce it, the build fails rather than the pilot quietly running with a domain
permanently below its coverage floor.

``channel`` is the part the ruleset does not carry and the generator needs:
*which acquisition path a value arrives on*. Consent and missingness are
properties of the channel, not of the domain — a subject who declines the
wearable loses D4 entirely while their leave record is unaffected, because the
force already holds the leave record and never needed an opt-in for it.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from manobal_risk import Domain


class Channel(StrEnum):
    """How a value physically reaches the platform."""

    #: Derived from the nightly HRMS delta (SDD §4.4). No opt-in: these are
    #: records the force already holds about duty, leave and postings.
    HRMS = "hrms_delta"
    #: Force-issued wearable over BLE. Opt-in, and subject to non-wear.
    WEARABLE = "force_wearable"
    #: Validated instrument, administered fortnightly in-app.
    INSTRUMENT = "psychometric_instrument"
    #: Daily five-point check-in.
    EMA = "daily_checkin"
    #: On-device prosodic derivatives from a voice check-in.
    VOICE = "voice_checkin"
    #: App telemetry. Available to anyone enrolled, by definition of being
    #: enrolled — it is the meta-signal that measures the other channels.
    APP = "app_telemetry"


@dataclass(frozen=True, slots=True)
class IndicatorSpec:
    """Emission metadata for one indicator code."""

    code: str
    domain: Domain
    channel: Channel
    #: Counts are emitted as integers so that a Fano factor or a rejection tally
    #: does not arrive at the engine reading 2.9999999996.
    integral: bool = False
    decimals: int = 4


def _spec(
    code: str,
    domain: Domain,
    channel: Channel,
    *,
    integral: bool = False,
    decimals: int = 4,
) -> IndicatorSpec:
    return IndicatorSpec(
        code=code, domain=domain, channel=channel, integral=integral, decimals=decimals
    )


_SPECS: tuple[IndicatorSpec, ...] = (
    # D1 workload — rolling roster aggregates.
    _spec("duty_hours_7d", Domain.WORKLOAD, Channel.HRMS, decimals=2),
    _spec("duty_hours_28d", Domain.WORKLOAD, Channel.HRMS, decimals=2),
    _spec("consecutive_duty_days", Domain.WORKLOAD, Channel.HRMS, integral=True),
    _spec("roster_volatility", Domain.WORKLOAD, Channel.HRMS),
    _spec("rest_denial_count", Domain.WORKLOAD, Channel.HRMS, integral=True),
    # D2 leave.
    _spec("leave_apply_rate_delta", Domain.LEAVE, Channel.HRMS),
    _spec("short_leave_burstiness", Domain.LEAVE, Channel.HRMS),
    _spec("leave_rejection_count", Domain.LEAVE, Channel.HRMS, integral=True),
    _spec("unplanned_absence_count", Domain.LEAVE, Channel.HRMS, integral=True),
    # D3 organisational.
    _spec("transfer_request_count", Domain.ORGANISATIONAL, Channel.HRMS, integral=True),
    _spec("duty_swap_rate_delta", Domain.ORGANISATIONAL, Channel.HRMS),
    _spec("training_participation_delta", Domain.ORGANISATIONAL, Channel.HRMS),
    _spec("deployment_intensity", Domain.ORGANISATIONAL, Channel.HRMS, decimals=2),
    _spec("family_separation_days", Domain.ORGANISATIONAL, Channel.HRMS, integral=True),
    # D4 physiological — nightly wearable readings.
    _spec("resting_hr_nightly", Domain.PHYSIOLOGICAL, Channel.WEARABLE, decimals=2),
    _spec("hrv_rmssd_nightly", Domain.PHYSIOLOGICAL, Channel.WEARABLE, decimals=2),
    _spec("sleep_duration_min", Domain.PHYSIOLOGICAL, Channel.WEARABLE, decimals=1),
    _spec("sleep_efficiency", Domain.PHYSIOLOGICAL, Channel.WEARABLE),
    _spec("sleep_onset_variability", Domain.PHYSIOLOGICAL, Channel.WEARABLE, decimals=2),
    _spec("daily_steps", Domain.PHYSIOLOGICAL, Channel.WEARABLE, integral=True),
    _spec("spo2_nocturnal_min", Domain.PHYSIOLOGICAL, Channel.WEARABLE, decimals=2),
    # D5 self-report.
    _spec("pss10_total", Domain.SELF_REPORT, Channel.INSTRUMENT, integral=True),
    _spec("phq9_total", Domain.SELF_REPORT, Channel.INSTRUMENT, integral=True),
    _spec("gad7_total", Domain.SELF_REPORT, Channel.INSTRUMENT, integral=True),
    _spec("ema_mood", Domain.SELF_REPORT, Channel.EMA, integral=True),
    _spec("ema_fatigue", Domain.SELF_REPORT, Channel.EMA, integral=True),
    _spec("ema_sleep_quality", Domain.SELF_REPORT, Channel.EMA, integral=True),
    # D6 vocal-acoustic.
    _spec("voice_f0_variability", Domain.VOCAL_ACOUSTIC, Channel.VOICE),
    _spec("voice_speech_rate", Domain.VOCAL_ACOUSTIC, Channel.VOICE),
    _spec("voice_pause_ratio", Domain.VOCAL_ACOUSTIC, Channel.VOICE),
    _spec("voice_jitter_local", Domain.VOCAL_ACOUSTIC, Channel.VOICE, decimals=5),
    _spec("voice_shimmer_local", Domain.VOCAL_ACOUSTIC, Channel.VOICE),
    _spec("voice_loudness_mean", Domain.VOCAL_ACOUSTIC, Channel.VOICE),
    # D7 engagement.
    _spec("checkin_completion_rate_28d", Domain.ENGAGEMENT, Channel.APP),
    _spec("app_session_count_14d", Domain.ENGAGEMENT, Channel.APP, integral=True),
    _spec("instrument_completion_latency_days", Domain.ENGAGEMENT, Channel.APP, decimals=2),
)

INDICATORS: Mapping[str, IndicatorSpec] = MappingProxyType({spec.code: spec for spec in _SPECS})

#: Domains derived from data the force already holds. They need no opt-in, which
#: is why a subject who never enrols is still fully scoreable on three of seven
#: domains — and why declining the wearable cannot make somebody invisible.
OBJECTIVE_DOMAINS: frozenset[Domain] = frozenset(
    {Domain.WORKLOAD, Domain.LEAVE, Domain.ORGANISATIONAL}
)


def codes_for_channel(channel: Channel) -> tuple[str, ...]:
    return tuple(spec.code for spec in _SPECS if spec.channel is channel)


def codes_for_domain(domain: Domain) -> tuple[str, ...]:
    return tuple(spec.code for spec in _SPECS if spec.domain is domain)


def format_value(code: str, value: float) -> float:
    """Round to the indicator's declared precision.

    Rounding at emission rather than at write time is what makes byte-identical
    output achievable: a float that survives a round trip through JSON at four
    decimal places cannot drift between platforms or numpy versions.
    """
    spec = INDICATORS[code]
    return float(round(value)) if spec.integral else round(float(value), spec.decimals)
