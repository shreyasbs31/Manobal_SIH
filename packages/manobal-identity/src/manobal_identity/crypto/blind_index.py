"""Deterministic lookup into an encrypted vault (SDD §4.9, §5.1).

The vault must answer "which row is this service number?" without decrypting
every row to find out. The blind index is that answer: a keyed MAC of the
normalised service number, stored in a unique index.

**The blind index must never leave Zone 3.** Its determinism is the entire point
and also the entire danger — two systems holding the same index for the same
person could correlate their records without ever seeing a name. It is a lookup
key inside the enclave, never an identifier in a payload.

The MAC is computed inside the key-management boundary so that the index key,
like every other key in this enclave, is used but never held.
"""

from __future__ import annotations

import re
from typing import Final

from manobal_identity.crypto.kms import KeyManagementService

_SEPARATORS: Final = re.compile(r"[\s\-/\\._]+")
"""Forces write the same number as CRPF-1987-114523, CRPF 1987 114523, or
crpf/1987/114523. All three are one person."""

_DOMAIN: Final = b"manobal/identity/service-no/v1"
"""Domain separation, so this MAC cannot be replayed in another context."""


def normalise_service_no(service_no: str) -> str:
    """Reduce a service number to its canonical form.

    HRMS extracts are not typographically consistent, and a person who acquires
    two tokens because of a stray hyphen accumulates no baseline at all — they
    look like two people with half the history each. Normalisation is therefore
    a correctness requirement, not tidiness.
    """
    canonical = _SEPARATORS.sub("", service_no).strip().lower()
    if not canonical:
        raise ValueError("A service number cannot be empty once normalised.")
    return canonical


def blind_index(service_no: str, kms: KeyManagementService) -> str:
    """Return the hex lookup index for a service number."""
    canonical = normalise_service_no(service_no)
    return kms.compute_mac(_DOMAIN + b"\x00" + canonical.encode()).hex()
