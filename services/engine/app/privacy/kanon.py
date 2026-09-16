from __future__ import annotations

import hashlib
from typing import Any


def complementary_suppress(
    cells: list[dict[str, Any]],
    *,
    k: int = 10,
    churn_seed: str = "manobal",
) -> list[dict[str, Any]]:
    scored = []
    for index, cell in enumerate(cells):
        n = int(cell.get("n") or 0)
        scored.append((n, index, cell))
    scored.sort(key=lambda item: (item[0], _churn(churn_seed, str(item[2].get("key", item[1])))))
    suppressed_idx: set[int] = set()
    for n, index, _cell in scored:
        if n < k:
            suppressed_idx.add(index)
    if suppressed_idx:
        remaining = [item for item in scored if item[1] not in suppressed_idx]
        if remaining:
            suppressed_idx.add(remaining[0][1])
    out: list[dict[str, Any]] = []
    for index, cell in enumerate(cells):
        if index in suppressed_idx:
            hidden = {key: value for key, value in cell.items() if key in {"key", "unit", "week"}}
            hidden["band"] = "hidden"
            hidden["n"] = None
            out.append(hidden)
        else:
            out.append(dict(cell))
    return out


def trend_neighbour_suppress(weeks: list[dict[str, Any]], *, k: int = 10) -> list[dict[str, Any]]:
    flags = [int(cell.get("n") or 0) < k for cell in weeks]
    extra = flags[:]
    for index, flagged in enumerate(flags):
        if flagged:
            if index:
                extra[index - 1] = True
            if index + 1 < len(extra):
                extra[index + 1] = True
    out: list[dict[str, Any]] = []
    for cell, hide in zip(weeks, extra, strict=True):
        if hide:
            out.append({"week": cell.get("week"), "band": "hidden", "n": None})
        else:
            out.append(dict(cell))
    return out


def simulator_allows(n: int, k: int = 10) -> bool:
    return n >= k


def commander_incident_card(
    *,
    enrolled: int,
    asked: int,
    open_until: str,
    followup: str,
    k: int = 10,
) -> dict[str, str | int | None]:
    if enrolled < k:
        return {
            "window": open_until,
            "followup": followup,
            "asked_label": "hidden",
            "asked": None,
        }
    if asked < 3:
        label = "a few"
        count: int | None = None
    else:
        label = str(asked)
        count = asked
    return {
        "window": open_until,
        "followup": followup,
        "asked_label": label,
        "asked": count,
    }


def _churn(seed: str, key: str) -> str:
    return hashlib.sha256(f"{seed}:{key}".encode()).hexdigest()
