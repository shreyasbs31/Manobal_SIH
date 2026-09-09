"""OIDC bearer-token authentication (SDD §6.2, NFR-SEC3).

MANOBAL never sees a password. Personnel authenticate against the force identity
provider and arrive holding a signed JWT; this module verifies the signature
against the provider's published JWKS, checks the standard temporal and audience
claims, and turns the result into a :class:`Principal`.

The verification options are spelled out explicitly rather than left to library
defaults. Defaults change between releases, and an upgrade that silently stops
checking ``aud`` is not the kind of thing anyone notices in a diff.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import jwt
from jwt import PyJWKClient
from rest_framework import authentication, exceptions

from .config import OIDCConfig
from .predicates import mfa_is_satisfied
from .principal import Principal

if TYPE_CHECKING:
    from rest_framework.request import Request

#: Module-level so the JWKS is fetched and cached once per process rather than
#: once per request. An HTTP round trip to the identity provider on every API
#: call would dominate the latency budget in NFR-P1.
_jwks_client: PyJWKClient | None = None
_config: OIDCConfig | None = None


def config() -> OIDCConfig:
    global _config
    if _config is None:
        _config = OIDCConfig.from_settings()
    return _config


def _client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(config().jwks_url, cache_keys=True, lifespan=600)
    return _jwks_client


class OIDCBearerAuthentication(authentication.BaseAuthentication):
    """Verify a bearer JWT and attach the resulting principal.

    Returning ``None`` for a missing header means "not authenticated by this
    scheme", which lets DRF fall through to the permission layer and produce a
    401 with a proper ``WWW-Authenticate`` challenge. Raising here instead would
    turn every unauthenticated probe into a 500-shaped error.
    """

    keyword = "Bearer"

    def authenticate(self, request: Request) -> tuple[Principal, dict[str, Any]] | None:
        header = authentication.get_authorization_header(request).decode("latin-1")
        if not header:
            return None
        parts = header.split()
        if len(parts) != 2 or parts[0] != self.keyword:
            raise exceptions.AuthenticationFailed("MB-4010: malformed Authorization header")

        claims = self._verify(parts[1])
        settings_ = config()
        try:
            principal = Principal.from_claims(
                claims, second_factor_methods=sorted(settings_.second_factor_methods)
            )
        except (KeyError, ValueError) as exc:
            # The reason is logged for operators but not returned. Telling a
            # caller which claim was unacceptable helps them craft a better
            # forgery far more than it helps them fix their configuration.
            raise exceptions.AuthenticationFailed("MB-4011: token claims unusable") from exc

        if not mfa_is_satisfied(
            principal,
            required_roles=settings_.mfa_required_roles,
            accepted_methods=settings_.second_factor_methods,
        ):
            raise exceptions.AuthenticationFailed(
                "MB-4012: this role requires a second authentication factor"
            )
        return principal, claims

    def authenticate_header(self, request: Request) -> str:
        return f'{self.keyword} realm="manobal"'

    # ------------------------------------------------------------- internals --

    def _verify(self, token: str) -> dict[str, Any]:
        settings_ = config()
        try:
            key = _client().get_signing_key_from_jwt(token).key
            decoded: dict[str, Any] = jwt.decode(
                token,
                key,
                algorithms=list(settings_.algorithms),
                audience=settings_.audience,
                issuer=settings_.issuer,
                leeway=settings_.leeway_seconds,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    "require": ["exp", "iat", "iss", "aud", "sub"],
                },
            )
        except jwt.ExpiredSignatureError as exc:
            raise exceptions.AuthenticationFailed("MB-4013: token expired") from exc
        except jwt.PyJWTError as exc:
            raise exceptions.AuthenticationFailed("MB-4010: token verification failed") from exc
        return decoded
