"""Application-layer envelope encryption for the identity vault (NFR-SEC2).

The vault is encrypted twice over: PostgreSQL sits on encrypted storage, and
then every identifying column is separately encrypted here, before it ever
reaches the driver. The second layer is the one that matters, because it is the
one that survives a stolen dump, a rogue DBA and a mistaken backup restore. The
database sees ciphertext and nothing else.

The scheme is standard envelope encryption:

*   each vault row gets its own random **data key**;
*   the data key is wrapped by the **key-encryption key**, which lives in the
    HSM and never enters this process in production;
*   each field is sealed with AES-256-GCM under the row's data key.

Every seal is bound, through GCM's additional authenticated data, to the store,
the field and the subject token it belongs to. That binding is what stops a
ciphertext being *moved* — a name lifted into another person's row, or a mobile
number slid into the name column, will not open. Confidentiality alone would not
have caught either.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Final

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from manobal_identity.crypto.kms import (
    KEY_BYTES,
    NONCE_BYTES,
    KeyManagementService,
    WrappedKey,
)

_WRAPPED_FORMAT_VERSION: Final = 1
"""Leading byte of a serialised wrapped key, so the format can change later."""

_HEADER_BYTES: Final = 1 + 2 + NONCE_BYTES
"""Format version, KEK version, nonce."""


@dataclass(frozen=True, slots=True)
class SealedValue:
    """One encrypted field, as stored."""

    nonce: bytes
    ciphertext: bytes

    def __bytes__(self) -> bytes:
        return self.nonce + self.ciphertext

    @classmethod
    def from_bytes(cls, raw: bytes) -> SealedValue:
        if len(raw) <= NONCE_BYTES:
            raise ValueError("Sealed value is too short to contain a nonce.")
        return cls(nonce=raw[:NONCE_BYTES], ciphertext=raw[NONCE_BYTES:])


@dataclass(frozen=True, slots=True)
class RecordKey:
    """A row's data key, in the clear alongside its wrapped form.

    Instances are transient by intent: the plaintext ``data_key`` lives only as
    long as the request that needs it, while ``wrapped`` is what goes to the
    database.
    """

    data_key: bytes
    wrapped: bytes
    kek_version: int

    def __repr__(self) -> str:
        """Never render the data key; this object appears in tracebacks."""
        return f"RecordKey(kek_version={self.kek_version}, data_key=<redacted>)"


class EnvelopeCipher:
    """Seals and opens identity fields under per-record data keys."""

    def __init__(self, kms: KeyManagementService) -> None:
        self._kms = kms

    def new_record_key(self) -> RecordKey:
        """Mint a data key for a new vault row and wrap it for storage."""
        data_key = os.urandom(KEY_BYTES)
        wrapped = self._kms.wrap_data_key(data_key)
        return RecordKey(
            data_key=data_key,
            wrapped=_serialise(wrapped),
            kek_version=wrapped.kek_version,
        )

    def load_record_key(self, wrapped: bytes) -> RecordKey:
        """Recover a data key from its stored wrapped form."""
        parsed = _deserialise(wrapped)
        return RecordKey(
            data_key=self._kms.unwrap_data_key(parsed),
            wrapped=wrapped,
            kek_version=parsed.kek_version,
        )

    def seal(self, key: RecordKey, plaintext: str, *, aad: bytes) -> SealedValue:
        nonce = os.urandom(NONCE_BYTES)
        ciphertext = AESGCM(key.data_key).encrypt(nonce, plaintext.encode(), aad)
        return SealedValue(nonce=nonce, ciphertext=ciphertext)

    def open(self, key: RecordKey, sealed: SealedValue, *, aad: bytes) -> str:
        plaintext = AESGCM(key.data_key).decrypt(sealed.nonce, sealed.ciphertext, aad)
        return plaintext.decode()


def field_aad(field: str, subject_token: str) -> bytes:
    """The authenticated context binding a ciphertext to its column and row."""
    return f"subject_identity|{field}|{subject_token}".encode()


def _serialise(wrapped: WrappedKey) -> bytes:
    return (
        bytes([_WRAPPED_FORMAT_VERSION])
        + wrapped.kek_version.to_bytes(2, "big")
        + wrapped.nonce
        + wrapped.ciphertext
    )


def _deserialise(raw: bytes) -> WrappedKey:
    if len(raw) <= _HEADER_BYTES:
        raise ValueError("Wrapped key is too short to be well-formed.")
    if raw[0] != _WRAPPED_FORMAT_VERSION:
        raise ValueError(f"Unsupported wrapped-key format version {raw[0]}.")
    return WrappedKey(
        kek_version=int.from_bytes(raw[1:3], "big"),
        nonce=raw[3:_HEADER_BYTES],
        ciphertext=raw[_HEADER_BYTES:],
    )
