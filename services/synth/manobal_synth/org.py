from __future__ import annotations

from dataclasses import dataclass

COMPANIES: tuple[str, ...] = ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot")
RANK_BANDS: tuple[tuple[str, float], ...] = (
    ("Constable/GD", 0.70),
    ("Head Constable", 0.15),
    ("ASI", 0.05),
    ("SI", 0.05),
    ("Inspector", 0.02),
    ("gazetted", 0.03),
)
TENURE_BANDS: tuple[str, ...] = ("0_to_5", "5_to_10", "10_to_15", "15_plus")
HOME_REGIONS: tuple[str, ...] = ("north_band", "west_band", "east_band", "south_band")
LANGUAGES: tuple[str, ...] = ("hi", "en", "hi-Latn", "ta")
GENDERS: tuple[str, ...] = ("male", "female")

SECTORS: tuple[tuple[str, str, str, str, str, tuple[str, ...], str], ...] = (
    ("north", "Sector North Synthetic", "north", "cold", "high", ("n01", "n02", "n03"), "N"),
    (
        "central",
        "Sector Central Synthetic",
        "central",
        "hot-humid",
        "plain",
        ("c02", "c03", "c04"),
        "C",
    ),
    ("east", "Sector East Synthetic", "east", "hot-humid", "plain", ("e01", "e02", "e03"), "E"),
    (
        "capital",
        "Sector Capital Synthetic",
        "capital",
        "temperate",
        "plain",
        ("c01", "p02", "p03"),
        "K",
    ),
)

COMPANY_LABEL = {
    "alpha": "Alpha",
    "bravo": "Bravo",
    "charlie": "Charlie",
    "delta": "Delta",
    "echo": "Echo",
    "foxtrot": "Foxtrot",
}


@dataclass(frozen=True)
class UnitSpec:
    path: str
    name: str
    level: str
    parent: str | None
    theatre: str
    climate_class: str
    altitude_class: str


def battalion_label(sector_key: str, bn_code: str) -> str:
    if sector_key == "north":
        return f"Bn N-{bn_code[1:].zfill(2)} Synthetic"
    if sector_key == "east":
        return f"Bn E-{bn_code[1:].zfill(2)} Synthetic"
    if sector_key == "capital" and bn_code == "c01":
        return "Bn C-01 Synthetic"
    if sector_key == "central":
        return f"Bn C-{bn_code[1:].zfill(2)} Synthetic"
    return f"Bn {bn_code.upper()} Synthetic"


def build_units() -> tuple[UnitSpec, ...]:
    units: list[UnitSpec] = [
        UnitSpec("force", "Force HQ Synthetic", "force", None, "all", "temperate", "plain"),
    ]
    for key, name, theatre, climate, altitude, battalions, _prefix in SECTORS:
        sector_path = f"force.{key}"
        units.append(
            UnitSpec(sector_path, name, "sector", "force", theatre, climate, altitude),
        )
        for bn_code in battalions:
            bn_path = f"{sector_path}.{bn_code}"
            units.append(
                UnitSpec(
                    bn_path,
                    battalion_label(key, bn_code),
                    "battalion",
                    sector_path,
                    theatre,
                    climate,
                    altitude,
                ),
            )
            for company in COMPANIES:
                units.append(
                    UnitSpec(
                        f"{bn_path}.{company}",
                        f"{COMPANY_LABEL[company]} company Synthetic",
                        "company",
                        bn_path,
                        theatre,
                        climate,
                        altitude,
                    ),
                )
    return tuple(units)


def company_paths() -> tuple[str, ...]:
    return tuple(unit.path for unit in build_units() if unit.level == "company")


def battalion_paths() -> tuple[str, ...]:
    return tuple(unit.path for unit in build_units() if unit.level == "battalion")


def sector_paths() -> tuple[str, ...]:
    return tuple(unit.path for unit in build_units() if unit.level == "sector")
