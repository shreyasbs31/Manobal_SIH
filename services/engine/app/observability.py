from __future__ import annotations

from collections import defaultdict
from typing import Any

CAP_INR = 400.0
TOKEN_INR = 0.002

_latencies: dict[str, list[float]] = defaultdict(list)
_counts: dict[str, int] = defaultdict(int)
_errors: dict[str, int] = defaultdict(int)
_tokens = 0
_forced_guard = False


def record_request(path: str, seconds: float, status: int) -> None:
    key = path.split("?")[0]
    _counts[key] += 1
    _latencies[key].append(seconds * 1000)
    if len(_latencies[key]) > 200:
        _latencies[key] = _latencies[key][-200:]
    if status >= 400:
        _errors[key] += 1


def record_tokens(n: int) -> None:
    global _tokens
    _tokens += max(0, n)


def set_cost_guard(forced: bool) -> None:
    global _forced_guard
    _forced_guard = forced


def estimated_spend_inr() -> float:
    return round(_tokens * TOKEN_INR, 2)


def cost_guard_active() -> bool:
    return _forced_guard or estimated_spend_inr() > CAP_INR


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((q / 100) * (len(ordered) - 1)))))
    return round(ordered[index], 2)


def metrics_payload() -> dict[str, Any]:
    sample = _latencies.get("/api/v1/companion/turn") or next(iter(_latencies.values()), [])
    return {
        "requests": dict(_counts),
        "errors": dict(_errors),
        "p50_ms": _percentile(sample, 50),
        "p95_ms": _percentile(sample, 95),
        "estimated_spend_inr": estimated_spend_inr(),
        "cap_inr": CAP_INR,
        "cost_guard": cost_guard_active(),
        "cache_hit_rate": 0.0,
    }


def reset_metrics() -> None:
    global _tokens, _forced_guard
    _latencies.clear()
    _counts.clear()
    _errors.clear()
    _tokens = 0
    _forced_guard = False
