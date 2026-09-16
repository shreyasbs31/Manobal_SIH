from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from .scoring.ruleset import REPO_ROOT

LEVER_PATH = REPO_ROOT / "infra" / "rulesets" / "interventions.yaml"

TIER_SCORE = {"T0": 0, "T1": 1, "T2": 2, "T3": 3, "T4": 4}


@dataclass(frozen=True)
class Lever:
    code: str
    label: str
    owner: str
    domains: tuple[str, ...]


def load_levers() -> list[Lever]:
    raw = yaml.safe_load(Path(LEVER_PATH).read_text(encoding="utf-8"))
    return [
        Lever(
            code=str(item["code"]),
            label=str(item["label"]),
            owner=str(item["owner"]),
            domains=tuple(item.get("domains") or ()),
        )
        for item in raw["levers"]
    ]


def rank_levers(
    *,
    tier: str,
    dominant_domains: list[str],
    lifecycle_state: str,
    deesc_rate: dict[str, float] | None = None,
    operation: bool = False,
    below_strength: bool = False,
) -> list[Lever]:
    rates = deesc_rate or {}
    ranked: list[tuple[float, Lever]] = []
    for lever in load_levers():
        score = 0.15
        if lever.code == "NO_ACTION":
            score = 0.05
        overlap = len(set(lever.domains).intersection(dominant_domains))
        score += 0.35 * overlap
        score += 0.12 * TIER_SCORE.get(tier, 0)
        if lifecycle_state == "return_from_leave" and lever.code == "REINTEGRATION_CHAT":
            score += 0.4
        if "leave" in dominant_domains and lever.code in {
            "LEAVE_PRIORITISE",
            "LEAVE_SHORT_FAMILY",
            "FAMILY_CONNECT",
        }:
            score += 0.35
        if "hardship" in dominant_domains and lever.code in {
            "GRIEVANCE_EXPEDITE",
            "LEGAL_AID_REFERRAL",
        }:
            score += 0.4
        if "workload" in dominant_domains and lever.code == "REST_48H":
            score += 0.45
        if operation and lever.code in {"REST_48H", "LEAVE_PRIORITISE"} and below_strength:
            score -= 0.5
        score += 0.2 * rates.get(lever.code, 0.0)
        ranked.append((score, lever))
    ranked.sort(key=lambda item: item[0], reverse=True)
    ordered = [lever for _score, lever in ranked]
    no_action = next(lever for lever in ordered if lever.code == "NO_ACTION")
    without = [lever for lever in ordered if lever.code != "NO_ACTION"]
    return without + [no_action]


OUTCOMES: list[dict[str, str]] = []
WEEKLY_RATES: dict[str, float] = {}


def record_decision(case_id: str, lever: str, outcome: str | None = None) -> None:
    OUTCOMES.append({"case_id": case_id, "lever": lever, "outcome": outcome or "open"})


def weekly_rerank() -> dict[str, float]:
    totals: dict[str, list[int]] = {}
    for row in OUTCOMES:
        totals.setdefault(row["lever"], [0, 0])
        totals[row["lever"]][1] += 1
        if row["outcome"] in {"helpful", "deescalated"}:
            totals[row["lever"]][0] += 1
    WEEKLY_RATES.clear()
    for lever, (good, n) in totals.items():
        WEEKLY_RATES[lever] = good / n if n else 0.0
    return dict(WEEKLY_RATES)
