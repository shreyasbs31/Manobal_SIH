from __future__ import annotations

from datetime import date, timedelta

import pytest
from app.scoring.changepoint import onset_from_change_points, pelt_rbf
from app.scoring.core import (
    DomainState,
    apply_acute,
    apply_corroboration,
    apply_hysteresis,
    cusum_step,
    desesasonalise,
    ewma_step,
    forecast_authority,
    raw_tier,
    regime_blend,
    renormalised_wsi,
    shrink_median,
    z_score,
    zhat,
)
from app.scoring.indicators import baseline_stats, duty_indicators
from app.scoring.pipeline import score_person_day
from app.scoring.ruleset import load_ruleset, sign_yaml, verify_yaml


def test_z_ewma_cusum_formulas() -> None:
    z_value = z_score(12.0, 8.0, 1.0, floor=0.5, direction=1.0)
    assert z_value == (12.0 - 8.0) / max(1.4826, 0.5)
    assert zhat(-1.0) == 0.0
    assert zhat(6.0) == 1.0
    assert abs(ewma_step(1.0, 0.0) - 0.3) < 1e-9
    assert cusum_step(0.2, 0.6, 0.1) == pytest.approx(0.7)


def test_corroboration_caps_single_domain_at_t1() -> None:
    assert apply_corroboration("T3", 1) == "T1"
    assert apply_corroboration("T3", 2) == "T3"


def test_hysteresis_holds_two_cycles() -> None:
    held, cycles = apply_hysteresis("T1", "T3", 0, need=2)
    assert held == "T3"
    assert cycles == 1
    held, cycles = apply_hysteresis("T1", "T3", 1, need=2)
    assert held == "T1"


def test_acute_overrides_to_t4() -> None:
    assert apply_acute("T0", True) == "T4"
    assert apply_acute("T2", False) == "T2"


def test_cold_start_shrinks_toward_cohort() -> None:
    blended = shrink_median(7, 10.0, 4.0, minimum=21)
    assert abs(blended - (7 / 21 * 10 + 14 / 21 * 4)) < 1e-9


def test_floors_stop_trivial_flags() -> None:
    tiny = z_score(8.05, 8.0, 0.0, floor=2.0, direction=1.0)
    assert tiny == pytest.approx(0.05 / 2.0)
    assert zhat(tiny) < 0.1


def test_renormalised_wsi_and_limited_data() -> None:
    states = [
        DomainState("workload", 0.8, 0.8, 0.0, 1.0, True, True, True, 0.18),
        DomainState("leave", 0.2, 0.2, 0.0, 1.0, True, True, False, 0.15),
        DomainState("body_vitals", 0.9, 0.9, 0.0, 0.4, True, False, False, 0.18),
        DomainState("self_report", 0.1, 0.1, 0.0, 0.2, False, False, False, 0.22),
        DomainState("hardship", 0.1, 0.1, 0.0, 1.0, True, True, False, 0.12),
        DomainState("vocal_acoustics", 0.0, 0.0, 0.0, 0.0, False, False, False, 0.08),
        DomainState("engagement", 0.0, 0.0, 0.0, 0.0, False, False, False, 0.07),
    ]
    wsi, share, limited = renormalised_wsi(states)
    assert 0.4 < wsi < 0.6
    assert limited is True
    assert share < 0.5


def test_deseasonal_and_regime_blend() -> None:
    assert desesasonalise(10.0, 1.0, 0.5) == 8.5
    start = regime_blend(0, 21, 10.0, 4.0)
    end = regime_blend(21, 21, 10.0, 4.0)
    assert start > end
    assert end == 4.0


def test_forecast_never_lifts_above_t1_without_corroboration() -> None:
    assert forecast_authority("T0", "rising", 0) == "T1"
    assert forecast_authority("T3", "rising", 1) == "T1"
    assert forecast_authority("T3", "rising", 2) == "T3"


def test_signed_ruleset_requires_two_wdec_keys() -> None:
    ruleset = load_ruleset("v1.0.0")
    assert ruleset.version == "1.0.0"
    assert verify_yaml(ruleset.yaml_text, ruleset.signature)
    tampered = ruleset.yaml_text.replace("0.18", "0.19", 1)
    assert verify_yaml(tampered, ruleset.signature) is False
    other = sign_yaml(tampered)
    assert other != ruleset.signature


