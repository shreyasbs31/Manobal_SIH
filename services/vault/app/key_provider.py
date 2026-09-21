from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from typing import Protocol, cast

from azure.identity.aio import DefaultAzureCredential
from azure.keyvault.keys.aio import KeyClient
from azure.keyvault.keys.crypto import KeyWrapAlgorithm
from azure.keyvault.keys.crypto.aio import CryptographyClient
from azure.keyvault.secrets.aio import SecretClient
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .config import Settings


@dataclass(frozen=True)
class WrappedKey:
    ciphertext: bytes
    version: str


class KeyProvider(Protocol):
    async def token_digest(self, service_number: str) -> bytes: ...

    async def wrap_key(self, data_key: bytes) -> WrappedKey: ...

    async def unwrap_key(self, wrapped: bytes, version: str) -> bytes: ...

    async def close(self) -> None: ...


class LocalKeyProvider:
    """Development-only provider backed by a mounted JSON file."""

    def __init__(self, settings: Settings) -> None:
        raw = json.loads(settings.local_key_file.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("Local key file must contain a JSON object")
        values = cast(dict[str, object], raw)
        self._version = str(values["version"])
        self._token_key = self._decode_key(values["token_hmac_key"])
        self._wrapping_key = self._decode_key(values["wrapping_key"])

    @staticmethod
    def _decode_key(value: object) -> bytes:
        if not isinstance(value, str):
            raise ValueError("Local keys must be base64 strings")
        decoded = base64.b64decode(value, validate=True)
        if len(decoded) != 32:
            raise ValueError("Local keys must decode to 32 bytes")
        return decoded

    async def token_digest(self, service_number: str) -> bytes:
        return hmac.new(
            self._token_key,
            service_number.encode("utf-8"),
            hashlib.sha256,
        ).digest()

    async def wrap_key(self, data_key: bytes) -> WrappedKey:
        if len(data_key) != 32:
            raise ValueError("Data keys must contain 32 bytes")
        nonce = os.urandom(12)
        ciphertext = AESGCM(self._wrapping_key).encrypt(
            nonce,
            data_key,
            self._version.encode("utf-8"),
        )
        return WrappedKey(ciphertext=nonce + ciphertext, version=self._version)

    async def unwrap_key(self, wrapped: bytes, version: str) -> bytes:
        if version != self._version or len(wrapped) < 29:
            raise ValueError("Wrapped key version is unavailable")
        return AESGCM(self._wrapping_key).decrypt(
            wrapped[:12],
            wrapped[12:],
            version.encode("utf-8"),
        )

    async def close(self) -> None:
        return None


class AzureKeyVaultKeyProvider:
    def __init__(self, settings: Settings) -> None:
        if settings.keyvault_uri is None:
            raise ValueError("KEYVAULT_URI is required")
        self._settings = settings
        self._credential = DefaultAzureCredential(
            managed_identity_client_id=settings.azure_client_id or None,
            exclude_interactive_browser_credential=True,
        )
        self._keys = KeyClient(settings.keyvault_uri, self._credential)
        self._secrets = SecretClient(settings.keyvault_uri, self._credential)
        self._token_key: bytes | None = None

    async def _get_token_key(self) -> bytes:
        if self._token_key is None:
            secret = await self._secrets.get_secret(self._settings.kv_token_key_name)
            if secret.value is None:
                raise ValueError("Token key secret has no value")
            decoded = base64.b64decode(secret.value, validate=True)
            if len(decoded) < 32:
                raise ValueError("Token key secret is too short")
            self._token_key = decoded
        return self._token_key

    async def token_digest(self, service_number: str) -> bytes:
        token_key = await self._get_token_key()
        return hmac.new(
            token_key,
            service_number.encode("utf-8"),
            hashlib.sha256,
        ).digest()

    async def wrap_key(self, data_key: bytes) -> WrappedKey:
        key = await self._keys.get_key(self._settings.kv_kek_name)
        crypto = CryptographyClient(key, self._credential)
        try:
            result = await crypto.wrap_key(
                KeyWrapAlgorithm.rsa_oaep_256,
                data_key,
            )
        finally:
            await crypto.close()
        version = key.properties.version
        if version is None:
            raise ValueError("Key Vault KEK has no version")
        return WrappedKey(ciphertext=result.encrypted_key, version=version)

    async def unwrap_key(self, wrapped: bytes, version: str) -> bytes:
        key = await self._keys.get_key(self._settings.kv_kek_name, version)
        crypto = CryptographyClient(key, self._credential)
        try:
            result = await crypto.unwrap_key(
                KeyWrapAlgorithm.rsa_oaep_256,
                wrapped,
            )
            return result.key
        finally:
            await crypto.close()

    async def close(self) -> None:
        await self._keys.close()
        await self._secrets.close()
        await self._credential.close()


def build_key_provider(settings: Settings) -> KeyProvider:
    if settings.key_provider == "azure":
        return AzureKeyVaultKeyProvider(settings)
    return LocalKeyProvider(settings)
