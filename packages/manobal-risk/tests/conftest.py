"""Shared fixtures for the risk-engine suites."""

from __future__ import annotations

from pathlib import Path

import pytest

from manobal_risk.ruleset import Ruleset, load_ruleset

#: The real production artefact. Tests run against the same file the engine
#: loads, so a mis-specified weight or a malformed indicator fails the build
#: rather than waiting to be discovered in a pilot.
RULESET_PATH = Path(__file__).resolve().parents[3] / "rulesets" / "manobal-ruleset-1.0.0.yaml"


@pytest.fixture(scope="session")
def ruleset_path() -> Path:
    assert RULESET_PATH.is_file(), f"ruleset artefact missing at {RULESET_PATH}"
    return RULESET_PATH


@pytest.fixture(scope="session")
def ruleset(ruleset_path: Path) -> Ruleset:
    # Signature verification is exercised by test_signing.py against throwaway
    # keys. Loading here without it keeps the unit suites independent of whether
    # a developer has a signed copy checked out.
    return load_ruleset(ruleset_path, require_signature=False)
