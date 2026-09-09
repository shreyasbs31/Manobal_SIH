"""Ground-truth cohort assignment — who declines, who games, who escalates.

This is the file that makes SDD §10.6 K3 and K4 measurable before a pilot. Every
subject leaves here with a complete, recorded answer to "is this person actually
in trouble, from when, how badly, and are they hiding it" — and that answer is
written to ``ground_truth.jsonl`` and never to ``observations.jsonl``. False
positives and false negatives are then arithmetic rather than opinion.

Two assignment rules are interpretations of Appendix A.3 worth stating.

``--gaming-cohort`` selects personnel who suppress their self-report while their
objective indicators keep deteriorating. A suppressor who is not deteriorating is
indistinguishable from an honest healthy subject and contributes nothing to the
corroboration-gate question, so the gaming cohort is drawn *from inside* the
distressed population, and only extends it if the requested gaming fraction
exceeds the distress fraction.

``--acute-events`` selects personnel who reach a PHQ-9 item-9 positive or raise
an explicit SOS. The event is assigned to the person, not to the platform: a
subject who never enrolled still has the crisis, it simply never reaches the
system. Those cases are recorded with ``acute_reported = false``, which is the
honest fixture for the population an app-based acute pathway cannot reach.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from manobal_risk import AcuteTriggerKind

from .arrays import FloatArray
from .config import GenerationConfig
from .consent import ConsentState
from .fairness import subgroup_rates
from .population import Subject
from .rng import substream
from .trajectory import (
    draw_onset_days,
    draw_ramp_days,
    draw_severity,
    flat_strain,
    is_deteriorating,
    strain_curve,
)

#: Share of self-raised acute events that present as an item-9 positive rather
#: than an explicit SOS. Item 9 dominates because it is asked routinely, whereas
#: pressing an SOS requires the person to decide they are in crisis.
_ITEM9_SHARE = 0.62

#: Acute events cluster in decline but are not confined to it — a bereavement or
#: a debt crisis arrives without a six-month behavioural run-up, and an acute
#: pathway that only ever fires for already-flagged subjects would be untested
#: against exactly the case it exists for.
_ACUTE_DISTRESSED_SHARE = 0.7

#: Earliest fraction of the run at which an acute event may occur, so that the
#: engine has some history for the subject when the override fires.
_ACUTE_EARLIEST_FRACTION = 0.35


@dataclass(frozen=True, slots=True)
class Cohort:
    """One subject's injected truth."""

    distressed: bool
    onset_day: int | None
    ramp_days: float
    severity: float
    gaming: bool
    acute_day: int | None
    acute_kind: AcuteTriggerKind | None
    acute_reported: bool

    def strain(self, n_days: int) -> FloatArray:
        """The daily strain series driving every downstream stage."""
        if not self.distressed or self.onset_day is None:
            return flat_strain(n_days)
        return strain_curve(
            n_days,
            onset_day=self.onset_day,
            ramp_days=self.ramp_days,
            severity=self.severity,
        )

    def label(self) -> str:
        if self.gaming:
            return "gaming"
        return "distress" if self.distressed else "stable"


