from __future__ import annotations

from datetime import timedelta

import polars as pl

INDICATOR_DIRECTION: dict[str, float] = {
    "duty_hours_7d": 1.0,
    "duty_hours_28d": 1.0,
    "consecutive_duty_days": 1.0,
    "night_shift_ratio_28d": 1.0,
    "roster_volatility_28d": 1.0,
    "rest_denials_28d": 1.0,
    "quick_returns_14d": 1.0,
    "days_since_last_leave": 1.0,
    "leave_rejections_90d": 1.0,
    "short_leave_fano_28d": 1.0,
    "leave_apply_rate_delta": 1.0,
    "unplanned_absence_28d": 1.0,
    "el_balance_unused_ratio": 1.0,
    "family_separation_days": 1.0,
    "hard_area_days_365": 1.0,
    "climate_hardship_days_90": 1.0,
    "incident_exposure_30d": 1.0,
    "transfer_requests_180d": 1.0,
    "duty_swap_rate_delta": 1.0,
    "grievance_open_age_max": 1.0,
    "sleep_minutes_7d": -1.0,
    "sleep_efficiency_7d": -1.0,
    "sleep_midpoint_variability_14d": 1.0,
    "hrv_rmssd_7d": -1.0,
    "resting_hr_7d": 1.0,
    "activity_delta": 1.0,
    "ema_mood_7d": -1.0,
    "ema_energy_7d": -1.0,
    "ema_sleep_q_7d": -1.0,
    "pss10": 1.0,
    "cbi_personal": 1.0,
    "cbi_work": 1.0,
    "who5": -1.0,
    "phq9": 1.0,
    "gad7": 1.0,
    "voice_mahalanobis": 1.0,
    "checkin_completion_14d": -1.0,
    "response_latency_delta": 1.0,
}

DOMAIN_INDICATORS: dict[str, tuple[str, ...]] = {
    "workload": (
        "duty_hours_7d",
        "duty_hours_28d",
        "consecutive_duty_days",
        "night_shift_ratio_28d",
        "roster_volatility_28d",
        "rest_denials_28d",
        "quick_returns_14d",
    ),
    "leave": (
        "days_since_last_leave",
        "leave_rejections_90d",
        "short_leave_fano_28d",
        "leave_apply_rate_delta",
        "unplanned_absence_28d",
        "el_balance_unused_ratio",
    ),
    "hardship": (
        "family_separation_days",
        "hard_area_days_365",
        "climate_hardship_days_90",
        "incident_exposure_30d",
        "transfer_requests_180d",
        "duty_swap_rate_delta",
        "grievance_open_age_max",
    ),
    "body_vitals": (
        "sleep_minutes_7d",
        "sleep_efficiency_7d",
        "sleep_midpoint_variability_14d",
        "hrv_rmssd_7d",
        "resting_hr_7d",
        "activity_delta",
    ),
    "self_report": (
        "ema_mood_7d",
        "ema_energy_7d",
        "ema_sleep_q_7d",
        "pss10",
        "cbi_personal",
        "who5",
        "phq9",
        "gad7",
    ),
    "vocal_acoustics": ("voice_mahalanobis",),
    "engagement": ("checkin_completion_14d", "response_latency_delta"),
}


def weekday_effects(values: pl.DataFrame, column: str) -> pl.DataFrame:
    dated = values.with_columns(pl.col("date").dt.weekday().alias("weekday"))
    return dated.group_by(["token", "weekday"]).agg(pl.col(column).median().alias("weekday_median"))


def rotation_effects(values: pl.DataFrame, column: str) -> pl.DataFrame:
    dated = values.with_columns((pl.col("date").dt.ordinal_day() % 28).alias("phase"))
    return dated.group_by(["token", "phase"]).agg(pl.col(column).median().alias("phase_median"))


def duty_indicators(duty: pl.DataFrame, window_days: int = 90) -> pl.DataFrame:
    ordered = duty.sort(["token", "date"]).with_columns(
        pl.when(pl.col("rest_day")).then(0).otherwise(1).alias("on_duty"),
        pl.col("hours").cast(pl.Float64),
        pl.col("night").cast(pl.Int8),
        pl.col("rest_denied").cast(pl.Int8),
    )
    cutoff = ordered.select(pl.col("date").max()).item()
    if cutoff is not None:
        ordered = ordered.filter(pl.col("date") >= cutoff - timedelta(days=window_days))
    reset = (
        pl.when(pl.col("on_duty") == 0)
        .then(pl.col("on_duty").cum_sum().over("token"))
        .otherwise(None)
        .forward_fill()
        .over("token")
        .fill_null(0)
    )
    consecutive = (pl.col("on_duty").cum_sum().over("token") - reset) * pl.col("on_duty")
    prev_end = pl.col("date").shift(1).over("token") + pl.duration(
        hours=pl.col("hours").shift(1).over("token")
    )
    quick = ((pl.col("date") + pl.duration(hours=6) - prev_end).dt.total_hours() < 11) & (
        pl.col("on_duty") == 1
    )
    return ordered.with_columns(
        consecutive.alias("consecutive_duty_days"),
        pl.col("hours")
        .rolling_sum(window_size=7, min_samples=1)
        .over("token")
        .alias("duty_hours_7d"),
        pl.col("hours")
        .rolling_sum(window_size=28, min_samples=1)
        .over("token")
        .alias("duty_hours_28d"),
        pl.col("night")
        .rolling_mean(window_size=28, min_samples=1)
        .over("token")
        .alias("night_shift_ratio_28d"),
        pl.col("hours")
        .rolling_std(window_size=28, min_samples=2)
        .over("token")
        .fill_null(0)
        .alias("roster_volatility_28d"),
        pl.col("rest_denied")
        .rolling_sum(window_size=28, min_samples=1)
        .over("token")
        .alias("rest_denials_28d"),
        quick.cast(pl.Int8)
        .rolling_sum(window_size=14, min_samples=1)
        .over("token")
        .alias("quick_returns_14d"),
    )


