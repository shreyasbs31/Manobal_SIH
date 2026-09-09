"""Unit-level critical incidents — ``--incidents-per-year``.

An incident is a shared shock: everybody standing in the same place absorbs it at
once. That makes it the one driver in the generator that is correlated *across*
subjects, which matters because it is the failure mode of any per-subject
baseline. Twelve personnel in one company all deviating in the same week is not
twelve independent cases and the aggregation layer has to be able to see that.

The flag is read as a **force-wide** annual rate — twelve incidents a year across
the modelled force, not twelve per unit — which is the plain reading of the name
and the only one that stays sane as ``--units`` changes. At the SDD's 240 units
that leaves most units untouched over eighteen months, which is realistic and
means a test that wants an incident has to ask for a higher rate.

The response window is the SDD §6.4.6 pathway: raised stress for the affected
unit, decaying over about a month, plus a raised acute sensitivity for the small
number of personnel directly involved.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from .arrays import FloatArray
from .config import GenerationConfig
from .population import POSTING_INTENSITY, Unit
from .rng import substream
from .tokens import incident_id

#: Days over which an incident's elevated pressure is modelled, and the decay
#: constant inside that window. Thirty days rather than the SDD's 72-hour
#: check-in window: the check-in window is the *response* SLA, whereas the
#: behavioural effect on a unit outlasts it by weeks.
INCIDENT_WINDOW_DAYS = 30
INCIDENT_DECAY_DAYS = 11.0

#: Peak pressure added to an affected unit, in the same units as the deployment
#: pressure the workload stage consumes.
INCIDENT_PEAK_PRESSURE = 0.85

#: Probability that a given member of an affected unit was directly involved and
#: therefore reaches the M8 acute pathway on the SDD §4.7
#: ``critical_incident_direct_involvement`` trigger.
DIRECT_INVOLVEMENT_PROBABILITY = 0.025

_KINDS: tuple[str, ...] = (
    "ied_attack",
    "ambush",
    "operational_casualty",
    "accidental_death_on_duty",
    "civil_disturbance_casualty",
    "natural_disaster_deployment",
)


@dataclass(frozen=True, slots=True)
class Incident:
    incident_id: str
    unit_index: int
    unit_code: str
    sector_code: str
    day: int
    kind: str
    severity: float


def draw_incidents(config: GenerationConfig, units: Sequence[Unit]) -> tuple[Incident, ...]:
    """Draw the run's incidents, weighted towards high-intensity postings."""
    rng = substream(config.seed, "incidents")
    expected = config.incidents_per_year * config.duration_days / 365.0
    count = int(rng.poisson(expected)) if expected > 0.0 else 0
    if count == 0 or not units:
        return ()

    weights = np.array(
        [POSTING_INTENSITY[unit.posting_class] for unit in units], dtype=np.float64
    )
    weights /= weights.sum()
    unit_draws = rng.choice(len(units), size=count, p=weights)
    day_draws = rng.integers(0, config.duration_days, size=count)
    kind_draws = rng.integers(0, len(_KINDS), size=count)
    severities = rng.uniform(0.55, 1.0, size=count)

    incidents = [
        Incident(
            incident_id=incident_id(config.seed, position),
            unit_index=units[int(unit_draws[position])].index,
            unit_code=units[int(unit_draws[position])].code,
            sector_code=units[int(unit_draws[position])].sector_code,
            day=int(day_draws[position]),
            kind=_KINDS[int(kind_draws[position])],
            severity=float(severities[position]),
        )
        for position in range(count)
    ]
    return tuple(sorted(incidents, key=lambda incident: (incident.day, incident.incident_id)))


def incidents_by_unit(incidents: Sequence[Incident]) -> dict[int, tuple[Incident, ...]]:
    grouped: dict[int, list[Incident]] = {}
    for incident in incidents:
        grouped.setdefault(incident.unit_index, []).append(incident)
    return {index: tuple(items) for index, items in grouped.items()}


def unit_pressure(incidents: Sequence[Incident], n_days: int) -> FloatArray:
    """Additional daily pressure on a unit from its own incidents.

    Exponential decay from the day of the incident. Overlapping incidents add,
    because a unit hit twice in a fortnight is in a materially worse place than
    one hit once and the generator should not smooth that away.
    """
    pressure = np.zeros(n_days, dtype=np.float64)
    days = np.arange(n_days, dtype=np.float64)
    for incident in incidents:
        elapsed = days - float(incident.day)
        window = (elapsed >= 0.0) & (elapsed < INCIDENT_WINDOW_DAYS)
        decay = np.exp(-np.maximum(elapsed, 0.0) / INCIDENT_DECAY_DAYS)
        pressure += INCIDENT_PEAK_PRESSURE * incident.severity * decay * window
    return pressure
