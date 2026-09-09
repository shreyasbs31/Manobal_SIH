"""Subject-token minting (SDD FR-2.4, §5.1).

A subject token is the only name the analytics plane ever knows a person by. It
is drawn from the operating system's CSPRNG and is *not* derived from the
service number — not by hashing, not by encryption, not by a keyed function of
any kind.

That choice is deliberate and worth stating plainly, because a keyed hash of the
service number would have been simpler. Service numbers are low-entropy and
structured: a force prefix, a year, a short serial. Anyone who obtained the
derivation key could enumerate the entire force offline and rebuild the mapping
without ever touching the vault. A random token has no such preimage. The cost
is that the mapping must be *stored*, which is precisely what the vault is for,
and storing it is what makes every resolution auditable.
"""

from __future__ import annotations

import base64
import secrets
from typing import Final

SUBJECT_TOKEN_PREFIX: Final = "st_"  # noqa: S105 — a label, not a credential
"""Marks a token in logs, dumps and payloads so it is never mistaken for a name."""

_TOKEN_BYTES: Final = 32
"""256 bits. Guessing is not an attack path at this width."""


def mint_subject_token() -> str:
    """Return a fresh, unpredictable subject token.

    Takes no arguments, so there is nothing it could be derived from.
    """
    body = base64.b32encode(secrets.token_bytes(_TOKEN_BYTES)).decode().lower()
    return SUBJECT_TOKEN_PREFIX + body.rstrip("=")
