"""The key-management boundary for the identity enclave (SDD NFR-SEC2, §4.9).

Every piece of key material in Zone 3 sits behind this interface. In production
the implementation is backed by an HSM through PKCS#11 and the key bytes never
enter this process at all: ``wrap_data_key``, ``unwrap_data_key`` and
``compute_mac`` become remote operations. The local implementation below holds
keys in memory so the system is runnable on a laptop, and is the only part of
the enclave that must be swapped for a real deployment.

The interface is deliberately narrow. It offers no way to *read* a key, only to
use one. Code elsewhere in the enclave therefore cannot log, serialise or
accidentally persist a key-encryption key, because it never holds one.
"""

from __future__ import annotations

import base64
import hmac
import os
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from typing import Final, Protocol, runtime_checkable

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY_BYTES: Final = 32
"""AES-256 and HMAC-SHA-256 both take a 256-bit key (NFR-SEC2)."""

NONCE_BYTES: Final = 12
"""The nonce length AES-GCM is specified and analysed for."""

_KEK_ENV_PREFIX: Final = "MANOBAL_IDENTITY_KEK_V"
_INDEX_KEY_ENV: Final = "MANOBAL_IDENTITY_INDEX_KEY"
_ACTIVE_VERSION_ENV: Final = "MANOBAL_IDENTITY_KEK_ACTIVE"


class KeyManagementError(Exception):
    """Base class for key-management failures."""


class UnknownKeyVersionError(KeyManagementError):
    """A record was sealed under a key version this service does not hold.

    Raised rather than tolerated. A record that cannot be decrypted is a
    recoverable operational problem; a record that is silently skipped is a
    person who has quietly disappeared from the vault.
    """


@dataclass(frozen=True, slots=True)
class WrappedKey:
    """A data key encrypted under a key-encryption key."""

    kek_version: int
    nonce: bytes
    ciphertext: bytes


@runtime_checkable
class KeyManagementService(Protocol):
    """What the enclave is allowed to ask of its key store."""

    @property
    def active_kek_version(self) -> int:
        """The version new records are sealed under."""

    def wrap_data_key(self, data_key: bytes) -> WrappedKey: ...

    def unwrap_data_key(self, wrapped: WrappedKey) -> bytes: ...

    def compute_mac(self, message: bytes) -> bytes:
        """Keyed MAC for the blind index, computed inside the key boundary."""


class LocalKeyManagementService:
    """An in-memory stand-in for the HSM, for development and tests.

    Holding several key versions at once is not a convenience — it is how
    rotation works. A rotation adds a version and moves the active pointer;
    records sealed under earlier versions keep opening until they are re-sealed.
    """

    def __init__(
        self,
        keks: Mapping[int, bytes],
        active_version: int,
        index_key: bytes,
    ) -> None:
        if not keks:
            raise ValueError("A key store needs at least one key-encryption key.")
        for version, key in keks.items():
            if len(key) != KEY_BYTES:
                raise ValueError(
                    f"Key-encryption key v{version} must be 256 bits, "
                    f"got {len(key) * 8}."
                )
        if len(index_key) != KEY_BYTES:
            raise ValueError(
                f"The blind-index key must be 256 bits, got {len(index_key) * 8}."
            )
        if active_version not in keks:
            raise ValueError(
                f"The active key version v{active_version} is not held; "
                f"available versions are {sorted(keks)}."
            )
        self._keks = dict(keks)
        self._active_version = active_version
        self._index_key = index_key

    @classmethod
    def from_environment(cls) -> LocalKeyManagementService:
        """Load keys from ``MANOBAL_IDENTITY_KEK_V*`` and friends.

        Keys are base64-encoded. This exists so that no key material is ever
        written into a settings file or a repository.
        """
        keks: dict[int, bytes] = {}
        for name, value in os.environ.items():
            if not name.startswith(_KEK_ENV_PREFIX):
                continue
            suffix = name.removeprefix(_KEK_ENV_PREFIX)
            if not suffix.isdigit():
                continue
            keks[int(suffix)] = base64.b64decode(value)
        if not keks:
            raise KeyManagementError(
                f"No identity key-encryption keys found. Set at least "
                f"{_KEK_ENV_PREFIX}1 to a base64-encoded 256-bit key."
            )

        index_key_b64 = os.environ.get(_INDEX_KEY_ENV)
        if not index_key_b64:
            raise KeyManagementError(f"{_INDEX_KEY_ENV} is not set.")

        active = os.environ.get(_ACTIVE_VERSION_ENV)
        active_version = int(active) if active else max(keks)

        return cls(
            keks=keks,
            active_version=active_version,
            index_key=base64.b64decode(index_key_b64),
        )

    @property
    def active_kek_version(self) -> int:
        return self._active_version

    def wrap_data_key(self, data_key: bytes) -> WrappedKey:
        if len(data_key) != KEY_BYTES:
            raise ValueError(f"A data key must be 256 bits, got {len(data_key) * 8}.")
        nonce = os.urandom(NONCE_BYTES)
        kek = self._keks[self._active_version]
        ciphertext = AESGCM(kek).encrypt(nonce, data_key, self._wrap_aad())
        return WrappedKey(
            kek_version=self._active_version, nonce=nonce, ciphertext=ciphertext
        )

    def unwrap_data_key(self, wrapped: WrappedKey) -> bytes:
        kek = self._keks.get(wrapped.kek_version)
        if kek is None:
            raise UnknownKeyVersionError(
                f"This service does not hold key-encryption key "
                f"v{wrapped.kek_version}; available versions are "
                f"{sorted(self._keks)}. The record cannot be opened here."
            )
        return AESGCM(kek).decrypt(wrapped.nonce, wrapped.ciphertext, self._wrap_aad())

    def compute_mac(self, message: bytes) -> bytes:
        return hmac.new(self._index_key, message, sha256).digest()

    @staticmethod
    def _wrap_aad() -> bytes:
        """Domain separation, so a wrapped data key cannot be replayed as a field."""
        return b"manobal/identity/data-key"

    def __repr__(self) -> str:
        """Deliberately omits key material; a key in a traceback is a disclosure."""
        return (
            f"{type(self).__name__}(versions={sorted(self._keks)}, "
            f"active=v{self._active_version})"
        )

    __str__ = __repr__