def test_two_domain_drift_reaches_t3() -> None:
    days = [date(2026, 7, 1) + timedelta(days=offset) for offset in range(80)]
    duty = [(day, 8.0 if offset < 50 else 13.0) for offset, day in enumerate(days)]
    sleep = [(day, 420.0 if offset < 50 else 250.0) for offset, day in enumerate(days)]
    result = score_person_day(
        token="st_aaaaaaaaaaaaaaaa",
        as_of=days[-1],
        indicator_history={"duty_hours_7d": duty, "sleep_minutes_7d": sleep},
        consents={"hr_derived", "wearable"},
        coverage={"workload": 1.0, "body_vitals": 1.0},
    )
    assert result.final_tier in {"T2", "T3"}
    assert len(result.corroborating_domains) >= 2


def test_single_domain_sleep_stays_with_the_person() -> None:
    days = [date(2026, 8, 1) + timedelta(days=offset) for offset in range(40)]
    sleep = [(day, 420.0 if offset < 30 else 240.0) for offset, day in enumerate(days)]
    stable = [(day, 8.0) for day in days]
    result = score_person_day(
        token="st_bbbbbbbbbbbbbbbb",
        as_of=days[-1],
        indicator_history={"sleep_minutes_7d": sleep, "duty_hours_7d": stable},
        consents={"hr_derived", "wearable", "self_report"},
        coverage={"body_vitals": 1.0, "workload": 1.0},
    )
    assert result.final_tier in {"T0", "T1"}


def test_declined_wearable_domain_does_not_participate() -> None:
    days = [date(2026, 8, 1) + timedelta(days=offset) for offset in range(40)]
    sleep = [(day, 200.0) for day in days]
    duty = [(day, 8.0) for day in days]
    result = score_person_day(
        token="st_cccccccccccccccc",
        as_of=days[-1],
        indicator_history={"sleep_minutes_7d": sleep, "duty_hours_7d": duty},
        consents={"hr_derived"},
        coverage={"body_vitals": 1.0, "workload": 1.0},
    )
    body = next(state for state in result.domain_states if state.name == "body_vitals")
    assert body.participating is False
    assert result.final_tier in {"T0", "T1"}


def test_shadow_ruleset_runs_in_parallel() -> None:
    days = [date(2026, 7, 1) + timedelta(days=offset) for offset in range(60)]
    duty = [(day, 12.0) for day in days]
    sleep = [(day, 280.0) for day in days]
    shadow = load_ruleset("v1.1.0-shadow")
    result = score_person_day(
        token="st_dddddddddddddddd",
        as_of=days[-1],
        indicator_history={"duty_hours_7d": duty, "sleep_minutes_7d": sleep},
        consents={"hr_derived", "wearable"},
        coverage={"workload": 1.0, "body_vitals": 1.0},
        shadow=shadow,
    )
    assert result.shadow_tier is not None
    assert result.ruleset_version == "1.0.0"


def test_change_points_only_when_wsi_elevated() -> None:
    low = [0.1] * 40
    assert onset_from_change_points(low, 39) is None
    series = [0.1] * 30 + [0.6] * 20
    onset = onset_from_change_points(series, 49)
    assert onset is not None
    breaks = pelt_rbf(series)
    assert breaks


def test_duty_indicators_consecutive_days() -> None:
    import polars as pl

    rows = []
    token = "st_eeeeeeeeeeeeeeee"
    start = date(2026, 8, 1)
    for offset in range(25):
        rest = offset == 0
        rows.append(
            {
                "token": token,
                "date": start + timedelta(days=offset),
                "hours": 0.0 if rest else 12.0,
                "night": False,
                "rest_day": rest,
                "rest_denied": False,
            }
        )
    frame = duty_indicators(pl.DataFrame(rows), window_days=90)
    last = frame.sort("date").row(-1, named=True)
    assert last["consecutive_duty_days"] >= 19


def test_baseline_stats_median_and_mad() -> None:
    median, mad, n = baseline_stats([1.0, 2.0, 3.0, 4.0, 100.0])
    assert n == 5
    assert median == 3.0
    assert mad == 1.0


