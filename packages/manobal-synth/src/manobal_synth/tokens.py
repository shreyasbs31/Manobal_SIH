"""Deterministic pseudonymous identifiers.

Subject tokens are derived from ``(seed, index)`` rather than drawn from the
generation RNG. Two consequences matter. A token is reproducible from the seed
alone, so a ground-truth row can be matched to an observation row across two
separate runs. And a token carries no ordering information an analyst could use
to recover the generation index, which keeps the synthetic corpus shaped like the
real one: SDD §4.9 tokens are opaque, and a fixture that leaked structure would
let tests pass that production data would fail.
"""

from __future__ import annotations

import hashlib

#: RFC 4648 base32 alphabet, lowercased. Excludes 0, 1, 8 and 9 so that a token
#: read aloud or transcribed from a log cannot be confused with O, I, l or B.
_ALPHABET = "abcdefghijklmnopqrstuvwxyz234567"

TOKEN_PREFIX = "st_"
TOKEN_BODY_CHARS = 26

_BITS_PER_CHAR = 5
_DIGEST_BYTES = (TOKEN_BODY_CHARS * _BITS_PER_CHAR + 7) // 8


def _base32ish(payload: bytes, chars: int) -> str:
    value = int.from_bytes(payload, "big")
    return "".join(
        _ALPHABET[(value >> (_BITS_PER_CHAR * i)) & 0x1F] for i in reversed(range(chars))
    )


def subject_token(seed: int, index: int) -> str:
    """Return the stable token for the ``index``-th subject of a ``seed``."""
    material = f"manobal-synth/subject/{seed}/{index}".encode()
    digest = hashlib.blake2b(material, digest_size=_DIGEST_BYTES).digest()
    return TOKEN_PREFIX + _base32ish(digest, TOKEN_BODY_CHARS)


def sector_code(index: int) -> str:
    return f"sec_{index + 1:02d}"


def unit_code(index: int) -> str:
    return f"unit_{index + 1:04d}"


def incident_id(seed: int, index: int) -> str:
    material = f"manobal-synth/incident/{seed}/{index}".encode()
    digest = hashlib.blake2b(material, digest_size=8).digest()
    return "inc_" + _base32ish(digest, 12)
