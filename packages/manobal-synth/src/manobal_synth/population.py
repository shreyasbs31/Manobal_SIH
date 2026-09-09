"""The force: sectors, units and personnel demographics.

The rank mix follows BPRD's published sanctioned-strength shape rather than a
convenient uniform draw, because the fairness fixtures are only useful if the
subgroups have realistic sizes. A parity test across a rank band holding two
percent of the force behaves very differently from one holding sixty, and the
SDD §9.6 gate has to be exercised against the real proportions.

Nothing here is scored. These attributes exist so that §9.6 disparate-impact
tests have subgroups to compare and so that unit-level incidents have a unit to
land on; they are written to ``subjects.jsonl``, deliberately in a different file
from ``observations.jsonl``, mirroring the production separation in which the
risk engine is handed a token and nothing else.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

import numpy as np

from .config import DeploymentModel, GenerationConfig, RankDistribution
from .rng import substream
from .tokens import sector_code, subject_token, unit_code


class RankBand(StrEnum):
    CONSTABLE = "constable"
    HEAD_CONSTABLE = "head_constable"
    ASI = "assistant_sub_inspector"
    SI = "sub_inspector"
    INSPECTOR = "inspector"
    GAZETTED = "gazetted_officer"


class TenureBucket(StrEnum):
    UNDER_2 = "under_2y"
    TWO_TO_5 = "2_to_5y"
    FIVE_TO_15 = "5_to_15y"
    OVER_15 = "over_15y"


class PostingClass(StrEnum):
    HIGH_INTENSITY = "high_intensity"
    MODERATE = "moderate"
    STATIC = "static_guard"


#: Approximate CRPF constabulary-heavy shape. Calibration target, not a citation:
#: the generator needs realistic subgroup *sizes*, not exact establishment tables.
_CRPF_ACTUAL: Mapping[RankBand, float] = MappingProxyType(
    {
        RankBand.CONSTABLE: 0.615,
        RankBand.HEAD_CONSTABLE: 0.152,
        RankBand.ASI: 0.071,
        RankBand.SI: 0.079,
        RankBand.INSPECTOR: 0.043,
        RankBand.GAZETTED: 0.040,
    }
)

#: Median years of service and dispersion per band. Seniority correlates with
#: rank, which is what makes rank and tenure partially confounded subgroups — a
#: property the parity tests need to contend with rather than be shielded from.
_TENURE_YEARS: Mapping[RankBand, tuple[float, float]] = MappingProxyType(
    {
        RankBand.CONSTABLE: (6.0, 5.0),
        RankBand.HEAD_CONSTABLE: (13.0, 5.0),
        RankBand.ASI: (17.0, 5.0),
        RankBand.SI: (14.0, 6.0),
        RankBand.INSPECTOR: (19.0, 5.0),
        RankBand.GAZETTED: (16.0, 7.0),
    }
)

#: Duty-load multiplier by band. A constable on a picket and a gazetted officer
#: do not share a workload baseline, and the personal-baseline approach only
#: looks credible if the population it starts from is stratified.
RANK_LOAD_FACTOR: Mapping[RankBand, float] = MappingProxyType(
    {
        RankBand.CONSTABLE: 1.06,
        RankBand.HEAD_CONSTABLE: 1.02,
        RankBand.ASI: 0.97,
        RankBand.SI: 0.95,
        RankBand.INSPECTOR: 0.92,
        RankBand.GAZETTED: 0.88,
    }
)

_LANGUAGES: Mapping[str, float] = MappingProxyType(
    {
        "hindi": 0.45,
        "english": 0.10,
        "bengali": 0.09,
        "marathi": 0.08,
        "telugu": 0.07,
        "tamil": 0.06,
        "kannada": 0.05,
        "malayalam": 0.04,
        "odia": 0.03,
        "assamese": 0.03,
    }
)

_REGIONS: tuple[str, ...] = (
    "north",
    "north_east",
    "left_wing_extremism_belt",
    "west",
    "south",
    "central",
    "kashmir_valley",
    "east",
)

#: Posting mix per deployment model, and the family-station probability of each
#: class. ``insurgency_mixed`` is the SDD's example: rotation between
#: high-intensity deployment and static duty, with family separation attached.
_POSTING_MIX: Mapping[DeploymentModel, Mapping[PostingClass, float]] = MappingProxyType(
    {
        DeploymentModel.INSURGENCY_MIXED: MappingProxyType(
            {
                PostingClass.HIGH_INTENSITY: 0.35,
                PostingClass.MODERATE: 0.40,
                PostingClass.STATIC: 0.25,
            }
        ),
        DeploymentModel.STATIC_GUARD: MappingProxyType(
            {
                PostingClass.HIGH_INTENSITY: 0.08,
                PostingClass.MODERATE: 0.27,
                PostingClass.STATIC: 0.65,
            }
        ),
    }
)

FAMILY_STATION_PROBABILITY: Mapping[PostingClass, float] = MappingProxyType(
    {
        PostingClass.HIGH_INTENSITY: 0.05,
        PostingClass.MODERATE: 0.35,
        PostingClass.STATIC: 0.75,
    }
)

#: Weighted days per calendar day for the ``deployment_intensity`` indicator.
POSTING_INTENSITY: Mapping[PostingClass, float] = MappingProxyType(
    {
        PostingClass.HIGH_INTENSITY: 1.0,
        PostingClass.MODERATE: 0.55,
        PostingClass.STATIC: 0.2,
    }
)


@dataclass(frozen=True, slots=True)
class Unit:
    index: int
    code: str
    sector_code: str
    region: str
    posting_class: PostingClass
    family_station: bool
    assigned_strength: int


@dataclass(frozen=True, slots=True)
class Subject:
    """A person's fixed attributes. No behaviour, no time series."""

    index: int
    subject_token: str
    unit_index: int
    unit_code: str
    sector_code: str
    rank_band: RankBand
    tenure_years: float
    language: str

    @property
    def tenure_bucket(self) -> TenureBucket:
        if self.tenure_years < 2.0:
            return TenureBucket.UNDER_2
        if self.tenure_years < 5.0:
            return TenureBucket.TWO_TO_5
        if self.tenure_years < 15.0:
            return TenureBucket.FIVE_TO_15
        return TenureBucket.OVER_15


