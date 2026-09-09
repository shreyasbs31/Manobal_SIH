"""Statistics and scoring shims shared by the suites.

Spearman is implemented here rather than pulled from scipy because scipy is not
a dependency of this monorepo and the generator's correctness tests should not
be the reason it becomes one. The tie handling is average-rank, matching
``scipy.stats.spearmanr`` on the inputs these tests use.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import fields

import numpy as np

from manobal_risk import Domain, Observation, SubjectHistory
from manobal_synth.arrays import FloatArray
from manobal_synth.dataset import SubjectRecords


def _average_ranks(values: FloatArray) -> FloatArray:
    order = np.argsort(values, kind="stable")
    ranks = np.empty(len(values), dtype=np.float64)
    ranks[order] = np.arange(len(values), dtype=np.float64)
    # Average the ranks inside each tie group. Without this, a constant stretch
    # of an integral indicator would get an arbitrary within-group ordering and
    # the correlation would depend on the sort algorithm.
    sorted_values = values[order]
    start = 0
    for stop in range(1, len(values) + 1):
        if stop == len(values) or sorted_values[stop] != sorted_values[start]:
            ranks[order[start:stop]] = ranks[order[start:stop]].mean()
            start = stop
    return ranks


def spearman(left: FloatArray, right: FloatArray) -> float:
    """Spearman rank correlation. Returns nan when either side is constant."""
    a = _average_ranks(np.asarray(left, dtype=np.float64))
    b = _average_ranks(np.asarray(right, dtype=np.float64))
    a = a - a.mean()
    b = b - b.mean()
    denominator = float(np.sqrt((a**2).sum() * (b**2).sum()))
    if denominator == 0.0:
        return float("nan")
    return float((a * b).sum() / denominator)


def mean_finite(values: Iterable[float]) -> float:
    finite = [value for value in values if np.isfinite(value)]
    if not finite:
        return float("nan")
    return float(np.mean(finite))


def history_for(records: SubjectRecords, as_of: object) -> SubjectHistory:
    """Load a subject's generated rows into the risk engine's input type.

    The field-by-field unpack is the point of the test: if ``ObservationRow``
    and ``manobal_risk.Observation`` ever drift apart, this raises rather than
    silently adapting.

    ``dataclasses.fields`` rather than ``__dict__`` because both row types are
    slotted, and a slotted instance has no instance dictionary to read.
    """
    observations = tuple(
        Observation(
            **{
                field.name: getattr(row, field.name)
                for field in fields(row)
                if field.name != "subject_token"
            }
        )
        for row in records.observations
    )
    return SubjectHistory(
        subject_token=records.ground_truth.subject_token,
        as_of=as_of,
        observations=observations,
        consented_domains=frozenset(
            Domain(domain) for domain in records.ground_truth.consented_domains
        ),
    )


def tier_counts(tiers: Sequence[str]) -> dict[str, int]:
    return {tier: tiers.count(tier) for tier in sorted(set(tiers))}


def tier_share_at_or_above(tiers: Sequence[str], minimum: str) -> float:
    """Fraction of subjects at or above a tier name such as ``T1``."""
    if not tiers:
        return 0.0
    floor = int(minimum[1:])
    return sum(1 for tier in tiers if int(tier[1:]) >= floor) / len(tiers)
