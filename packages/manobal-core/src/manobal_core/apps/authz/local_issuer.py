"""Local RS256 issuer that stands in for the force IdP (SDD §6.2).

Production never loads this module. The PEM next to it is a development key:
it signs synthetic principals against a laptop JWKS, and it is useless against
any deployment that does not explicitly enable ``LOCAL_ISSUER_ENABLED``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.core.exceptions import ImproperlyConfigured

from manobal_core.apps.governance.enums import Role

ISSUER = "https://localhost/manobal-dev"
AUDIENCE = "manobal-core"
KEY_ID = "manobal-dev-1"
TOKEN_TTL = timedelta(hours=8)
_PEM_PATH = Path(__file__).with_name("dev_issuer.pem")
_OFFICER_ROLES = frozenset(
    {
        Role.WELFARE_OFFICER,
        Role.MEDICAL_OFFICER,
        Role.COMMANDER,
        Role.WDEC_AUDITOR,
    }
)


@lru_cache(maxsize=1)
def private_key() -> rsa.RSAPrivateKey:
    material = _PEM_PATH.read_bytes()
    loaded = serialization.load_pem_private_key(material, password=None)
    if not isinstance(loaded, rsa.RSAPrivateKey):
        raise ImproperlyConfigured("dev issuer PEM is not an RSA private key")
    return loaded


def public_jwk() -> dict[str, str]:
    """JWKS member for ``GET /dev/jwks`` and in-process verification."""
    numbers = private_key().public_key().public_numbers()
    return {
        "kty": "RSA",
        "kid": KEY_ID,
        "use": "sig",
        "alg": "RS256",
        "n": _b64url(_int_to_bytes(numbers.n)),
        "e": _b64url(_int_to_bytes(numbers.e)),
    }


def mint_token(
    *,
    role: str,
    actor_id: str,
    force_code: str = "CAPF",
    unit_code: str = "",
    subject_token: str = "",
    scopes: str = "",
    ttl: timedelta = TOKEN_TTL,
    now: datetime | None = None,
) -> str:
    """Mint a bearer JWT with the same claim set a force IdP would issue."""
    if role not in Role.values:
        raise ValueError(f"unknown MANOBAL role: {role}")
    moment = now or datetime.now(tz=UTC)
    claims: dict[str, Any] = {
        "sub": actor_id,
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": int(moment.timestamp()),
        "nbf": int(moment.timestamp()),
        "exp": int((moment + ttl).timestamp()),
        "manobal_role": role,
        "force_code": force_code,
        "unit_code": unit_code,
        "amr": ["pwd", "otp"] if role in _OFFICER_ROLES or role == Role.INTEGRATION else ["pwd"],
        "sid": f"dev-{actor_id}",
    }
    if scopes:
        claims["scope"] = scopes
    if role == Role.PERSONNEL:
        claims["subject_token"] = subject_token or actor_id
    return jwt.encode(claims, private_key(), algorithm="RS256", headers={"kid": KEY_ID})


def _b64url(raw: bytes) -> str:
    import base64

    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _int_to_bytes(value: int) -> bytes:
    length = (value.bit_length() + 7) // 8
    return value.to_bytes(length, "big")
