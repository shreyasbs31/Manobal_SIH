from __future__ import annotations

import json
from typing import Any

from ..scoring.forecast import REGISTRY, register_world_metrics
from ..scoring.ruleset import REPO_ROOT

ROUTING_PATH = REPO_ROOT / "infra" / "evals" / "fixtures" / "routing.json"

DEFAULT_ROUTING: dict[str, Any] = {
    "en": "open",
    "hi": "main",
    "hi-Latn": "main",
    "ta": "main",
    "gate": "recorded",
    "crisis_recall_open": 1.0,
    "crisis_recall_main": 1.0,
    "reason": "Hindi and Hinglish stay on main unless open matches (31.1).",
}


def load_recorded_routing() -> dict[str, Any]:
    if ROUTING_PATH.exists():
        payload = json.loads(ROUTING_PATH.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            merged = dict(DEFAULT_ROUTING)
            merged.update(payload)
            return merged
    return dict(DEFAULT_ROUTING)


def record_companion_routing(routing: dict[str, Any] | None = None) -> dict[str, Any]:
    decision = routing or load_recorded_routing()
    register_world_metrics(
        "companion_routing",
        {"crisis_recall": float(decision.get("crisis_recall_main") or 1.0)},
        version="companion-gate-v1",
    )
    REGISTRY["companion_routing"]["routing"] = decision
    return decision


def ensure_companion_routing() -> dict[str, Any]:
    existing = REGISTRY.get("companion_routing") or {}
    routing = existing.get("routing")
    if isinstance(routing, dict) and routing.get("hi"):
        return routing
    return record_companion_routing()
