from __future__ import annotations

from datetime import datetime

import jwt
from pydantic import BaseModel, Field, ValidationError

from .config import Settings
from .errors import ApiError


class GrantClaims(BaseModel):
    sub: str = Field(pattern=r"^st_[a-z2-7]{16}$")
    token: str = Field(pattern=r"^st_[a-z2-7]{16}$")
    case_id: str = Field(pattern=r"^MB-[0-9]{4}$")
    actor: str = Field(min_length=2)
    actor_role: str = Field(min_length=2)
    scope_path: str = Field(min_length=1)
    purpose_code: str = Field(min_length=2, max_length=64)
    contact_note_due_at: datetime
    exp: datetime
    jti: str


def _grant_public_key(settings: Settings) -> str:
    configured = settings.grant_public_key_pem.get_secret_value()
    if configured.strip():
        return configured
    return settings.grant_public_key_file.read_text(encoding="utf-8")


def verify_grant(encoded: str, settings: Settings) -> GrantClaims:
    try:
        public_key = _grant_public_key(settings)
        payload = jwt.decode(
            encoded,
            public_key,
            algorithms=["EdDSA"],
            audience=settings.grant_audience,
            issuer=settings.grant_issuer,
            options={
                "require": [
                    "sub",
                    "token",
                    "case_id",
                    "actor",
                    "actor_role",
                    "scope_path",
                    "purpose_code",
                    "contact_note_due_at",
                    "exp",
                    "iat",
                    "jti",
                ]
            },
        )
        claims = GrantClaims.model_validate(payload)
        if claims.sub != claims.token:
            raise ValueError("subject binding")
        return claims
    except (OSError, jwt.PyJWTError, ValidationError, ValueError) as error:
        raise ApiError(
            "grant_invalid",
            "The identity grant is invalid or expired",
            hint="Request a new purpose-bound grant",
            status_code=403,
        ) from error
