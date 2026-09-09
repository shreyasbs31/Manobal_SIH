"""The causal chain, written out as one directed graph.

This function is the requirement in Appendix A.3 made literal. Read top to
bottom and the arrows are the assignments:

    deployment pressure + injected strain
        -> workload      (D1)  duty hours, rest denial, roster volatility
        -> physiology    (D4)  sleep, then HRV / resting HR / steps
        -> self-report   (D5)  affect, then instruments and check-ins
        -> voice         (D6)  prosody
        -> leave         (D2)  leave-seeking, burstiness, absence
        -> organisational(D3)  transfer, swap, withdrawal
        -> engagement    (D7)  check-in and app decline

No stage receives an argument produced below it. The one apparent exception is
the last two lines, where the engagement stage's completion mask is used to
decide which days have D5 check-in *rows*. That is availability, not value: the
mood a subject would have reported was already fixed by the affect latent, and
what engagement decides is only whether they bothered to report it. Keeping the
two apart is what stops the withdrawal coupling from becoming a feedback loop
that would make the injected ground truth impossible to state.

The correlations the risk engine's corroboration gate depends on are therefore
*consequences* of this graph rather than parameters of it. Nobody here writes
"make D1 and D4 correlate at -0.6"; sleep is a function of the trailing week of
duty, and the correlation is whatever that implies.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from .arrays import BoolArray, FloatArray
from .cohorts import Cohort
from .config import GenerationConfig
from .indicators import INDICATORS, Channel
from .missingness import SubjectMissingness, subject_missingness
from .person import PersonModel
from .population import Subject, Unit
from .rng import substream
from .stages.deployment import Exogenous, exogenous_drivers
from .stages.engagement import engagement_stage
from .stages.leave import leave_stage
from .stages.organisational import organisational_stage
from .stages.physiology import physiology_stage
from .stages.self_report import self_report_stage
from .stages.voice import voice_stage
from .stages.workload import workload_stage


@dataclass(frozen=True, slots=True)
class SubjectSeries:
    """One subject's complete generated history, before consent filtering."""

    subject_token: str
    #: Indicator code -> daily values over the whole run.
    indicators: Mapping[str, FloatArray]
    #: Indicator code -> whether a row exists for that day, from cadence and
    #: missingness together. Consent is applied later, per domain.
    available: Mapping[str, BoolArray]
    #: Named latents, kept for the causal-correlation and calibration tests.
    #: Never written to any output file — they are not data the platform could
    #: ever have.
    latents: Mapping[str, FloatArray]
    exogenous: Exogenous
    missingness: SubjectMissingness


def generate_subject_series(
    config: GenerationConfig,
    subject: Subject,
    person: PersonModel,
    unit: Unit,
    cohort: Cohort,
    incident_pressure: FloatArray,
    hrms_outages: BoolArray,
) -> SubjectSeries:
    """Run the whole chain for one subject."""
    n_days = config.duration_days
    strain = cohort.strain(n_days)

    exogenous = exogenous_drivers(
        substream(config.seed, "exogenous", subject.index),
        n_days,
        unit,
        config.deployment_model,
        incident_pressure,
    )
    workload = workload_stage(
        substream(config.seed, "workload", subject.index),
        person,
        exogenous,
        strain,
    )
    missing = subject_missingness(
        config, person, hrms_outages, exogenous.planned_leave, workload.rest_day
    )
    physiology = physiology_stage(
        substream(config.seed, "physiology", subject.index),
        person,
        workload.strain,
        strain,
        workload.rest_day,
        missing.wearable_worn,
    )
    self_report = self_report_stage(
        substream(config.seed, "self_report", subject.index),
        person,
        workload.strain,
        physiology.recovery_deficit,
        physiology.sleep_debt,
        strain,
        gaming=cohort.gaming,
    )
    voice = voice_stage(
        substream(config.seed, "voice", subject.index),
        person,
        self_report.affect,
        physiology.recovery_deficit,
        gaming=cohort.gaming,
    )
    leave = leave_stage(
        substream(config.seed, "leave", subject.index),
        person,
        self_report.affect,
        workload.strain,
        strain,
        incident_pressure,
    )
    organisational = organisational_stage(
        substream(config.seed, "organisational", subject.index),
        person,
        self_report.affect,
        leave.leave_seeking,
        strain,
        exogenous.intensity_weight,
        exogenous.non_family_station,
    )
    engagement = engagement_stage(
        substream(config.seed, "engagement", subject.index),
        person,
        self_report.affect,
        organisational.org_churn,
        strain,
        self_report.instrument_days,
        gaming=cohort.gaming,
    )

    indicators: dict[str, FloatArray] = {}
    for stage in (workload, physiology, self_report, voice, leave, organisational, engagement):
        indicators.update(stage.indicators)

    available = _availability(
        n_days=n_days,
        missing=missing,
        instrument_days=self_report.instrument_days,
        voice_days=voice.checkin_days,
        checkin_completed=engagement.checkin_completed,
    )
    latents = MappingProxyType(
        {
            "distress_strain": strain,
            "deployment_pressure": exogenous.pressure,
            "workload_strain": workload.strain,
            "sleep_debt": physiology.sleep_debt,
            "recovery_deficit": physiology.recovery_deficit,
            "affect": self_report.affect,
            "leave_seeking": leave.leave_seeking,
            "org_churn": organisational.org_churn,
        }
    )
    return SubjectSeries(
        subject_token=subject.subject_token,
        indicators=MappingProxyType(indicators),
        available=MappingProxyType(available),
        latents=latents,
        exogenous=exogenous,
        missingness=missing,
    )


def _availability(
    *,
    n_days: int,
    missing: SubjectMissingness,
    instrument_days: BoolArray,
    voice_days: BoolArray,
    checkin_completed: BoolArray,
) -> dict[str, BoolArray]:
    """Which days carry a row, per channel.

    The instrument channel is available from the first *answered* administration
    onwards, because a carried-forward value needs something to carry. Missing a
    later administration does not remove the row — it staleness the value, which
    is the SDD §4.5 ``current_value_max_age_days`` path rather than the coverage
    path, and the two must not be conflated.
    """
    answered = instrument_days & missing.instrument_answered
    instrument_available = _from_first_true(answered)

    by_channel: dict[Channel, BoolArray] = {
        Channel.HRMS: missing.hrms_present,
        Channel.WEARABLE: missing.wearable_worn,
        Channel.INSTRUMENT: instrument_available,
        Channel.EMA: checkin_completed,
        Channel.VOICE: voice_days & missing.voice_recorded,
        Channel.APP: _all_days(n_days),
    }
    return {code: by_channel[spec.channel] for code, spec in INDICATORS.items()}


def _from_first_true(flags: BoolArray) -> BoolArray:
    import numpy as np

    if not flags.any():
        return np.zeros(len(flags), dtype=bool)
    first = int(np.argmax(flags))
    mask = np.zeros(len(flags), dtype=bool)
    mask[first:] = True
    return mask


def _all_days(n_days: int) -> BoolArray:
    import numpy as np

    return np.ones(n_days, dtype=bool)
