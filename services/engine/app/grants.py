from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import jwt
from pydantic import BaseModel, Field

from .auth import Principal
from .config import Settings, get_settings


class GrantRequest(BaseModel):
    token: str = Field(pattern=r"^st_[a-z2-7]{16}$")
    case_id: str = Field(pattern=r"^MB-[0-9]{4}$")
    purpose_code: str = Field(min_length=2, max_length=64)
    ttl_days: int = Field(default=14, ge=1, le=14)


class GrantToken(BaseModel):
    token: str
    expires_at: datetime
    contact_note_due_at: datetime


def _grant_private_key(settings: Settings) -> str:
    configured = settings.grant_private_key_pem.get_secret_value()
    if configured.strip():
        return configured
    return settings.grant_private_key_file.read_text(encoding="utf-8")


def mint_grant(
    request: GrantRequest,
    principal: Principal,
    settings: Settings | None = None,
) -> GrantToken:
    active_settings = settings or get_settings()
    now = datetime.now(UTC)
    expires = now + timedelta(days=request.ttl_days)
    contact_note_due = now + timedelta(hours=24)
    private_key = _grant_private_key(active_settings)
    claims = {
        "iss": active_settings.grant_issuer,
        "aud": active_settings.grant_audience,
        "sub": request.token,
        "token": request.token,
        "case_id": request.case_id,
        "actor": principal.actor_id,
        "actor_role": principal.role.value,
        "scope_path": principal.scope_path,
        "purpose_code": request.purpose_code,
        "contact_note_due_at": int(contact_note_due.timestamp()),
        "iat": now,
        "exp": expires,
        "jti": str(uuid.uuid4()),
    }
    encoded = jwt.encode(claims, private_key, algorithm="EdDSA")
    return GrantToken(
        token=encoded,
        expires_at=expires,
        contact_note_due_at=contact_note_due,
    )