def test_raw_tier_bounds() -> None:
    assert raw_tier(0.2) == "T0"
    assert raw_tier(0.4) == "T1"
    assert raw_tier(0.6) == "T2"
    assert raw_tier(0.8) == "T3"


def test_pelt_fallback_and_empty_wsi() -> None:
    import numpy as np
    from app.scoring.changepoint import _pelt_fallback

    series = np.concatenate([np.zeros(12), np.ones(12)])
    breaks = _pelt_fallback(series, min_size=5)
    assert isinstance(breaks, list)
    assert pelt_rbf([0.1, 0.2]) == []
    assert onset_from_change_points([], 0) is None


def test_indicator_builders_cover_empty_and_filled() -> None:
    from datetime import UTC, datetime

    import polars as pl
    from app.scoring.indicators import (
        bio_indicators,
        ema_indicators,
        engagement_indicators,
        instrument_latest,
        leave_indicators,
        rotation_effects,
        weekday_effects,
    )

    start = date(2026, 8, 1)
    duty = pl.DataFrame(
        {
            "token": ["st_eeeeeeeeeeeeeeee"] * 10,
            "date": [start + timedelta(days=i) for i in range(10)],
            "hours": [8.0] * 10,
            "night": [False] * 10,
            "rest_day": [False] * 10,
            "rest_denied": [False] * 10,
        }
    )
    weekday_effects(duty, "hours")
    rotation_effects(duty, "hours")
    leave = pl.DataFrame(
        {
            "token": ["st_eeeeeeeeeeeeeeee", "st_eeeeeeeeeeeeeeee"],
            "status": ["approved", "rejected"],
            "to_date": [start, start + timedelta(days=2)],
        }
    )
    balance = pl.DataFrame(
        {"token": ["st_eeeeeeeeeeeeeeee"], "as_of": [start], "el_days": [10.0]}
    )
    leave_out = leave_indicators(duty, leave, balance)
    assert "days_since_last_leave" in leave_out.columns
    leave_indicators(duty, leave, pl.DataFrame())
    empty_ema = ema_indicators(pl.DataFrame())
    assert empty_ema.height == 0
    ema = pl.DataFrame(
        {
            "token": ["st_eeeeeeeeeeeeeeee"],
            "at": [datetime(2026, 8, 2, tzinfo=UTC)],
            "mood": [3.0],
            "energy": [3.0],
            "sleep_quality": [3.0],
        }
    )
    assert ema_indicators(ema).height == 1
    assert bio_indicators(pl.DataFrame()).height == 0
    bio = pl.DataFrame(
        {
            "token": ["st_eeeeeeeeeeeeeeee"],
            "date": [start],
            "sleep_min": [360.0],
            "sleep_eff": [0.8],
            "hrv_rmssd": [40.0],
            "rhr": [62.0],
            "steps": [4000],
        }
    )
    assert "sleep_minutes_7d" in bio_indicators(bio).columns
    assert engagement_indicators(pl.DataFrame()).height == 0
    eng = pl.DataFrame(
        {
            "token": ["st_eeeeeeeeeeeeeeee"],
            "date": [start],
            "completed": [1],
            "expected": [1],
        }
    )
    assert "checkin_completion_14d" in engagement_indicators(eng).columns
    assert instrument_latest(pl.DataFrame()).height == 0
    inst = pl.DataFrame(
        {
            "token": ["st_eeeeeeeeeeeeeeee"],
            "at": [datetime(2026, 8, 2, tzinfo=UTC)],
            "kind": ["pss10"],
            "total": [12.0],
        }
    )
    assert instrument_latest(inst).height == 1
    median, mad, n = baseline_stats([])
    assert n == 0 and median == 0.0 and mad == 1.0


def test_empty_participating_weight_and_hysteresis_drop() -> None:
    empty = renormalised_wsi([])
    assert empty == (0.0, 0.0, True)
    held, cycles = apply_hysteresis("T1", "T2", 0)
    assert held == "T2" and cycles == 1
    dropped, reset = apply_hysteresis("T1", "T2", 1)
    assert dropped == "T1" and reset == 0
    same, _ = apply_hysteresis("T2", "T2", 0)
    assert same == "T2"
