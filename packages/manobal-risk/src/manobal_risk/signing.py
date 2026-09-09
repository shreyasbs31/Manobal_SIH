"""Ed25519 signing for ruleset artefacts — NFR-M5, FR-3.6, SDD §10.5.

The scoring ruleset is data, not code: a YAML file a clinician or a WDEC member
can read and review without being able to read Python. What stops that from
becoming a liability is that the risk engine refuses to load an artefact it
cannot verify, so "the ruleset is easy to change" never becomes "the ruleset is
easy to change *quietly*".

Signatures are detached (``<artefact>.sig``) and computed over the exact bytes of
the file. There is no canonicalisation step, so there is no gap between what a
reviewer read and what the engine verified.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from nacl.exceptions import BadSignatureError
from nacl.signing import SigningKey, VerifyKey

from .errors import RulesetSignatureError

SIGNATURE_SUFFIX = ".sig"


def artefact_sha256(payload: bytes) -> str:
    """Content hash recorded on every assessment the artefact produces (FR-3.6)."""
    return hashlib.sha256(payload).hexdigest()


def signature_path_for(artefact_path: Path) -> Path:
    return artefact_path.with_name(artefact_path.name + SIGNATURE_SUFFIX)


def generate_keypair() -> tuple[str, str]:
    """Return ``(signing_key_hex, verify_key_hex)``.

    Development convenience only. Production signing keys are generated inside
    the HSM and never exist as hex anywhere (SDD §3.3, §7.2).
    """
    signing_key = SigningKey.generate()
    return (
        bytes(signing_key).hex(),
        bytes(signing_key.verify_key).hex(),
    )


def sign_bytes(payload: bytes, signing_key_hex: str) -> str:
    signing_key = SigningKey(bytes.fromhex(signing_key_hex))
    return signing_key.sign(payload).signature.hex()


def verify_bytes(payload: bytes, signature_hex: str, verify_key_hex: str) -> None:
    """Raise :class:`RulesetSignatureError` unless the signature verifies."""
    try:
        VerifyKey(bytes.fromhex(verify_key_hex)).verify(payload, bytes.fromhex(signature_hex))
    except (BadSignatureError, ValueError) as exc:
        raise RulesetSignatureError(
            "Ruleset signature did not verify against the configured force signing key. "
            "The engine will not score against an unapproved ruleset."
        ) from exc


def sign_artefact(artefact_path: Path, signing_key_hex: str) -> Path:
    """Write a detached signature next to ``artefact_path`` and return its path."""
    signature = sign_bytes(artefact_path.read_bytes(), signing_key_hex)
    target = signature_path_for(artefact_path)
    target.write_text(signature + "\n", encoding="utf-8")
    return target


def verify_artefact(artefact_path: Path, verify_key_hex: str) -> None:
    """Verify the detached signature for ``artefact_path``.

    A missing signature file is an error, not a soft warning. "Unsigned" and
    "signed by the wrong key" are the same failure as far as the engine is
    concerned: in both cases nobody has attested that these rules were approved.
    """
    signature_file = signature_path_for(artefact_path)
    if not signature_file.is_file():
        raise RulesetSignatureError(
            f"No signature found at {signature_file.name}. "
            "Unsigned rulesets are not loadable in any environment."
        )
    verify_bytes(
        artefact_path.read_bytes(),
        signature_file.read_text(encoding="utf-8").strip(),
        verify_key_hex,
    )
