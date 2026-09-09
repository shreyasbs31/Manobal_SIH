"""Typed, validated view of the OIDC settings.

Django settings are an untyped namespace, which is tolerable for a page size and
not tolerable for the parameters that decide whether a token is trusted. Reading
``settings.OIDC["AUDIENCE"]`` at each call site yields ``object``, so a typo in a
key name or a string where a list belongs surfaces as a runtime failure during
an authentication attempt — the worst possible moment to discover it.

Parsing once into a frozen dataclass moves those failures to process start and
gives the verification code real types to work with.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def _str(config: dict[str, Any], key: str, *, required: bool = True) -> str:
    value = config.get(key)
    if not isinstance(value, str) or (required and not value):
        msg = f"OIDC[{key!r}] must be a non-empty string, got {value!r}"
        raise ImproperlyConfigured(msg)
    return value


def _str_tuple(config: dict[str, Any], key: str) -> tuple[str, ...]:
    value = config.get(key)
    if not isinstance(value, (list, tuple)) or not all(isinstance(v, str) for v in value):
        msg = f"OIDC[{key!r}] must be a sequence of strings, got {value!r}"
        raise ImproperlyConfigured(msg)
    return tuple(value)


@dataclass(frozen=True, slots=True)
class OIDCConfig:
    issuer: str
    audience: str
    jwks_url: str
    algorithms: tuple[str, ...]
    leeway_seconds: int
    mfa_required_roles: frozenset[str]
    second_factor_methods: frozenset[str]

    @classmethod
    def from_settings(cls) -> OIDCConfig:
        config: dict[str, Any] = dict(settings.OIDC)
        algorithms = _str_tuple(config, "ALGORITHMS")

        # Refusing "none" explicitly, even though PyJWT also rejects it. The
        # algorithm-confusion attack — presenting an unsigned token to a verifier
        # that honours the header's `alg` — is the canonical JWT vulnerability,
        # and the check costs nothing.
        if any(alg.lower() == "none" for alg in algorithms):
            msg = "OIDC['ALGORITHMS'] must not include 'none'"
            raise ImproperlyConfigured(msg)

        issuer = _str(config, "ISSUER")
        jwks_url = config.get("JWKS_URL") or f"{issuer.rstrip('/')}/protocol/openid-connect/certs"

        leeway = config.get("LEEWAY_SECONDS", 0)
        if not isinstance(leeway, int) or isinstance(leeway, bool) or not 0 <= leeway <= 300:
            msg = f"OIDC['LEEWAY_SECONDS'] must be an int within 0-300, got {leeway!r}"
            raise ImproperlyConfigured(msg)

        return cls(
            issuer=issuer,
            audience=_str(config, "AUDIENCE"),
            jwks_url=str(jwks_url),
            algorithms=algorithms,
            leeway_seconds=leeway,
            mfa_required_roles=frozenset(_str_tuple(config, "MFA_REQUIRED_ROLES")),
            second_factor_methods=frozenset(
                m.lower() for m in _str_tuple(config, "SECOND_FACTOR_METHODS")
            ),
        )
