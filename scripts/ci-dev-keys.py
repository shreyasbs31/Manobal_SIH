"""Create the gitignored development key files for a CI run.

The tests read infra/keys/, which is intentionally not tracked. This script creates
the missing files and never overwrites an existing one, so local development keys
are left alone.

Grant keys: a fresh Ed25519 pair, which is all the tests need.

Vault token key: the eight demo personas carry hard-coded subject tokens derived
from the project's private dev token key. That key must not be published, so CI
takes it from the optional DEV_VAULT_KEYS_JSON secret. Without it a random key is
generated and MANOBAL_CI_RANDOM_KEYS=1 is exported so the tests that assert those
fixed tokens skip themselves instead of failing.
"""

from __future__ import annotations

import base64
import json
import os
import secrets
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

KEYS = Path("infra/keys")


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o600)


def grant_keys() -> None:
    private_path = KEYS / "grant-private.pem"
    public_path = KEYS / "grant-public.pem"
    if private_path.exists() and public_path.exists():
        return
    private_key = Ed25519PrivateKey.generate()
    _write(
        private_path,
        private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode("ascii"),
    )
    _write(
        public_path,
        private_key.public_key()
        .public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("ascii"),
    )


def vault_keys() -> bool:
    """Return True when the project's real dev token key was supplied."""
    path = KEYS / "dev-vault-keys.json"
    if path.exists():
        return True
    supplied = os.environ.get("DEV_VAULT_KEYS_JSON", "").strip()
    if supplied:
        json.loads(supplied)
        _write(path, supplied)
        return True
    _write(
        path,
        json.dumps(
            {
                "version": "ci-random",
                "token_hmac_key": base64.b64encode(secrets.token_bytes(32)).decode(),
                "wrapping_key": base64.b64encode(secrets.token_bytes(32)).decode(),
                "notice": "Random CI key. Persona-token assertions are skipped.",
            }
        ),
    )
    return False


def main() -> None:
    KEYS.mkdir(parents=True, exist_ok=True)
    grant_keys()
    if vault_keys():
        print("Development keys ready (project token key supplied).")
        return
    print("Development keys ready (random token key; persona-token tests will skip).")
    github_env = os.environ.get("GITHUB_ENV")
    if github_env:
        with open(github_env, "a", encoding="utf-8") as handle:
            handle.write("MANOBAL_CI_RANDOM_KEYS=1\n")


if __name__ == "__main__":
    main()
