"""The scoring ruleset — rules as signed data, not code (NFR-M5, FR-3.6).

Weights, thresholds and tier boundaries live in a YAML artefact that a clinical
advisor or a WDEC member can read and argue with. Changing them is a reviewable
data change with a recorded diff and a signature, not a code deployment.

Loading is strict on purpose. Every constraint below is one an engineer could
plausibly get wrong in a hurry — domain weights that no longer sum to one, a
tier boundary edited out of order, an indicator pointing at a domain nobody
declared — and each of them silently mis-tiers people rather than crashing. The
engine refuses to start instead.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

import yaml

from .errors import RulesetError
from .signing import artefact_sha256, verify_artefact
from .types import Direction, Domain

#: Environment variable holding the hex-encoded Ed25519 public key that ruleset
#: artefacts must verify against. In production this is provisioned from Vault.
FORCE_VERIFY_KEY_ENV = "MANOBAL_RULESET_VERIFY_KEY"

_WEIGHT_SUM_TOLERANCE = 1e-6

_DIRECTIONS: Mapping[str, Direction] = MappingProxyType(
    {
        "rising_is_adverse": Direction.RISING_IS_ADVERSE,
        "falling_is_adverse": Direction.FALLING_IS_ADVERSE,
    }
)


@dataclass(frozen=True, slots=True)
class IndicatorSpec:
    """How one indicator is read: which domain, which direction is bad, how noisy."""

    code: str
    domain: Domain
    direction: Direction
    #: Floor on the deviation denominator, in the indicator's own units. Stops a
    #: very stable subject being flagged for a trivial absolute change.
    epsilon: float
    #: Relative weight inside its domain.
    weight: float = 1.0
    description: str = ""


@dataclass(frozen=True, slots=True)
class DomainSpec:
    domain: Domain
    #: Contribution to the composite, before coverage renormalisation.
    weight: float
    #: Score at or above which this domain counts as one of the corroborating
    #: signals. Per-domain because the evidence bases differ sharply — a
    #: validated instrument earns a lower bar than a voice feature.
    corroboration_threshold: float


@dataclass(frozen=True, slots=True)
class TierBounds:
    t1: float
    t2: float
    t3: float


@dataclass(frozen=True, slots=True)
class Ruleset:
    """A loaded, validated, signature-verified ruleset."""

    version: str
    sha256: str
    baseline_window_days: int
    baseline_min_observations: int
    #: How recent an indicator's latest observation must be to count as a current
    #: value. Beyond this it is treated as absent, which lowers the domain's
    #: coverage — the honest representation of a feed that has stopped reporting,
    #: as opposed to one reporting "normal" (FR-2.6 staleness).
    current_value_max_age_days: int
    coverage_floor: float
    z_divisor: float
    corroboration_min_domains: int
    hysteresis_cycles: int
    tier_bounds: TierBounds
    indicators: Mapping[str, IndicatorSpec]
    domains: Mapping[Domain, DomainSpec]
    source_path: str = ""

    def indicators_for(self, domain: Domain) -> tuple[IndicatorSpec, ...]:
        return tuple(spec for spec in self.indicators.values() if spec.domain is domain)

    def expected_indicator_count(self, domain: Domain) -> int:
        """Denominator of the coverage fraction for ``domain``.

        Counted from the ruleset rather than from the data, so that "this subject
        has no wearable" registers as low coverage instead of as perfect coverage
        of an empty set.
        """
        return len(self.indicators_for(domain))

    def indicator_weights_for(self, domain: Domain) -> Mapping[str, float]:
        return MappingProxyType(
            {spec.code: spec.weight for spec in self.indicators.values() if spec.domain is domain}
        )

    def domain_of(self, indicator_code: str) -> Domain | None:
        spec = self.indicators.get(indicator_code)
        return spec.domain if spec else None

    @property
    def indicator_domains(self) -> Mapping[str, Domain]:
        return MappingProxyType({code: spec.domain for code, spec in self.indicators.items()})


def load_ruleset(
    path: str | Path,
    *,
    verify_key_hex: str | None = None,
    require_signature: bool = True,
) -> Ruleset:
    """Load, verify and validate a ruleset artefact.

    ``require_signature`` exists for unit tests that build throwaway rulesets in
    a tmp dir. It is not wired to any configuration flag reachable from a running
    service: production loading always verifies, and there is no environment in
    which an operator can turn that off (SDD §10.5).
    """
    artefact = Path(path)
    if not artefact.is_file():
        raise RulesetError(f"Ruleset artefact not found: {artefact}")

    payload = artefact.read_bytes()

    if require_signature:
        key = verify_key_hex or os.environ.get(FORCE_VERIFY_KEY_ENV)
        if not key:
            raise RulesetError(
                f"No ruleset verification key configured. Set {FORCE_VERIFY_KEY_ENV} "
                "or pass verify_key_hex explicitly."
            )
        verify_artefact(artefact, key)

    try:
        document = yaml.safe_load(payload)
    except yaml.YAMLError as exc:
        raise RulesetError(f"Ruleset artefact is not valid YAML: {exc}") from exc

    return parse_ruleset(document, sha256=artefact_sha256(payload), source_path=str(artefact))


def parse_ruleset(
    document: Any,
    *,
    sha256: str,
    source_path: str = "",
) -> Ruleset:
    """Validate a parsed ruleset document into an immutable :class:`Ruleset`."""
    if not isinstance(document, dict):
        raise RulesetError("Ruleset must be a mapping at the top level.")

    version = document.get("version")
    if not isinstance(version, str) or not version.strip():
        raise RulesetError("Ruleset must declare a non-empty string 'version'.")

    scoring = document.get("scoring")
    if not isinstance(scoring, dict):
        raise RulesetError("Ruleset must declare a 'scoring' mapping.")

    domains = _parse_domains(document.get("domains"))
    indicators = _parse_indicators(document.get("indicators"), domains)
    bounds = _parse_tier_bounds(scoring.get("tier_bounds"))

    coverage_floor = _positive_fraction(scoring, "coverage_floor")
    z_divisor = _positive_number(scoring, "z_divisor")
    baseline_window_days = _positive_int(scoring, "baseline_window_days")
    baseline_min_observations = _positive_int(scoring, "baseline_min_observations")
    current_value_max_age_days = _positive_int(scoring, "current_value_max_age_days")
    corroboration_min_domains = _positive_int(scoring, "corroboration_min_domains")
    hysteresis_cycles = _non_negative_int(scoring, "hysteresis_cycles")

    if baseline_min_observations > baseline_window_days:
        raise RulesetError(
            "baseline_min_observations exceeds baseline_window_days; no subject could "
            "ever accumulate a sufficient baseline."
        )
    if current_value_max_age_days > baseline_window_days:
        raise RulesetError(
            "current_value_max_age_days exceeds baseline_window_days; an observation could "
            "be accepted as current while sitting outside its own baseline window."
        )

    for domain in domains:
        if not any(spec.domain is domain for spec in indicators.values()):
            raise RulesetError(
                f"Domain {domain} carries a weight but declares no indicators; it would "
                "always be at zero coverage and could never contribute."
            )

    return Ruleset(
        version=version,
        sha256=sha256,
        baseline_window_days=baseline_window_days,
        baseline_min_observations=baseline_min_observations,
        current_value_max_age_days=current_value_max_age_days,
        coverage_floor=coverage_floor,
        z_divisor=z_divisor,
        corroboration_min_domains=corroboration_min_domains,
        hysteresis_cycles=hysteresis_cycles,
        tier_bounds=bounds,
        indicators=MappingProxyType(dict(indicators)),
        domains=MappingProxyType(dict(domains)),
        source_path=source_path,
    )


def _parse_domains(raw: Any) -> dict[Domain, DomainSpec]:
    if not isinstance(raw, dict) or not raw:
        raise RulesetError("Ruleset must declare a non-empty 'domains' mapping.")

    domains: dict[Domain, DomainSpec] = {}
    for key, body in raw.items():
        try:
            domain = Domain(key)
        except ValueError as exc:
            raise RulesetError(f"Unknown domain '{key}' in ruleset.") from exc
        if not isinstance(body, dict):
            raise RulesetError(f"Domain '{key}' must be a mapping.")

        weight = _as_float(body.get("weight"), f"domains.{key}.weight")
        threshold = _as_float(
            body.get("corroboration_threshold"), f"domains.{key}.corroboration_threshold"
        )
        if weight <= 0:
            raise RulesetError(f"Domain '{key}' weight must be positive.")
        if not 0.0 <= threshold <= 1.0:
            raise RulesetError(f"Domain '{key}' corroboration_threshold must be within [0, 1].")

        domains[domain] = DomainSpec(
            domain=domain, weight=weight, corroboration_threshold=threshold
        )

    total = sum(spec.weight for spec in domains.values())
    if abs(total - 1.0) > _WEIGHT_SUM_TOLERANCE:
        raise RulesetError(
            f"Domain weights must sum to 1.0; they sum to {total:.6f}. "
            "Coverage renormalisation assumes a normalised weight vector."
        )
    return domains


def _parse_indicators(raw: Any, domains: Mapping[Domain, DomainSpec]) -> dict[str, IndicatorSpec]:
    if not isinstance(raw, dict) or not raw:
        raise RulesetError("Ruleset must declare a non-empty 'indicators' mapping.")

    indicators: dict[str, IndicatorSpec] = {}
    for code, body in raw.items():
        if not isinstance(body, dict):
            raise RulesetError(f"Indicator '{code}' must be a mapping.")

        raw_domain = body.get("domain")
        try:
            domain = Domain(str(raw_domain))
        except ValueError as exc:
            raise RulesetError(
                f"Indicator '{code}' references unknown domain '{raw_domain}'."
            ) from exc
        if domain not in domains:
            raise RulesetError(
                f"Indicator '{code}' belongs to domain '{domain}', which carries no weight."
            )

        direction_key = body.get("direction")
        if not isinstance(direction_key, str) or direction_key not in _DIRECTIONS:
            raise RulesetError(
                f"Indicator '{code}' must declare direction as one of "
                f"{sorted(_DIRECTIONS)}; got {direction_key!r}."
            )

        epsilon = _as_float(body.get("epsilon"), f"indicators.{code}.epsilon")
        if epsilon <= 0:
            raise RulesetError(
                f"Indicator '{code}' epsilon must be positive; it is the floor that stops a "
                "perfectly stable subject being flagged for a trivial change."
            )

        weight = _as_float(body.get("weight", 1.0), f"indicators.{code}.weight")
        if weight <= 0:
            raise RulesetError(f"Indicator '{code}' weight must be positive.")

        indicators[str(code)] = IndicatorSpec(
            code=str(code),
            domain=domain,
            direction=_DIRECTIONS[direction_key],
            epsilon=epsilon,
            weight=weight,
            description=str(body.get("description", "")),
        )
    return indicators


def _parse_tier_bounds(raw: Any) -> TierBounds:
    if not isinstance(raw, dict):
        raise RulesetError("scoring.tier_bounds must be a mapping with keys t1, t2, t3.")

    bounds = TierBounds(
        t1=_as_float(raw.get("t1"), "tier_bounds.t1"),
        t2=_as_float(raw.get("t2"), "tier_bounds.t2"),
        t3=_as_float(raw.get("t3"), "tier_bounds.t3"),
    )
    if not 0.0 < bounds.t1 < bounds.t2 < bounds.t3 <= 1.0:
        raise RulesetError(
            "tier_bounds must satisfy 0 < t1 < t2 < t3 <= 1; "
            f"got t1={bounds.t1}, t2={bounds.t2}, t3={bounds.t3}."
        )
    return bounds


def _as_float(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise RulesetError(f"{field} must be a number; got {value!r}.")
    return float(value)


def _positive_number(body: Mapping[str, Any], field: str) -> float:
    value = _as_float(body.get(field), f"scoring.{field}")
    if value <= 0:
        raise RulesetError(f"scoring.{field} must be positive.")
    return value


def _positive_fraction(body: Mapping[str, Any], field: str) -> float:
    value = _as_float(body.get(field), f"scoring.{field}")
    if not 0.0 < value <= 1.0:
        raise RulesetError(f"scoring.{field} must be within (0, 1].")
    return value


def _positive_int(body: Mapping[str, Any], field: str) -> int:
    value = body.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RulesetError(f"scoring.{field} must be a positive integer; got {value!r}.")
    return value


def _non_negative_int(body: Mapping[str, Any], field: str) -> int:
    value = body.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RulesetError(f"scoring.{field} must be a non-negative integer; got {value!r}.")
    return value
