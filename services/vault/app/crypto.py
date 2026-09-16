from __future__ import annotations

import base64
import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .key_provider import KeyProvider


def canonical_service_number(service_number: str) -> str:
    return "".join(service_number.upper().split())


async def subject_token(
    service_number: str,
    provider: KeyProvider,
) -> str:
    digest = await provider.token_digest(canonical_service_number(service_number))
    encoded = base64.b32encode(digest).decode("ascii").lower().rstrip("=")
    return f"st_{encoded[:16]}"


def encrypt_field(data_key: bytes, token: str, field: str, value: str) -> bytes:
    nonce = os.urandom(12)
    aad = f"{token}:{field}".encode()
    return nonce + AESGCM(data_key).encrypt(nonce, value.encode("utf-8"), aad)


def decrypt_field(data_key: bytes, token: str, field: str, value: bytes) -> str:
    if len(value) < 29:
        raise ValueError("Encrypted field is too short")
    aad = f"{token}:{field}".encode()
    plaintext = AESGCM(data_key).decrypt(value[:12], value[12:], aad)
    return plaintext.decode("utf-8")


@dataclass(frozen=True)
class EncryptedIdentity:
    token: str
    service_no_enc: bytes
    name_enc: bytes
    phone_enc: bytes | None
    posting_enc: bytes | None
    dek_wrapped: bytes
    kek_version: str


@dataclass(frozen=True)
class DecryptedIdentity:
    token: str
    service_no: str
    name: str
    phone: str | None
    posting: str | None


async def encrypt_identity(
    *,
    service_number: str,
    name: str,
    phone: str | None,
    posting: str | None,
    provider: KeyProvider,
) -> EncryptedIdentity:
    token = await subject_token(service_number, provider)
    data_key = bytearray(os.urandom(32))
    try:
        key_bytes = bytes(data_key)
        wrapped = await provider.wrap_key(key_bytes)
        return EncryptedIdentity(
            token=token,
            service_no_enc=encrypt_field(
                key_bytes,
                token,
                "service_no",
                canonical_service_number(service_number),
            ),
            name_enc=encrypt_field(key_bytes, token, "name", name),
            phone_enc=(
                encrypt_field(key_bytes, token, "phone", phone) if phone is not None else None
            ),
            posting_enc=(
                encrypt_field(key_bytes, token, "posting", posting) if posting is not None else None
            ),
            dek_wrapped=wrapped.ciphertext,
            kek_version=wrapped.version,
        )
    finally:
        for index in range(len(data_key)):
            data_key[index] = 0


async def decrypt_identity(
    *,
    token: str,
    service_no_enc: bytes,
    name_enc: bytes,
    phone_enc: bytes | None,
    posting_enc: bytes | None,
    dek_wrapped: bytes,
    kek_version: str,
    provider: KeyProvider,
) -> DecryptedIdentity:
    data_key = bytearray(await provider.unwrap_key(dek_wrapped, kek_version))
    try:
        key_bytes = bytes(data_key)
        return DecryptedIdentity(
            token=token,
            service_no=decrypt_field(
                key_bytes,
                token,
                "service_no",
                service_no_enc,
            ),
            name=decrypt_field(key_bytes, token, "name", name_enc),
            phone=(
                decrypt_field(key_bytes, token, "phone", phone_enc)
                if phone_enc is not None
                else None
            ),
            posting=(
                decrypt_field(key_bytes, token, "posting", posting_enc)
                if posting_enc is not None
                else None
            ),
        )
    finally:
        for index in range(len(data_key)):
            data_key[index] = 0
