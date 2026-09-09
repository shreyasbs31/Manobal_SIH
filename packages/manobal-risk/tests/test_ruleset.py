"""Ruleset loading and validation — NFR-M5, FR-3.6.

Rules-as-data is only an improvement over rules-as-code if the loader is stricter
than a compiler would have been. Every case below is one where a plausible typo
would otherwise mis-tier people silently.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml

from manobal_risk.errors import RulesetError, RulesetSignatureError
from manobal_risk.ruleset import FORCE_VERIFY_KEY_ENV, Ruleset, load_ruleset, parse_ruleset
from manobal_risk.types import Domain


@pytest.fixture
def document(ruleset_path: Path) -> dict[str, Any]:
    return yaml.safe_load(ruleset_path.read_bytes())


def parse(document: dict[str, Any]) -> Ruleset:
    return parse_ruleset(document, sha256="0" * 64)


class TestShippedArtefact:
    def test_the_production_ruleset_loads(self, ruleset: Ruleset) -> None:
        assert ruleset.version == "1.0.0"

    def test_every_domain_in_the_sdd_is_weighted(self, ruleset: Ruleset) -> None:
        assert set(ruleset.domains) == set(Domain)

    def test_domain_weights_match_the_sdd_table(self, ruleset: Ruleset) -> None:
        """SDD §4.5. These are calibration targets and will move — but they move
        by a reviewed, signed data change, never by accident."""
        assert {d.value: s.weight for d, s in ruleset.domains.items()} == {
            "D5_self_report": 0.22,
            "D1_workload": 0.18,
            "D4_physiological": 0.18,
            "D2_leave": 0.15,
            "D3_organisational": 0.12,
            "D6_vocal_acoustic": 0.08,
            "D7_engagement": 0.07,
        }

    def test_tier_bounds_match_the_sdd(self, ruleset: Ruleset) -> None:
        assert (ruleset.tier_bounds.t1, ruleset.tier_bounds.t2, ruleset.tier_bounds.t3) == (
            0.35,
            0.55,
            0.75,
        )

    def test_the_corroboration_gate_requires_two_domains(self, ruleset: Ruleset) -> None:
        assert ruleset.corroboration_min_domains == 2

    def test_voice_carries_the_highest_bar_of_any_domain(self, ruleset: Ruleset) -> None:
        """SDD §12.2 R9: the weakest evidence base and the highest accent and
        language sensitivity of the seven domains, so it needs the most
        deviation before it is allowed to corroborate anything."""
        voice = ruleset.domains[Domain.VOCAL_ACOUSTIC]

        assert voice.corroboration_threshold == max(
            s.corroboration_threshold for s in ruleset.domains.values()
        )

    def test_the_two_weakest_signals_carry_the_two_smallest_weights(self, ruleset: Ruleset) -> None:
        """Voice (weak evidence base) and engagement (silence has many innocent
        causes) sit below every objective or instrument-backed domain."""
        by_weight = sorted(ruleset.domains.values(), key=lambda s: s.weight)

        assert {s.domain for s in by_weight[:2]} == {Domain.ENGAGEMENT, Domain.VOCAL_ACOUSTIC}

    def test_every_domain_has_enough_indicators_to_clear_its_coverage_floor(
        self, ruleset: Ruleset
    ) -> None:
        for domain in ruleset.domains:
            assert ruleset.expected_indicator_count(domain) >= 2, domain

    def test_indicator_lookup_helpers_agree(self, ruleset: Ruleset) -> None:
        assert ruleset.domain_of("pss10_total") is Domain.SELF_REPORT
        assert ruleset.domain_of("not_an_indicator") is None
        assert set(ruleset.indicator_weights_for(Domain.SELF_REPORT)) == {
            s.code for s in ruleset.indicators_for(Domain.SELF_REPORT)
        }


class TestValidation:
    def test_domain_weights_must_sum_to_one(self, document: dict[str, Any]) -> None:
        broken = copy.deepcopy(document)
        broken["domains"]["D5_self_report"]["weight"] = 0.5

        with pytest.raises(RulesetError, match=r"sum to 1\.0"):
            parse(broken)

    def test_tier_bounds_must_be_strictly_increasing(self, document: dict[str, Any]) -> None:
        broken = copy.deepcopy(document)
        broken["scoring"]["tier_bounds"] = {"t1": 0.6, "t2": 0.5, "t3": 0.9}

        with pytest.raises(RulesetError, match="tier_bounds"):
            parse(broken)

    def test_an_indicator_may_not_reference_an_unweighted_domain(
        self, document: dict[str, Any]
    ) -> None:
        broken = copy.deepcopy(document)
        broken["indicators"]["pss10_total"]["domain"] = "not_a_domain"

        with pytest.raises(RulesetError, match="unknown domain"):
            parse(broken)

    def test_a_weighted_domain_must_declare_indicators(self, document: dict[str, Any]) -> None:
        """Otherwise it sits permanently at zero coverage, quietly removing its
        weight from every composite while still appearing in the ruleset."""
        broken = copy.deepcopy(document)
        broken["indicators"] = {
            code: body
            for code, body in broken["indicators"].items()
            if body["domain"] != "D7_engagement"
        }

        with pytest.raises(RulesetError, match="declares no indicators"):
            parse(broken)

    def test_epsilon_must_be_positive(self, document: dict[str, Any]) -> None:
        broken = copy.deepcopy(document)
        broken["indicators"]["pss10_total"]["epsilon"] = 0.0

        with pytest.raises(RulesetError, match="epsilon must be positive"):
            parse(broken)

    def test_direction_must_be_one_of_the_two_known_values(self, document: dict[str, Any]) -> None:
        broken = copy.deepcopy(document)
        broken["indicators"]["pss10_total"]["direction"] = "up"

        with pytest.raises(RulesetError, match="direction"):
            parse(broken)

    def test_baseline_minimum_may_not_exceed_the_window(self, document: dict[str, Any]) -> None:
        broken = copy.deepcopy(document)
        broken["scoring"]["baseline_min_observations"] = 500

        with pytest.raises(RulesetError, match="ever accumulate a sufficient baseline"):
            parse(broken)

    def test_staleness_window_may_not_exceed_the_baseline_window(
        self, document: dict[str, Any]
    ) -> None:
        broken = copy.deepcopy(document)
        broken["scoring"]["current_value_max_age_days"] = 400

        with pytest.raises(RulesetError, match="current_value_max_age_days"):
            parse(broken)

    def test_coverage_floor_must_be_a_fraction(self, document: dict[str, Any]) -> None:
        broken = copy.deepcopy(document)
        broken["scoring"]["coverage_floor"] = 1.5

        with pytest.raises(RulesetError, match="coverage_floor"):
            parse(broken)

    def test_corroboration_minimum_must_be_a_positive_integer(
        self, document: dict[str, Any]
    ) -> None:
        broken = copy.deepcopy(document)
        broken["scoring"]["corroboration_min_domains"] = 0

        with pytest.raises(RulesetError, match="corroboration_min_domains"):
            parse(broken)

    def test_hysteresis_cycles_may_be_zero_but_not_negative(self, document: dict[str, Any]) -> None:
        allowed = copy.deepcopy(document)
        allowed["scoring"]["hysteresis_cycles"] = 0
        assert parse(allowed).hysteresis_cycles == 0

        broken = copy.deepcopy(document)
        broken["scoring"]["hysteresis_cycles"] = -1
        with pytest.raises(RulesetError, match="hysteresis_cycles"):
            parse(broken)

    def test_a_missing_version_is_rejected(self, document: dict[str, Any]) -> None:
        broken = copy.deepcopy(document)
        broken.pop("version")

        with pytest.raises(RulesetError, match="version"):
            parse(broken)

    def test_a_missing_scoring_block_is_rejected(self, document: dict[str, Any]) -> None:
        broken = copy.deepcopy(document)
        broken.pop("scoring")

        with pytest.raises(RulesetError, match="scoring"):
            parse(broken)

    def test_a_non_mapping_document_is_rejected(self) -> None:
        with pytest.raises(RulesetError, match="mapping at the top level"):
            parse_ruleset(["not", "a", "mapping"], sha256="0" * 64)

    def test_a_numeric_field_given_a_string_is_rejected(self, document: dict[str, Any]) -> None:
        broken = copy.deepcopy(document)
        broken["domains"]["D5_self_report"]["weight"] = "0.22"

        with pytest.raises(RulesetError, match="must be a number"):
            parse(broken)

    def test_a_boolean_is_not_accepted_as_a_number(self, document: dict[str, Any]) -> None:
        """``True == 1`` in Python. A ruleset that silently reads ``weight: yes``
        as ``1.0`` is exactly the class of quiet mis-tiering this loader exists
        to prevent."""
        broken = copy.deepcopy(document)
        broken["domains"]["D5_self_report"]["weight"] = True

        with pytest.raises(RulesetError, match="must be a number"):
            parse(broken)


class TestLoading:
    def test_a_missing_artefact_is_an_error(self, tmp_path: Path) -> None:
        with pytest.raises(RulesetError, match="not found"):
            load_ruleset(tmp_path / "nope.yaml", require_signature=False)

    def test_malformed_yaml_is_an_error(self, tmp_path: Path) -> None:
        artefact = tmp_path / "bad.yaml"
        artefact.write_text("version: [unclosed\n", encoding="utf-8")

        with pytest.raises(RulesetError, match="not valid YAML"):
            load_ruleset(artefact, require_signature=False)

    def test_loading_records_the_content_hash(self, ruleset: Ruleset) -> None:
        assert len(ruleset.sha256) == 64
        assert int(ruleset.sha256, 16) >= 0

    def test_signature_verification_is_required_by_default(
        self, ruleset_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """SDD §10.5: the service refuses to start on an unsigned artefact."""
        monkeypatch.delenv(FORCE_VERIFY_KEY_ENV, raising=False)

        with pytest.raises(RulesetError, match="verification key"):
            load_ruleset(ruleset_path)

    def test_an_unsigned_artefact_is_refused_even_with_a_key_present(
        self, ruleset_path: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        unsigned = tmp_path / "unsigned.yaml"
        unsigned.write_bytes(ruleset_path.read_bytes())
        monkeypatch.setenv(FORCE_VERIFY_KEY_ENV, "aa" * 32)

        with pytest.raises(RulesetSignatureError, match="No signature found"):
            load_ruleset(unsigned)

    def test_the_ruleset_is_immutable_once_loaded(self, ruleset: Ruleset) -> None:
        with pytest.raises((AttributeError, TypeError)):
            ruleset.coverage_floor = 0.1  # type: ignore[misc]
        with pytest.raises(TypeError):
            ruleset.domains[Domain.WORKLOAD] = None  # type: ignore[index]
