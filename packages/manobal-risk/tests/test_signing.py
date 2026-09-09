"""Ruleset signing — NFR-M5, FR-3.6, SDD §10.5.

"The ruleset is easy to change" must never become "the ruleset is easy to change
quietly". These tests are what keep those two sentences apart.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from manobal_risk.cli import main
from manobal_risk.errors import RulesetSignatureError
from manobal_risk.ruleset import FORCE_VERIFY_KEY_ENV, load_ruleset
from manobal_risk.signing import (
    artefact_sha256,
    generate_keypair,
    sign_artefact,
    sign_bytes,
    signature_path_for,
    verify_artefact,
    verify_bytes,
)


@pytest.fixture
def keypair() -> tuple[str, str]:
    return generate_keypair()


@pytest.fixture
def artefact(tmp_path: Path, ruleset_path: Path) -> Path:
    copy = tmp_path / ruleset_path.name
    copy.write_bytes(ruleset_path.read_bytes())
    return copy


class TestSignAndVerify:
    def test_a_signed_artefact_verifies(
        self, artefact: Path, keypair: tuple[str, str]
    ) -> None:
        signing_key, verify_key = keypair

        sign_artefact(artefact, signing_key)

        verify_artefact(artefact, verify_key)  # does not raise

    def test_a_tampered_artefact_fails_verification(
        self, artefact: Path, keypair: tuple[str, str]
    ) -> None:
        """The scenario this exists for: someone edits a weight on the server."""
        signing_key, verify_key = keypair
        sign_artefact(artefact, signing_key)

        artefact.write_bytes(artefact.read_bytes().replace(b"weight: 0.22", b"weight: 0.92"))

        with pytest.raises(RulesetSignatureError):
            verify_artefact(artefact, verify_key)

    def test_a_signature_from_the_wrong_key_fails(self, artefact: Path) -> None:
        wrong_signing_key, _ = generate_keypair()
        _, force_verify_key = generate_keypair()
        sign_artefact(artefact, wrong_signing_key)

        with pytest.raises(RulesetSignatureError):
            verify_artefact(artefact, force_verify_key)

    def test_a_missing_signature_is_the_same_failure_as_a_bad_one(
        self, artefact: Path, keypair: tuple[str, str]
    ) -> None:
        _, verify_key = keypair

        with pytest.raises(RulesetSignatureError, match="No signature found"):
            verify_artefact(artefact, verify_key)

    def test_a_malformed_signature_is_rejected_without_crashing(
        self, artefact: Path, keypair: tuple[str, str]
    ) -> None:
        _, verify_key = keypair
        signature_path_for(artefact).write_text("not-hex", encoding="utf-8")

        with pytest.raises(RulesetSignatureError):
            verify_artefact(artefact, verify_key)

    def test_signing_is_over_the_exact_bytes_a_reviewer_read(
        self, artefact: Path, keypair: tuple[str, str]
    ) -> None:
        """No canonicalisation step, so there is no gap between the file that was
        reviewed and the bytes that were signed."""
        signing_key, verify_key = keypair
        payload = artefact.read_bytes()

        verify_bytes(payload, sign_bytes(payload, signing_key), verify_key)

    def test_the_content_hash_is_stable(self, artefact: Path) -> None:
        assert artefact_sha256(artefact.read_bytes()) == artefact_sha256(artefact.read_bytes())


class TestLoadingASignedArtefact:
    def test_load_ruleset_verifies_before_parsing(
        self, artefact: Path, keypair: tuple[str, str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        signing_key, verify_key = keypair
        sign_artefact(artefact, signing_key)
        monkeypatch.setenv(FORCE_VERIFY_KEY_ENV, verify_key)

        loaded = load_ruleset(artefact)

        assert loaded.version == "1.0.0"
        assert loaded.sha256 == artefact_sha256(artefact.read_bytes())

    def test_an_explicit_key_overrides_the_environment(
        self, artefact: Path, keypair: tuple[str, str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        signing_key, verify_key = keypair
        sign_artefact(artefact, signing_key)
        monkeypatch.setenv(FORCE_VERIFY_KEY_ENV, "bb" * 32)

        assert load_ruleset(artefact, verify_key_hex=verify_key).version == "1.0.0"


class TestCli:
    def test_keygen_emits_both_environment_lines(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["keygen"]) == 0

        out = capsys.readouterr().out
        assert "MANOBAL_RULESET_SIGNING_KEY=" in out
        assert f"{FORCE_VERIFY_KEY_ENV}=" in out

    def test_sign_then_verify_round_trips(
        self, artefact: Path, keypair: tuple[str, str], capsys: pytest.CaptureFixture[str]
    ) -> None:
        signing_key, verify_key = keypair

        assert main(["sign", str(artefact), "--signing-key", signing_key]) == 0
        assert main(["verify", str(artefact), "--verify-key", verify_key]) == 0
        assert "signature ok" in capsys.readouterr().out

    def test_sign_without_a_key_fails_loudly(
        self, artefact: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("MANOBAL_RULESET_SIGNING_KEY", raising=False)

        assert main(["sign", str(artefact)]) == 2

    def test_verify_without_a_key_fails_loudly(
        self, artefact: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv(FORCE_VERIFY_KEY_ENV, raising=False)

        assert main(["verify", str(artefact)]) == 2

    def test_verify_reports_a_bad_signature_as_a_failure_not_a_crash(
        self, artefact: Path, keypair: tuple[str, str]
    ) -> None:
        _, verify_key = keypair

        assert main(["verify", str(artefact), "--verify-key", verify_key]) == 1

    def test_show_prints_a_reviewable_summary(
        self, artefact: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["show", str(artefact)]) == 0

        out = capsys.readouterr().out
        assert '"version": "1.0.0"' in out
        assert "D5_self_report" in out
