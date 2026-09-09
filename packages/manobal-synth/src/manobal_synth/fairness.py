"""Subgroup base-rate fixtures for the SDD §9.6 disparate-impact gate.

The parity test compares flag rates across rank band, region, tenure bucket and
language. A generator that produced identical base rates everywhere would let
that test pass forever without ever demonstrating that it can fail — which is
worth nothing as a release gate. So there are two profiles.

``neutral`` gives every subgroup the same probability of entering distress. Any
disparity the pipeline then reports is manufactured downstream, by consent
take-up, missingness or the scoring itself, and that is exactly the disparity
§9.6 exists to catch.

``skewed`` injects a deliberate rank-band disparity — constables roughly five
times as likely to be in the distressed cohort as gazetted officers — so the
parity assertion can be *proved* to fail. Note what this does not claim about
reality: it is a test fixture, not a finding about CAPF personnel.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from .config import FairnessProfile
from .population import RankBand, Subject, TenureBucket

_NEUTRAL_RANK: Mapping[RankBand, float] = MappingProxyType(dict.fromkeys(RankBand, 1.0))

#: Ratio between the extremes is 5.4, comfortably outside the four-fifths rule,
#: so a parity test with any sane threshold has to reject it.
_SKEWED_RANK: Mapping[RankBand, float] = MappingProxyType(
    {
        RankBand.CONSTABLE: 1.90,
        RankBand.HEAD_CONSTABLE: 1.35,
        RankBand.ASI: 0.90,
        RankBand.SI: 0.75,
        RankBand.INSPECTOR: 0.50,
        RankBand.GAZETTED: 0.35,
    }
)

#: Tenure and language skews are milder on purpose. A fixture in which every
#: attribute is extreme cannot distinguish a parity test that checks all five
#: attributes from one that checks only the first and got lucky.
_SKEWED_TENURE: Mapping[TenureBucket, float] = MappingProxyType(
    {
        TenureBucket.UNDER_2: 1.35,
        TenureBucket.TWO_TO_5: 1.15,
        TenureBucket.FIVE_TO_15: 0.95,
        TenureBucket.OVER_15: 0.80,
    }
)


@dataclass(frozen=True, slots=True)
class SubgroupRates:
    """Multipliers applied to the configured distress base rate."""

    rank_band: Mapping[RankBand, float]
    tenure_bucket: Mapping[TenureBucket, float]
    #: Keyed by sector code suffix parity rather than by name, so that the skew
    #: survives any sector count the CLI is given.
    sector_alternating: tuple[float, float]
    language_minority: float

    def multiplier(self, subject: Subject) -> float:
        sector_index = int(subject.sector_code.rsplit("_", 1)[-1])
        language = 1.0 if subject.language == "hindi" else self.language_minority
        return (
            self.rank_band[subject.rank_band]
            * self.tenure_bucket[subject.tenure_bucket]
            * self.sector_alternating[sector_index % 2]
            * language
        )


NEUTRAL = SubgroupRates(
    rank_band=_NEUTRAL_RANK,
    tenure_bucket=MappingProxyType(dict.fromkeys(TenureBucket, 1.0)),
    sector_alternating=(1.0, 1.0),
    language_minority=1.0,
)

SKEWED = SubgroupRates(
    rank_band=_SKEWED_RANK,
    tenure_bucket=_SKEWED_TENURE,
    sector_alternating=(1.20, 0.85),
    language_minority=1.10,
)


def subgroup_rates(profile: FairnessProfile) -> SubgroupRates:
    return SKEWED if profile is FairnessProfile.SKEWED else NEUTRAL
