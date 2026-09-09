"""Generation parameters — the SDD Appendix A.3 command line, as a value type.

Every knob the CLI exposes lands in one frozen object that is validated once, at
construction. The generator itself then never re-checks a bound, and the manifest
is a straight serialisation of this object, so a dataset always carries the exact
parameters that produced it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from datetime import date, timedelta
from enum import StrEnum
from typing import Any

from .errors import SynthConfigError

#: Fixed default so that a run with no ``--start-date`` is still byte-reproducible.
#: Reading the clock here would break the determinism guarantee outright.
DEFAULT_START_DATE = date(2025, 3, 1)

#: The seed from the SDD Appendix A.3 example invocation, used when ``--seed`` is
#: omitted. A default rather than a required flag so that the smoke command is
#: two flags long, and a constant rather than an entropy draw for the same reason
#: as the start date: an unseeded run would be irreproducible, which is the one
#: property this generator is not allowed to lose.
DEFAULT_SEED = 20260908

#: Below this the risk engine cannot form a baseline at all (ninety-day window,
#: twenty-one observations) and the output would be untestable rather than small.
MIN_DURATION_DAYS = 60

#: Days of primitive history burned before the first indicator row is emitted, so
#: that the 28-day aggregates in the SDD §4.4 table are not computed from four
#: days of roster.
WARMUP_DAYS = 28

#: One CRPF battalion is roughly a third of a thousand personnel, which is the
#: ratio behind the SDD's 80,000-over-240-units example.
PERSONNEL_PER_UNIT = 333
PERSONNEL_PER_SECTOR = 20000
MAX_SECTORS = 8


class RankDistribution(StrEnum):
    """Where the rank mix comes from."""

    CRPF_ACTUAL = "crpf_actual"
    UNIFORM = "uniform"


class ConsentProfile(StrEnum):
    REALISTIC = "realistic"
    FULL = "full"


class MissingnessProfile(StrEnum):
    REALISTIC = "realistic"
    NONE = "none"


class DeploymentModel(StrEnum):
    INSURGENCY_MIXED = "insurgency_mixed"
    STATIC_GUARD = "static_guard"


class DistressOnset(StrEnum):
    WEIBULL = "weibull"
    UNIFORM = "uniform"


class FairnessProfile(StrEnum):
    """Whether subgroup base rates are equal or deliberately skewed.

    ``skewed`` exists so that the SDD §9.6 disparate-impact test can be shown to
    fail when it should. A parity assertion that has never been observed to fail
    is not evidence of parity, it is evidence of an untested assertion.
    """

    NEUTRAL = "neutral"
    SKEWED = "skewed"


class OutputFormat(StrEnum):
    JSONL = "jsonl"
    #: Columnar-friendly CSV. Named for what it deliberately is not: adding a
    #: parquet writer would drag pyarrow into a package whose only runtime
    #: dependencies are numpy and the risk engine.
    CSV = "parquet-free-csv"


@dataclass(frozen=True, slots=True)
class GenerationConfig:
    """A complete, validated description of one synthetic corpus."""

    seed: int
    personnel: int = 80_000
    duration_days: int = 540
    sectors: int | None = None
    units: int | None = None
    rank_distribution: RankDistribution = RankDistribution.CRPF_ACTUAL
    enrolment_rate: float = 0.42
    consent_profile: ConsentProfile = ConsentProfile.REALISTIC
    missingness: MissingnessProfile = MissingnessProfile.REALISTIC
    deployment_model: DeploymentModel = DeploymentModel.INSURGENCY_MIXED
    incidents_per_year: float = 12.0
    distress_cohort: float = 0.06
    distress_onset: DistressOnset = DistressOnset.WEIBULL
    acute_events: float = 0.004
    gaming_cohort: float = 0.02
    fairness_profile: FairnessProfile = FairnessProfile.NEUTRAL
    output_format: OutputFormat = OutputFormat.JSONL
    start_date: date = DEFAULT_START_DATE

    def __post_init__(self) -> None:
        _require(self.personnel >= 1, "personnel must be at least 1")
        _require(
            self.duration_days >= MIN_DURATION_DAYS,
            f"duration-days must be at least {MIN_DURATION_DAYS}; the risk engine needs a "
            "ninety-day baseline window with twenty-one observations in it",
        )
        _require(self.seed >= 0, "seed must be a non-negative integer")
        _require(self.incidents_per_year >= 0.0, "incidents-per-year must not be negative")
        for name, value in (
            ("enrolment-rate", self.enrolment_rate),
            ("distress-cohort", self.distress_cohort),
            ("acute-events", self.acute_events),
            ("gaming-cohort", self.gaming_cohort),
        ):
            _require(0.0 <= value <= 1.0, f"{name} must be within [0, 1]; got {value}")
        _require(
            self.gaming_cohort + self.distress_cohort <= 1.0,
            "distress-cohort and gaming-cohort together must not exceed the whole force",
        )
        if self.sectors is not None:
            _require(self.sectors >= 1, "sectors must be at least 1")
        if self.units is not None:
            _require(self.units >= 1, "units must be at least 1")
        _require(
            self.resolved_units >= self.resolved_sectors,
            f"units ({self.resolved_units}) must not be fewer than sectors "
            f"({self.resolved_sectors}); a sector with no unit can hold nobody",
        )

    @property
    def resolved_sectors(self) -> int:
        """Sector count, scaled from ``personnel`` when not given explicitly.

        Defaulting rather than requiring the flag is what lets the smoke command
        be two arguments long: nobody should have to work out how many sectors
        fifty people need.
        """
        if self.sectors is not None:
            return self.sectors
        scaled = math.ceil(self.personnel / PERSONNEL_PER_SECTOR)
        return min(max(scaled, 1), MAX_SECTORS)

    @property
    def resolved_units(self) -> int:
        if self.units is not None:
            return self.units
        scaled = round(self.personnel / PERSONNEL_PER_UNIT)
        return max(scaled, self.resolved_sectors)

    @property
    def warmup_days(self) -> int:
        """Primitive days consumed before the first indicator row."""
        return min(WARMUP_DAYS, self.duration_days // 4)

    @property
    def end_date(self) -> date:
        return self.start_date + timedelta(days=self.duration_days - 1)

    def day_to_date(self, day: int) -> date:
        return self.start_date + timedelta(days=day)

    def with_seed(self, seed: int) -> GenerationConfig:
        return replace(self, seed=seed)

    def as_manifest_parameters(self) -> dict[str, Any]:
        """The parameter block of ``manifest.json``.

        Records the *resolved* sector and unit counts alongside the requested
        ones, so that a dataset generated from a two-flag smoke command can still
        be reproduced exactly without knowing this module's defaulting rules.
        """
        return {
            "seed": self.seed,
            "personnel": self.personnel,
            "duration_days": self.duration_days,
            "sectors": self.sectors,
            "units": self.units,
            "resolved_sectors": self.resolved_sectors,
            "resolved_units": self.resolved_units,
            "rank_distribution": str(self.rank_distribution),
            "enrolment_rate": self.enrolment_rate,
            "consent_profile": str(self.consent_profile),
            "missingness": str(self.missingness),
            "deployment_model": str(self.deployment_model),
            "incidents_per_year": self.incidents_per_year,
            "distress_cohort": self.distress_cohort,
            "distress_onset": str(self.distress_onset),
            "acute_events": self.acute_events,
            "gaming_cohort": self.gaming_cohort,
            "fairness_profile": str(self.fairness_profile),
            "output_format": str(self.output_format),
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "warmup_days": self.warmup_days,
        }


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SynthConfigError(message)