def leave_indicators(
    duty: pl.DataFrame,
    leave_event: pl.DataFrame,
    leave_balance: pl.DataFrame,
) -> pl.DataFrame:
    last_approved = (
        leave_event.filter(pl.col("status") == "approved")
        .group_by("token")
        .agg(pl.col("to_date").max().alias("last_leave"))
    )
    rejections = (
        leave_event.filter(pl.col("status") == "rejected")
        .group_by("token")
        .agg(pl.len().alias("leave_rejections_90d"))
    )
    latest = duty.select(["token", "date"]).unique(subset=["token"], keep="last")
    out = latest.join(last_approved, on="token", how="left").join(
        rejections, on="token", how="left"
    )
    out = out.with_columns(
        (pl.col("date") - pl.col("last_leave"))
        .dt.total_days()
        .fill_null(180)
        .alias("days_since_last_leave"),
        pl.col("leave_rejections_90d").fill_null(0),
        pl.lit(0.0).alias("short_leave_fano_28d"),
        pl.lit(0.0).alias("leave_apply_rate_delta"),
        pl.lit(0.0).alias("unplanned_absence_28d"),
    )
    if leave_balance.height:
        bal = leave_balance.sort("as_of").unique(subset=["token"], keep="last")
        out = out.join(bal.select(["token", "el_days"]), on="token", how="left").with_columns(
            (pl.col("el_days").fill_null(12) / 30.0).alias("el_balance_unused_ratio")
        )
    else:
        out = out.with_columns(pl.lit(0.4).alias("el_balance_unused_ratio"))
    return out


def ema_indicators(ema: pl.DataFrame) -> pl.DataFrame:
    if ema.height == 0:
        return pl.DataFrame(schema={"token": pl.String, "date": pl.Date, "ema_mood_7d": pl.Float64})
    dated = ema.sort(["token", "at"]).with_columns(pl.col("at").dt.date().alias("date"))
    return (
        dated.group_by(["token", "date"])
        .agg(
            pl.col("mood").mean().alias("mood"),
            pl.col("energy").mean().alias("energy"),
            pl.col("sleep_quality").mean().alias("sleep_q"),
        )
        .sort(["token", "date"])
        .with_columns(
            pl.col("mood")
            .rolling_mean(window_size=7, min_samples=1)
            .over("token")
            .alias("ema_mood_7d"),
            pl.col("energy")
            .rolling_mean(window_size=7, min_samples=1)
            .over("token")
            .alias("ema_energy_7d"),
            pl.col("sleep_q")
            .rolling_mean(window_size=7, min_samples=1)
            .over("token")
            .alias("ema_sleep_q_7d"),
        )
    )


def bio_indicators(bio: pl.DataFrame) -> pl.DataFrame:
    if bio.height == 0:
        return pl.DataFrame(
            schema={"token": pl.String, "date": pl.Date, "sleep_minutes_7d": pl.Float64}
        )
    return bio.sort(["token", "date"]).with_columns(
        pl.col("sleep_min")
        .rolling_mean(window_size=7, min_samples=1)
        .over("token")
        .alias("sleep_minutes_7d"),
        pl.col("sleep_eff")
        .rolling_mean(window_size=7, min_samples=1)
        .over("token")
        .alias("sleep_efficiency_7d"),
        pl.col("hrv_rmssd")
        .rolling_mean(window_size=7, min_samples=1)
        .over("token")
        .alias("hrv_rmssd_7d"),
        pl.col("rhr")
        .rolling_mean(window_size=7, min_samples=1)
        .over("token")
        .alias("resting_hr_7d"),
        pl.col("sleep_min")
        .rolling_std(window_size=14, min_samples=2)
        .over("token")
        .fill_null(0)
        .alias("sleep_midpoint_variability_14d"),
        pl.col("steps").diff().abs().over("token").fill_null(0).alias("activity_delta"),
    )


def engagement_indicators(engagement: pl.DataFrame) -> pl.DataFrame:
    if engagement.height == 0:
        return pl.DataFrame(
            schema={"token": pl.String, "date": pl.Date, "checkin_completion_14d": pl.Float64}
        )
    return engagement.sort(["token", "date"]).with_columns(
        (
            pl.col("completed").rolling_sum(window_size=14, min_samples=1).over("token")
            / pl.col("expected").rolling_sum(window_size=14, min_samples=1).over("token").clip(1)
        ).alias("checkin_completion_14d"),
        pl.lit(0.0).alias("response_latency_delta"),
    )


def instrument_latest(instrument: pl.DataFrame) -> pl.DataFrame:
    if instrument.height == 0:
        return pl.DataFrame(schema={"token": pl.String, "date": pl.Date})
    dated = instrument.with_columns(pl.col("at").dt.date().alias("date"))
    wide = dated.pivot(
        values="total", index=["token", "date"], on="kind", aggregate_function="last"
    )
    return wide


def baseline_stats(series: list[float], minimum: int = 21) -> tuple[float, float, int]:
    ordered = sorted(value for value in series if value is not None)
    n = len(ordered)
    if n == 0:
        return 0.0, 1.0, 0
    mid = n // 2
    median = ordered[mid] if n % 2 else 0.5 * (ordered[mid - 1] + ordered[mid])
    deviations = sorted(abs(value - median) for value in ordered)
    mad = deviations[mid] if n % 2 else 0.5 * (deviations[mid - 1] + deviations[mid])
    return float(median), float(mad), n
