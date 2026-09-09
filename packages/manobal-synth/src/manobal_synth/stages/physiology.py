"""Stage 2 — D4 physiological: sleep first, then autonomic response to it.

Two links, in order, because the physiology runs in that order. Workload costs
sleep; lost sleep and sustained load together suppress HRV, raise resting heart
rate and flatten activity. HRV is not driven by workload directly anywhere in
this module — it is driven by the sleep debt that workload produced — which is
what makes the D1/D4 correlation the causal test looks for a *derived* property
rather than an asserted one.

Everything responds through the subject's own ``reactivity`` trait. Two people on
an identical roster do not lose the same amount of sleep, and the corroboration
gate has to cope with a subject whose body says less than their diary says.

Sleep responds to the *trailing week* of duty, not to today's shift. The lag is
what stops the generated data from looking simultaneous, and it is why the
Spearman correlation the causal test measures is strong but not degenerate.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..arrays import BoolArray, FloatArray
from ..person import PersonModel
from ..processes import graded_response
from ..windows import lagged_smooth, masked_rolling_std

#: Sleep integrates the week behind it; the autonomic system integrates the
#: fortnight behind that. Both windows are trailing.
_SLEEP_LAG_DAYS = 7
_AUTONOMIC_LAG_DAYS = 14
_ONSET_VARIABILITY_WINDOW = 14

#: Minutes of sleep lost per unit of workload strain, and the recovery on a rest
#: day. A rest-day lie-in is not decoration: it is what makes rest denial cost
#: sleep as well as hours, so two D1 indicators reach D4 by different routes.
_SLEEP_MINUTES_PER_STRAIN = 80.0
_REST_DAY_SLEEP_BONUS = 16.0
#: Rostered leave is modelled as its own effect rather than as a large negative
#: workload deviation, so that a fortnight at home does not read as the inverse
#: of a fortnight of overwork.
_LEAVE_SLEEP_BONUS = 30.0

_SLEEP_EFFICIENCY_PER_STRAIN = 0.075
#: Bedtime drifts later and, more importantly, becomes less predictable. The
#: dispersion inflation is what ``sleep_onset_variability`` picks up.
_SLEEP_ONSET_SHIFT_HOURS = 0.80
_SLEEP_ONSET_DISPERSION_GAIN = 1.25
#: A fortnight's bedtime standard deviation of two and a half hours is already a
#: completely shattered sleep schedule; beyond that the statistic stops
#: discriminating and only inflates the domain's robust dispersion.
_MAX_ONSET_VARIABILITY_MINUTES = 150.0

#: Relative sleep deficit that counts as one unit of sleep debt, so that debt is
#: comparable across subjects with very different sleep baselines.
_SLEEP_DEBT_SCALE = 0.10

#: Weights of the autonomic load's three parents. Sleep debt leads, sustained
#: load follows, and a direct term carries the part of distress that is not
#: mediated by duty at all — grief, debt, a sick parent at home.
_DEBT_TO_AUTONOMIC = 0.62
_LOAD_TO_AUTONOMIC = 0.42
_DISTRESS_TO_AUTONOMIC = 0.70

#: Proportional HRV suppression per unit of autonomic load. Suppressed RMSSD is
#: the most-replicated wearable stress marker and the effect in chronic stress
#: cohorts is large, which is why it carries the highest weight in D4.
_HRV_SUPPRESSION = 0.135
_RESTING_HR_RISE = 4.6
_STEPS_SUPPRESSION = 0.165
#: Deliberately small. Nocturnal SpO2 in CAPF postings is dominated by altitude,
#: not by affect, and the ruleset weights it at 0.5 for exactly that reason.
_SPO2_DROP = 0.45

_SLEEP_MIN_MINUTES = 90.0
_SLEEP_MAX_MINUTES = 720.0

#: Workload deviation a subject absorbs without measurable physiological cost.
#: In the units of ``workload.py`` this is roughly a ten-percent swing in weekly
#: hours — an ordinary fortnight. See ``processes.graded_response`` for why a
#: linear transfer here would make the whole corpus untestable.
_WORKLOAD_TOLERANCE = 1.90
#: Relief saturates: a light fortnight buys back rest, not an unbounded amount
#: of it.
_RELIEF_FLOOR = -0.50


@dataclass(frozen=True, slots=True)
class PhysiologyStage:
    indicators: dict[str, FloatArray]
    #: Chronic recovery deficit. The parent of the affect stage.
    recovery_deficit: FloatArray
    sleep_debt: FloatArray


def physiology_stage(
    rng: np.random.Generator,
    person: PersonModel,
    workload_strain: FloatArray,
    distress_strain: FloatArray,
    rest_day: BoolArray,
    on_leave: BoolArray,
    worn: BoolArray,
) -> PhysiologyStage:
    """Generate sleep, then the autonomic and activity response to it."""
    reactivity = person.trait("reactivity")
    sleep_pressure = reactivity * graded_response(
        lagged_smooth(workload_strain, _SLEEP_LAG_DAYS),
        tolerance=_WORKLOAD_TOLERANCE,
        floor=_RELIEF_FLOOR,
    )

    sleep_duration = _sleep_duration(rng, person, sleep_pressure, rest_day, on_leave)
    sleep_debt = (person.trait("sleep_duration_mean") - sleep_duration) / (
        person.trait("sleep_duration_mean") * _SLEEP_DEBT_SCALE
    )
    chronic_debt = lagged_smooth(sleep_debt, _AUTONOMIC_LAG_DAYS)
    autonomic_load = (
        _DEBT_TO_AUTONOMIC * chronic_debt
        + _LOAD_TO_AUTONOMIC * lagged_smooth(sleep_pressure, _AUTONOMIC_LAG_DAYS)
        + _DISTRESS_TO_AUTONOMIC * reactivity * distress_strain
    )

    indicators = {
        "sleep_duration_min": sleep_duration,
        "sleep_efficiency": _sleep_efficiency(rng, person, sleep_pressure),
        "sleep_onset_variability": _onset_variability(rng, person, sleep_pressure, worn),
        "hrv_rmssd_nightly": _hrv(rng, person, autonomic_load),
        "resting_hr_nightly": _resting_hr(rng, person, autonomic_load),
        "daily_steps": _steps(rng, person, autonomic_load),
        "spo2_nocturnal_min": _spo2(rng, person, autonomic_load),
    }
    return PhysiologyStage(
        indicators=indicators,
        recovery_deficit=0.5 * chronic_debt + 0.5 * autonomic_load,
        sleep_debt=sleep_debt,
    )


def _sleep_duration(
    rng: np.random.Generator,
    person: PersonModel,
    sleep_pressure: FloatArray,
    rest_day: BoolArray,
    on_leave: BoolArray,
) -> FloatArray:
    minutes = (
        person.trait("sleep_duration_mean")
        - _SLEEP_MINUTES_PER_STRAIN * sleep_pressure
        + _REST_DAY_SLEEP_BONUS * rest_day
        + _LEAVE_SLEEP_BONUS * on_leave
        + rng.normal(0.0, person.trait("sleep_duration_sd"), size=len(sleep_pressure))
    )
    bounded: FloatArray = np.clip(minutes, _SLEEP_MIN_MINUTES, _SLEEP_MAX_MINUTES)
    return bounded


def _sleep_efficiency(
    rng: np.random.Generator,
    person: PersonModel,
    sleep_pressure: FloatArray,
) -> FloatArray:
    values = (
        person.trait("sleep_efficiency_mean")
        - _SLEEP_EFFICIENCY_PER_STRAIN * sleep_pressure
        + rng.normal(0.0, person.trait("sleep_efficiency_sd"), size=len(sleep_pressure))
    )
    return np.clip(values, 0.35, 0.995)


def _onset_variability(
    rng: np.random.Generator,
    person: PersonModel,
    sleep_pressure: FloatArray,
    worn: BoolArray,
) -> FloatArray:
    """Fourteen-day dispersion of bedtime, in minutes.

    Derived from a nightly onset series rather than sampled directly, so that the
    indicator really is the dispersion of the nights the wearable saw. Nights
    lost to non-wear therefore widen or narrow it, which is the coupling between
    D4 coverage and D4 values that a directly-sampled indicator would miss.
    """
    dispersion = person.trait("sleep_onset_sd") * np.maximum(
        1.0 + _SLEEP_ONSET_DISPERSION_GAIN * sleep_pressure, 0.2
    )
    onset_hours = (
        person.trait("sleep_onset_mean")
        + _SLEEP_ONSET_SHIFT_HOURS * sleep_pressure
        + dispersion * rng.normal(0.0, 1.0, size=len(sleep_pressure))
    )
    spread_minutes = masked_rolling_std(onset_hours * 60.0, worn, _ONSET_VARIABILITY_WINDOW)
    return np.minimum(spread_minutes, _MAX_ONSET_VARIABILITY_MINUTES)


def _hrv(rng: np.random.Generator, person: PersonModel, autonomic_load: FloatArray) -> FloatArray:
    values = person.trait("hrv_rmssd_mean") * (
        1.0 - _HRV_SUPPRESSION * autonomic_load
    ) + rng.normal(0.0, person.trait("hrv_rmssd_sd"), size=len(autonomic_load))
    return np.clip(values, 4.0, 200.0)


def _resting_hr(
    rng: np.random.Generator,
    person: PersonModel,
    autonomic_load: FloatArray,
) -> FloatArray:
    values = (
        person.trait("resting_hr_mean")
        + _RESTING_HR_RISE * autonomic_load
        + rng.normal(0.0, person.trait("resting_hr_sd"), size=len(autonomic_load))
    )
    return np.clip(values, 35.0, 110.0)


def _steps(rng: np.random.Generator, person: PersonModel, autonomic_load: FloatArray) -> FloatArray:
    values = person.trait("daily_steps_mean") * (
        1.0 - _STEPS_SUPPRESSION * autonomic_load
    ) + rng.normal(0.0, person.trait("daily_steps_sd"), size=len(autonomic_load))
    return np.clip(values, 200.0, 40000.0)


def _spo2(rng: np.random.Generator, person: PersonModel, autonomic_load: FloatArray) -> FloatArray:
    values = (
        person.trait("spo2_min_mean")
        - _SPO2_DROP * autonomic_load
        + rng.normal(0.0, person.trait("spo2_min_sd"), size=len(autonomic_load))
    )
    return np.clip(values, 78.0, 100.0)
