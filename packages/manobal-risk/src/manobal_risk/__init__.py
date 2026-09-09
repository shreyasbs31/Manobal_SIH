"""MANOBAL risk engine (SDD §4.5, module M5/M6).

A pure, dependency-light scoring library. It takes a subject's pseudonymous
history and a signed ruleset, and returns a tier plus the names of the categories
that contributed. It returns no score, holds no credential, opens no socket and
touches no database — which is what makes SDD §3.2 rule 1 ("the risk engine has
no path to Zone 3") a property of the code rather than a promise about it.
"""

from __future__ import annotations

from .engine import score, score_with_trace
from .errors import (
    InsufficientBaselineError,
    ManobalRiskError,
    RulesetError,
    RulesetSignatureError,
)
from .ruleset import DomainSpec, IndicatorSpec, Ruleset, TierBounds, load_ruleset, parse_ruleset
from .types import (
    DOMAIN_CATEGORY,
    AcuteTrigger,
    AcuteTriggerKind,
    Baseline,
    Direction,
    Domain,
    DomainScore,
    IndicatorDeviation,
    Observation,
    RiskAssessment,
    ScoringTrace,
    SubjectHistory,
    Tier,
)

__version__ = "0.1.0"

__all__ = [
    "DOMAIN_CATEGORY",
    "AcuteTrigger",
    "AcuteTriggerKind",
    "Baseline",
    "Direction",
    "Domain",
    "DomainScore",
    "DomainSpec",
    "IndicatorDeviation",
    "IndicatorSpec",
    "InsufficientBaselineError",
    "ManobalRiskError",
    "Observation",
    "RiskAssessment",
    "Ruleset",
    "RulesetError",
    "RulesetSignatureError",
    "ScoringTrace",
    "SubjectHistory",
    "Tier",
    "TierBounds",
    "load_ruleset",
    "parse_ruleset",
    "score",
    "score_with_trace",
]
