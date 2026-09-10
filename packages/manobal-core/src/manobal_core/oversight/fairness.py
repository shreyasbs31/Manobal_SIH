"""WDEC parity rollups. Cells below *k* are withheld, not rounded into a lie."""

from __future__ import annotations

from collections import defaultdict

from django.conf import settings
from django.db.models import Q

from manobal_core.apps.governance.aggregation import band_elevated
from manobal_core.apps.governance.enums import OFFICER_VISIBLE_TIERS, SubjectStatus
from manobal_core.apps.governance.models import RiskAssessmentRecord, Subject, Unit


def fairness_report(unit: Unit) -> dict[str, object]:
    """Rank-band cells for ``unit`` and the units beneath it.

    WDEC sits at the force. Counting only people posted on that exact node
    returns an empty report for CENTRAL while A Company is sitting under it.
    The path prefix includes the separator so ``12BN`` does not swallow
    ``12BN_RESERVE``.
    """
    k_threshold = int(settings.PRIVACY["K_ANONYMITY_THRESHOLD"])
    subjects = Subject.objects.filter(
        Q(unit__path=unit.path) | Q(unit__path__startswith=f"{unit.path}/"),
        status=SubjectStatus.ACTIVE,
    )
    tokens = list(subjects.values_list("subject_token", "rank_band"))
    latest = _latest_by_token([token for token, _ in tokens])
    buckets: dict[str, list[RiskAssessmentRecord | None]] = defaultdict(list)
    for token, band in tokens:
        buckets[band].append(latest.get(token))
    cells = [_cell(name, rows, k_threshold) for name, rows in sorted(buckets.items())]
    return {
        "unit": unit.code,
        "k_threshold": k_threshold,
        "cells": cells,
    }


def _cell(
    rank_band: str, rows: list[RiskAssessmentRecord | None], k_threshold: int
) -> dict[str, object]:
    # The denominator is the living rank-band, not the scored subset. Counting
    # only people with an assessment would shrink a company of twelve to the
    # three flagged cases and suppress a cell the commander is allowed to see.
    if len(rows) < k_threshold:
        return {"rank_band": rank_band, "suppressed": True}
    elevated = [
        row for row in rows if row is not None and row.tier in OFFICER_VISIBLE_TIERS
    ]
    counts: dict[str, int] = {}
    for row in elevated:
        for category in row.contributing_categories:
            counts[category] = counts.get(category, 0) + 1
    dominant = max(counts, key=lambda name: (counts[name], name)) if counts else ""
    return {
        "rank_band": rank_band,
        "suppressed": False,
        "elevated_band": band_elevated(len(elevated)),
        "dominant_category": dominant,
    }


def _latest_by_token(tokens: list[str]) -> dict[str, RiskAssessmentRecord]:
    if not tokens:
        return {}
    rows = RiskAssessmentRecord.objects.filter(subject_token__in=tokens).order_by(
        "subject_token", "-assessed_at", "-id"
    )
    latest: dict[str, RiskAssessmentRecord] = {}
    for row in rows:
        latest.setdefault(row.subject_token, row)
    return latest
