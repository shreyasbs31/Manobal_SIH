from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from .core import forecast_authority
from .ruleset import REPO_ROOT

EXCLUDED_ATTRIBUTES = frozenset(
    {
        "gender",
        "home_region",
        "language",
        "religion",
        "caste",
        "free_text",
        "name",
        "service_no",
    }
)
PHRASES_PATH = REPO_ROOT / "infra" / "rulesets" / "phrases.yaml"
ADVERSE_FEATURES = (
    "workload_z",
    "leave_z",
    "hardship_z",
    "body_vitals_z",
    "self_report_z",
    "vocal_acoustics_z",
    "engagement_z",
    "workload_slope_14",
    "body_vitals_slope_14",
    "cusum_max",
    "days_since_onset",
    "incident_exposure",
)


@dataclass
class ForecastModel:
    booster: Any
    calibrator: IsotonicRegression
    conformal_q: float
    feature_names: list[str]
    version: str = "lgbm-v1"


def assert_no_excluded(columns: list[str]) -> None:
    overlap = EXCLUDED_ATTRIBUTES.intersection(columns)
    if overlap:
        raise ValueError(f"Excluded attributes present: {sorted(overlap)}")


def load_phrases() -> dict[str, dict[str, str]]:
    import yaml

    raw = yaml.safe_load(PHRASES_PATH.read_text(encoding="utf-8"))
    return {str(lang): {str(k): str(v) for k, v in body.items()} for lang, body in raw.items()}


def phrase_for(indicator: str, lang: str = "en") -> str:
    phrases = load_phrases()
    table = phrases.get(lang, phrases["en"])
    return table.get(indicator, phrases["en"].get(indicator, indicator.replace("_", " ")))


def train_forecast(
    features: np.ndarray,
    labels: np.ndarray,
    feature_names: list[str],
    *,
    version: str = "lgbm-v1",
) -> ForecastModel:
    assert_no_excluded(feature_names)
    import lightgbm as lgb

    n = features.shape[0]
    split = max(8, int(n * 0.7))
    x_train, x_cal = features[:split], features[split:]
    y_train, y_cal = labels[:split], labels[split:]
    monotone = [1 if name in ADVERSE_FEATURES else 0 for name in feature_names]
    booster = lgb.train(
        {
            "objective": "binary",
            "verbosity": -1,
            "min_data_in_leaf": 1,
            "monotone_constraints": monotone,
        },
        lgb.Dataset(x_train, label=y_train, feature_name=feature_names),
        num_boost_round=40,
    )
    calibrator = IsotonicRegression(out_of_bounds="clip")
    raw_cal = booster.predict(x_cal) if len(x_cal) else booster.predict(x_train)
    y_fit = y_cal if len(x_cal) else y_train
    calibrator.fit(raw_cal, y_fit)
    calibrated = calibrator.predict(raw_cal)
    residuals = np.abs(calibrated - y_fit)
    q = float(np.quantile(residuals, 0.9)) if residuals.size else 0.1
    return ForecastModel(
        booster=booster,
        calibrator=calibrator,
        conformal_q=q,
        feature_names=feature_names,
        version=version,
    )


def predict_interval(model: ForecastModel, row: np.ndarray) -> tuple[float, float, float]:
    raw = float(model.booster.predict(row.reshape(1, -1))[0])
    p = float(model.calibrator.predict([raw])[0])
    lo = max(0.0, p - model.conformal_q)
    hi = min(1.0, p + model.conformal_q)
    return p, lo, hi


def shap_top(
    model: ForecastModel, row: np.ndarray, lang: str = "en", k: int = 3
) -> list[dict[str, str]]:
    contrib = model.booster.predict(row.reshape(1, -1), pred_contrib=True)[0]
    pairs = sorted(
        zip(model.feature_names, contrib[:-1], strict=True),
        key=lambda item: abs(float(item[1])),
        reverse=True,
    )
    return [
        {
            "feature": name,
            "phrase": phrase_for(name.replace("_z", "").replace("_slope_14", ""), lang),
        }
        for name, _value in pairs[:k]
    ]


def metrics(y_true: np.ndarray, y_prob: np.ndarray) -> dict[str, float]:
    y_hat = (y_prob >= 0.5).astype(int)
    out: dict[str, float] = {
        "precision": float(precision_score(y_true, y_hat, zero_division=0)),
        "recall": float(recall_score(y_true, y_hat, zero_division=0)),
        "f1": float(f1_score(y_true, y_hat, zero_division=0)),
        "brier": float(brier_score_loss(y_true, y_prob)),
    }
    if len(np.unique(y_true)) > 1:
        out["auroc"] = float(roc_auc_score(y_true, y_prob))
        out["auprc"] = float(average_precision_score(y_true, y_prob))
    return out


def apply_forecast_to_tier(
    current_tier: str,
    forecast_p: float,
    corroborating: int,
    slope: float,
) -> tuple[str, str]:
    trajectory = "stable"
    if forecast_p >= 0.5 or slope > 0.01:
        trajectory = "rising"
    elif slope < -0.01:
        trajectory = "falling"
    tier = current_tier
    if trajectory == "rising" and current_tier == "T0":
        tier = "T1"
    tier = forecast_authority(tier, trajectory, corroborating)
    return tier, trajectory


REGISTRY: dict[str, dict[str, object]] = {}


def register_world_metrics(world: str, values: dict[str, float], *, version: str) -> None:
    REGISTRY[world] = {"version": version, "metrics": values, "world": world}