def _rank_weights(distribution: RankDistribution) -> tuple[tuple[RankBand, ...], np.ndarray]:
    bands = tuple(RankBand)
    if distribution is RankDistribution.UNIFORM:
        weights = np.full(len(bands), 1.0 / len(bands))
    else:
        weights = np.array([_CRPF_ACTUAL[band] for band in bands], dtype=np.float64)
    return bands, weights / weights.sum()


def build_units(config: GenerationConfig) -> tuple[Unit, ...]:
    """Lay out sectors and units, and assign strengths.

    Units are spread across sectors as evenly as the counts allow. Posting class
    is drawn per unit rather than per subject because deployment is a property of
    where a unit is, and a unit-level critical incident has to reach everybody
    standing in the same place.
    """
    rng = substream(config.seed, "units")
    total_units = config.resolved_units
    total_sectors = config.resolved_sectors
    classes, probabilities = _posting_distribution(config.deployment_model)

    per_sector = np.array_split(np.arange(total_units), total_sectors)
    sector_of_unit = np.zeros(total_units, dtype=np.int64)
    for sector_index, unit_indices in enumerate(per_sector):
        sector_of_unit[unit_indices] = sector_index

    drawn = rng.choice(len(classes), size=total_units, p=probabilities)
    family = rng.random(total_units)
    strengths = _split_strength(config.personnel, total_units)

    return tuple(
        Unit(
            index=index,
            code=unit_code(index),
            sector_code=sector_code(int(sector_of_unit[index])),
            region=_REGIONS[int(sector_of_unit[index]) % len(_REGIONS)],
            posting_class=classes[int(drawn[index])],
            family_station=bool(
                family[index] < FAMILY_STATION_PROBABILITY[classes[int(drawn[index])]]
            ),
            assigned_strength=int(strengths[index]),
        )
        for index in range(total_units)
    )


def _posting_distribution(model: DeploymentModel) -> tuple[tuple[PostingClass, ...], np.ndarray]:
    mix = _POSTING_MIX[model]
    classes = tuple(mix)
    weights = np.array([mix[posting] for posting in classes], dtype=np.float64)
    return classes, weights / weights.sum()


def _split_strength(personnel: int, units: int) -> np.ndarray:
    base, remainder = divmod(personnel, units)
    strengths = np.full(units, base, dtype=np.int64)
    strengths[:remainder] += 1
    return strengths


def build_subjects(config: GenerationConfig, units: Sequence[Unit]) -> tuple[Subject, ...]:
    """Materialise the whole roster.

    Held in memory because demographics are small (a few hundred bytes a head)
    and every later stage needs random access to them, while the time series —
    which are not small — are streamed one subject at a time.
    """
    rng = substream(config.seed, "subjects")
    bands, weights = _rank_weights(config.rank_distribution)
    languages = tuple(_LANGUAGES)
    language_weights = np.array([_LANGUAGES[name] for name in languages], dtype=np.float64)
    language_weights /= language_weights.sum()

    unit_of_subject = np.repeat(
        np.arange(len(units), dtype=np.int64),
        np.array([unit.assigned_strength for unit in units], dtype=np.int64),
    )
    band_draws = rng.choice(len(bands), size=config.personnel, p=weights)
    language_draws = rng.choice(len(languages), size=config.personnel, p=language_weights)
    tenure_noise = rng.normal(0.0, 1.0, size=config.personnel)

    subjects: list[Subject] = []
    for index in range(config.personnel):
        band = bands[int(band_draws[index])]
        median, spread = _TENURE_YEARS[band]
        unit = units[int(unit_of_subject[index])]
        subjects.append(
            Subject(
                index=index,
                subject_token=subject_token(config.seed, index),
                unit_index=unit.index,
                unit_code=unit.code,
                sector_code=unit.sector_code,
                rank_band=band,
                tenure_years=float(np.clip(median + spread * tenure_noise[index], 0.5, 35.0)),
                language=languages[int(language_draws[index])],
            )
        )
    return tuple(subjects)
