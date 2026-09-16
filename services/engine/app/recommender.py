from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

# Contextual Thompson sampling over toolkit items. Never uses tier, scores, or officer data.
TOOLKIT_IDS = (
    "box_breathing",
    "four_seven_eight",
    "grounding",
    "sleep_wind_down",
    "yoga_nidra",
    "body_scan",
    "post_duty",
    "tactical_nap",
    "heat_cold",
    "anger_cooldown",
    "letter_home",
    "journal",
    "music_decompress",
    "articles",
)

HELPER_BOOST = {
    "music": ("music_decompress", "sleep_wind_down"),
    "talking to someone": ("letter_home", "articles"),
    "prayer or reflection": ("yoga_nidra", "body_scan"),
    "walking": ("post_duty", "grounding"),
    "writing": ("journal", "letter_home"),
    "breathing": ("box_breathing", "four_seven_eight"),
    "sleep": ("sleep_wind_down", "tactical_nap"),
    "sport": ("post_duty", "anger_cooldown"),
}

THEATRE_BOOST = {
    "north": ("heat_cold", "body_scan"),
    "central": ("heat_cold", "tactical_nap"),
    "east": ("letter_home", "yoga_nidra"),
    "capital": ("anger_cooldown", "grounding"),
}


@dataclass
class BanditArm:
    alpha: float = 1.0
    beta: float = 1.0


_ARMS: dict[str, dict[str, BanditArm]] = {}


def _context_key(context: dict[str, Any]) -> str:
    helpers = ",".join(sorted(context.get("helpers") or []))
    return "|".join(
        [
            str(context.get("time_of_day", "day")),
            str(context.get("shift_phase", "rest")),
            str(context.get("theatre", "central")),
            str(context.get("lifecycle_state", "inducted")),
            str(context.get("tags", "")),
            helpers,
        ]
    )


def _priors(item_id: str, context: dict[str, Any]) -> BanditArm:
    alpha = 1.2
    beta = 1.0
    helpers = context.get("helpers") or []
    for helper in helpers:
        if item_id in HELPER_BOOST.get(str(helper), ()):
            alpha += 3.8 if helper == "music" or helper == "sleep" else 1.4
    theatre = str(context.get("theatre", "central"))
    if item_id in THEATRE_BOOST.get(theatre, ()):
        alpha += 1.1
    if context.get("lifecycle_state") == "return_from_leave" and item_id in {
        "grounding",
        "journal",
        "letter_home",
    }:
        alpha += 1.6
    if context.get("shift_phase") == "post_duty" and item_id in {
        "post_duty",
        "sleep_wind_down",
        "tactical_nap",
        "music_decompress",
    }:
        alpha += 1.8
    return BanditArm(alpha=alpha, beta=beta)


def rank_toolkit(context: dict[str, Any], *, seed: int = 7) -> list[str]:
    for forbidden in ("tier", "score", "wsi", "forecast"):
        if forbidden in context:
            raise ValueError("recommender_must_not_use_scoring")
    key = _context_key(context)
    store = _ARMS.setdefault(key, {})
    rng = np.random.default_rng(seed)
    scored: list[tuple[float, str]] = []
    for item_id in TOOLKIT_IDS:
        arm = store.get(item_id) or _priors(item_id, context)
        store[item_id] = arm
        mean = arm.alpha / (arm.alpha + arm.beta)
        jitter = float(rng.normal(0, 0.002))
        scored.append((mean + jitter, item_id))
    scored.sort(reverse=True)
    return [item_id for _, item_id in scored]


def observe_reward(context: dict[str, Any], item_id: str, reward: str) -> None:
    key = _context_key(context)
    store = _ARMS.setdefault(key, {})
    arm = store.get(item_id) or _priors(item_id, context)
    if reward == "helped":
        arm.alpha += 1.6
    elif reward == "completed":
        arm.alpha += 0.4
    elif reward == "not_for_me":
        arm.beta += 1.2
    store[item_id] = arm


def ranking_payload(context: dict[str, Any]) -> dict[str, Any]:
    order = rank_toolkit(context)
    return {
        "order": order,
        "context": {
            "time_of_day": context.get("time_of_day"),
            "shift_phase": context.get("shift_phase"),
            "theatre": context.get("theatre"),
            "lifecycle_state": context.get("lifecycle_state"),
            "helpers": list(context.get("helpers") or []),
            "tags": context.get("tags"),
        },
    }
