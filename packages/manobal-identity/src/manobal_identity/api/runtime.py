"""Process-wide vault handle. Tests replace it; production builds it once."""

from __future__ import annotations

import base64
from threading import Lock

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from django.conf import settings

from manobal_identity.apps.vault.models import DatabaseReplayGuard
from manobal_identity.apps.vault.services import IdentityVault
from manobal_identity.crypto.kms import LocalKeyManagementService

_lock = Lock()
_vault: IdentityVault | None = None


def configure_vault(vault: IdentityVault | None) -> None:
    """Install (or clear) the vault used by the HTTP views.

    Tests call this with a fixture vault so they do not depend on environment
    key material. Production never calls it — :func:`get_vault` builds one.
    """
    global _vault
    with _lock:
        _vault = vault


def get_vault() -> IdentityVault:
    global _vault
    if _vault is not None:
        return _vault
    with _lock:
        if _vault is None:
            _vault = _build_vault()
        return _vault


def _build_vault() -> IdentityVault:
    trusted: dict[str, Ed25519PublicKey] = {}
    for key_id, material in settings.GRANT_ISSUER_KEYS.items():
        trusted[key_id] = Ed25519PublicKey.from_public_bytes(base64.b64decode(material))
    return IdentityVault(
        kms=LocalKeyManagementService.from_environment(),
        replay_guard=DatabaseReplayGuard(),
        trusted_keys=trusted,
    )
