from __future__ import annotations

import argparse
import base64
import getpass
import re
import secrets
import subprocess
import time
from collections.abc import Callable

from app.config import get_settings
from app.demo_access import make_access_code_hash
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.identity import AzureCliCredential
from azure.keyvault.secrets import SecretClient
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def _cli_secret(command: list[str]) -> str:
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _provider_values(resource_group: str) -> dict[str, str]:
    settings = get_settings()
    speech_key = settings.speech_key.get_secret_value().strip() or _cli_secret(
        [
            "az",
            "cognitiveservices",
            "account",
            "keys",
            "list",
            "--resource-group",
            resource_group,
            "--name",
            "manobal-speech",
            "--query",
            "key1",
            "--output",
            "tsv",
        ]
    )
    translator_key = settings.translator_key.get_secret_value().strip() or _cli_secret(
        [
            "az",
            "cognitiveservices",
            "account",
            "keys",
            "list",
            "--resource-group",
            resource_group,
            "--name",
            "manobal-translator",
            "--query",
            "key1",
            "--output",
            "tsv",
        ]
    )
    safety_key = settings.content_safety_key.get_secret_value().strip() or _cli_secret(
        [
            "az",
            "cognitiveservices",
            "account",
            "keys",
            "list",
            "--resource-group",
            resource_group,
            "--name",
            "manobal-safety",
            "--query",
            "key1",
            "--output",
            "tsv",
        ]
    )
    acs_connection = settings.acs_connection_string.get_secret_value().strip() or _cli_secret(
        [
            "az",
            "communication",
            "list-key",
            "--resource-group",
            resource_group,
            "--name",
            "manobal-acs",
            "--query",
            "primaryConnectionString",
            "--output",
            "tsv",
        ]
    )
    values = {
        "deepgram-api-key": settings.deepgram_api_key.get_secret_value().strip(),
        "speech-key": speech_key,
        "translator-key": translator_key,
        "content-safety-key": safety_key,
        "acs-connection-string": acs_connection,
    }
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise RuntimeError("Missing provider secret names: " + ", ".join(missing))
    return values


def _secret_exists(client: SecretClient, name: str) -> bool:
    try:
        client.get_secret(name)
        return True
    except ResourceNotFoundError:
        return False


def _set_with_retry(client: SecretClient, name: str, value: str) -> None:
    for attempt in range(6):
        try:
            client.set_secret(name, value)
            return
        except HttpResponseError as error:
            if error.status_code not in {401, 403} or attempt == 5:
                raise
            time.sleep(10)


def _ensure(
    client: SecretClient,
    name: str,
    factory: Callable[[], str],
) -> bool:
    if _secret_exists(client, name):
        return False
    _set_with_retry(client, name, factory())
    return True


def _prompt_code(label: str) -> str:
    first = getpass.getpass(f"{label} code: ")
    second = getpass.getpass(f"Confirm {label.lower()} code: ")
    if first != second:
        raise RuntimeError(f"{label} code confirmation did not match")
    if len(first) < 12:
        raise RuntimeError(f"{label} code must contain at least 12 characters")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", first):
        raise RuntimeError(
            f"{label} code may use letters, numbers, period, underscore, and hyphen"
        )
    return first


def _generate_grant_pair() -> tuple[str, str]:
    private_key = Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")
    return private_pem, public_pem


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Populate MANOBAL Key Vault secrets without printing values."
    )
    parser.add_argument("--app-vault", required=True)
    parser.add_argument("--identity-vault", required=True)
    parser.add_argument("--ai-resource-group", default="rg-manobal-ai")
    parser.add_argument("--rotate-access", action="store_true")
    args = parser.parse_args()

    credential = AzureCliCredential()
    app_client = SecretClient(
        vault_url=f"https://{args.app_vault}.vault.azure.net",
        credential=credential,
    )
    identity_client = SecretClient(
        vault_url=f"https://{args.identity_vault}.vault.azure.net",
        credential=credential,
    )

    changed: list[str] = []
    try:
        for name, value in _provider_values(args.ai_resource_group).items():
            _set_with_retry(app_client, name, value)
            changed.append(name)

        internal_app = {
            "access-jwt": lambda: secrets.token_urlsafe(48),
            "realtime-jwt": lambda: secrets.token_urlsafe(48),
            "incident-hmac": lambda: secrets.token_urlsafe(48),
            "demo-gate-jwt": lambda: secrets.token_urlsafe(48),
        }
        for name, factory in internal_app.items():
            if _ensure(app_client, name, factory):
                changed.append(name)

        internal_vault = {
            "vault-token-hmac": lambda: base64.b64encode(secrets.token_bytes(32)).decode(
                "ascii"
            ),
            "tokenise-ingest": lambda: secrets.token_urlsafe(48),
        }
        for name, factory in internal_vault.items():
            if _ensure(identity_client, name, factory):
                changed.append(name)

        private_exists = _secret_exists(app_client, "grant-private-pem")
        public_exists = _secret_exists(identity_client, "grant-public-pem")
        if not private_exists or not public_exists:
            private_pem, public_pem = _generate_grant_pair()
            _set_with_retry(app_client, "grant-private-pem", private_pem)
            _set_with_retry(identity_client, "grant-public-pem", public_pem)
            changed.extend(["grant-private-pem", "grant-public-pem"])

        access_exists = _secret_exists(app_client, "judge-access-hash")
        operator_exists = _secret_exists(app_client, "operator-access-hash")
        if args.rotate_access or not access_exists or not operator_exists:
            judge_code = _prompt_code("Judge")
            operator_code = _prompt_code("Operator")
            if secrets.compare_digest(judge_code, operator_code):
                raise RuntimeError("Judge and operator codes must be different")
            _set_with_retry(
                app_client,
                "judge-access-hash",
                make_access_code_hash(judge_code),
            )
            _set_with_retry(
                app_client,
                "operator-access-hash",
                make_access_code_hash(operator_code),
            )
            changed.extend(["judge-access-hash", "operator-access-hash"])
    finally:
        app_client.close()
        identity_client.close()
        credential.close()

    print(f"Key Vault synchronization complete for {len(set(changed))} secret names.")


if __name__ == "__main__":
    main()
