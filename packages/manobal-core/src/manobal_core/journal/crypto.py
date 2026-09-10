"""Per-subject journal keys, wrapped under a process master key.

The data key lives in the governance store. Ciphertext lives in the psych
store. Erasure destroys the key, so a restored psy backup cannot be read.
"""

from __future__ import annotations

import base64
import os
from typing import Any, cast

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings
from django.utils import timezone

from manobal_core.apps.governance.models import JournalKey

NONCE_BYTES = 12
KEY_BYTES = 32


class JournalCryptoError(RuntimeError):
    """The master key is missing, or the subject key has been destroyed."""


def encrypt_body(subject_token: str, plaintext: str) -> tuple[bytes, bytes, str]:
    """Return ``(ciphertext, nonce, key_id)`` for storage on the psy row."""
    key = _live_key(subject_token)
    nonce = os.urandom(NONCE_BYTES)
    cipher = AESGCM(_unwrap(key))
    ciphertext = cipher.encrypt(nonce, plaintext.encode(), subject_token.encode())
    return ciphertext, nonce, key.key_id


def decrypt_body(subject_token: str, ciphertext: bytes, nonce: bytes, key_id: str) -> str:
    key = (
        JournalKey.objects.filter(
            subject_token=subject_token, key_id=key_id, destroyed_at__isnull=True
        )
        .order_by("-created_at")
        .first()
    )
    if key is None:
        raise JournalCryptoError("journal key is not available")
    cipher = AESGCM(_unwrap(key))
    return cipher.decrypt(nonce, bytes(ciphertext), subject_token.encode()).decode()


def destroy_keys(subject_token: str) -> int:
    """Wipe wrapped key material. A restored backup of psy alone is then mute."""
    rows = JournalKey.objects.filter(subject_token=subject_token, destroyed_at__isnull=True)
    count = rows.count()
    rows.update(destroyed_at=timezone.now(), wrapped_key=b"")
    return count


def _live_key(subject_token: str) -> JournalKey:
    existing = (
        JournalKey.objects.filter(subject_token=subject_token, destroyed_at__isnull=True)
        .order_by("-created_at")
        .first()
    )
    if existing is not None:
        return existing
    data_key = os.urandom(KEY_BYTES)
    key_id = f"jk_{os.urandom(8).hex()}"
    return JournalKey.objects.create(
        subject_token=subject_token,
        key_id=key_id,
        wrapped_key=_wrap(data_key, key_id),
    )


def _master() -> bytes:
    cfg = cast(dict[str, Any], getattr(settings, "JOURNAL", {}))
    raw = str(cfg.get("MASTER_KEY_B64") or "")
    if not raw:
        raise JournalCryptoError("MANOBAL_JOURNAL_MASTER_KEY is not set")
    key = base64.b64decode(raw)
    if len(key) != KEY_BYTES:
        raise JournalCryptoError("journal master key must be 32 bytes")
    return key


def _wrap(data_key: bytes, key_id: str) -> bytes:
    nonce = os.urandom(NONCE_BYTES)
    sealed = AESGCM(_master()).encrypt(nonce, data_key, key_id.encode())
    return nonce + sealed


def _unwrap(row: JournalKey) -> bytes:
    blob = bytes(row.wrapped_key)
    if len(blob) <= NONCE_BYTES:
        raise JournalCryptoError("journal key has been destroyed")
    nonce, sealed = blob[:NONCE_BYTES], blob[NONCE_BYTES:]
    return AESGCM(_master()).decrypt(nonce, sealed, row.key_id.encode())
