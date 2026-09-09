"""Look up recommended next steps from the signed-adjacent YAML catalogue."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from django.conf import settings

from manobal_core.apps.governance.models import Case, InterventionRecommendation


@lru_cache(maxsize=4)
def _catalogue(path: str) -> dict[str, Any]:
    document = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        return {}
    return document


def propose_for_case(case: Case) -> list[InterventionRecommendation]:
    """Create recommendations for a newly opened case. Idempotent per code."""
    path = str(settings.INTERVENTIONS_PATH)
    recs = _catalogue(path).get("recommendations")
    if not isinstance(recs, dict):
        return []
    created: list[InterventionRecommendation] = []
    categories = list(case.contributing_categories) or ["default"]
    seen: set[str] = set()
    for category in categories:
        entries = recs.get(category) or recs.get("default") or []
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            code = str(entry.get("code") or "")
            if not code or code in seen:
                continue
            seen.add(code)
            if InterventionRecommendation.objects.filter(case=case, code=code).exists():
                continue
            created.append(
                InterventionRecommendation.objects.create(
                    case=case,
                    code=code,
                    rationale=str(entry.get("rationale") or ""),
                    priority=_as_int(entry.get("priority") or 0),
                )
            )
    return created


def _as_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return int(str(value))
    return value