def assign_cohorts(
    config: GenerationConfig,
    subjects: Sequence[Subject],
    consents: Sequence[ConsentState],
) -> tuple[Cohort, ...]:
    """Assign distress, gaming and acute status across the force."""
    rng = substream(config.seed, "cohorts")
    distressed = _draw_distressed(config, subjects, rng)
    gaming = _draw_gaming(config, distressed, rng)
    # Gaming is only meaningful against a deteriorating background, so a
    # suppressor drawn from outside the distressed set is promoted into it.
    distressed = distressed | gaming

    indices = np.flatnonzero(distressed)
    onsets = draw_onset_days(rng, len(indices), config.duration_days, config.distress_onset)
    ramps = draw_ramp_days(rng, len(indices), config.duration_days)
    severities = draw_severity(rng, len(indices))
    onset_by_subject = dict(zip(indices.tolist(), onsets.tolist(), strict=True))
    ramp_by_subject = dict(zip(indices.tolist(), ramps.tolist(), strict=True))
    severity_by_subject = dict(zip(indices.tolist(), severities.tolist(), strict=True))

    acute_day, acute_kind = _draw_acute(config, distressed, onset_by_subject, rng)

    return tuple(
        Cohort(
            distressed=bool(distressed[index]),
            onset_day=onset_by_subject.get(index),
            ramp_days=ramp_by_subject.get(index, 0.0),
            severity=severity_by_subject.get(index, 0.0),
            gaming=bool(gaming[index]),
            acute_day=acute_day.get(index),
            acute_kind=acute_kind.get(index),
            acute_reported=index in acute_day and consents[index].enrolled,
        )
        for index in range(len(subjects))
    )


def _draw_distressed(
    config: GenerationConfig,
    subjects: Sequence[Subject],
    rng: np.random.Generator,
) -> np.ndarray:
    """Bernoulli draw per subject at a fairness-weighted base rate.

    Multipliers are renormalised to their own mean so that switching
    ``--fairness-profile`` changes *who* is in the cohort without changing how
    many — otherwise a parity test could pass or fail on cohort size alone.
    """
    rates = subgroup_rates(config.fairness_profile)
    multipliers = np.array([rates.multiplier(subject) for subject in subjects], dtype=np.float64)
    mean = float(multipliers.mean()) if len(multipliers) else 1.0
    probabilities = np.clip(config.distress_cohort * multipliers / max(mean, 1e-9), 0.0, 1.0)
    return rng.random(len(subjects)) < probabilities


def _draw_gaming(
    config: GenerationConfig,
    distressed: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """Select suppressors, preferring subjects who are already deteriorating."""
    count = len(distressed)
    target = round(config.gaming_cohort * count)
    gaming = np.zeros(count, dtype=bool)
    if target <= 0:
        return gaming

    inside = np.flatnonzero(distressed)
    chosen = rng.permutation(inside)[:target]
    gaming[chosen] = True

    shortfall = target - len(chosen)
    if shortfall > 0:
        outside = np.flatnonzero(~distressed)
        gaming[rng.permutation(outside)[:shortfall]] = True
    return gaming


def _draw_acute(
    config: GenerationConfig,
    distressed: np.ndarray,
    onset_by_subject: dict[int, int],
    rng: np.random.Generator,
) -> tuple[dict[int, int], dict[int, AcuteTriggerKind]]:
    """Choose who has an acute event, when, and of which kind."""
    count = len(distressed)
    target = round(config.acute_events * count)
    if target <= 0:
        return {}, {}

    from_distressed = min(round(target * _ACUTE_DISTRESSED_SHARE), int(distressed.sum()))
    chosen = list(rng.permutation(np.flatnonzero(distressed))[:from_distressed])
    remaining = target - len(chosen)
    if remaining > 0:
        chosen.extend(rng.permutation(np.flatnonzero(~distressed))[:remaining].tolist())

    earliest = int(_ACUTE_EARLIEST_FRACTION * config.duration_days)
    latest = config.duration_days - 1
    days: dict[int, int] = {}
    kinds: dict[int, AcuteTriggerKind] = {}
    for index in sorted(int(value) for value in chosen):
        floor = max(earliest, onset_by_subject.get(index, earliest))
        days[index] = int(rng.integers(min(floor, latest), latest + 1))
        kinds[index] = (
            AcuteTriggerKind.PHQ9_ITEM9
            if float(rng.random()) < _ITEM9_SHARE
            else AcuteTriggerKind.EXPLICIT_SOS
        )
    return days, kinds


def deteriorating_at_end(cohort: Cohort, n_days: int) -> bool:
    return is_deteriorating(cohort.strain(n_days))
