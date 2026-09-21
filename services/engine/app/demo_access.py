from __future__ import annotations

import asyncio
import base64
import hashlib
import secrets
import time
import uuid
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from enum import StrEnum

import jwt
from fastapi import Request, Response
from pydantic import BaseModel, Field

from .auth import Role
from .config import Settings
from .errors import ApiError

_AUDIENCE = "manobal-demo-gate"
_ISSUER = "manobal-engine"
_OPERATOR_ROLES = frozenset({Role.ADMIN, Role.DIRECTOR})
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1


class DemoGateLevel(StrEnum):
    JUDGE = "judge"
    OPERATOR = "operator"


class DemoAccessRequest(BaseModel):
    code: str = Field(min_length=8, max_length=256)


class DemoAccessResponse(BaseModel):
    access: DemoGateLevel
    expires_in: int


class DemoAccessStatus(BaseModel):
    required: bool
    granted: bool
    access: DemoGateLevel | None = None


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def make_access_code_hash(code: str, *, salt: bytes | None = None) -> str:
    if len(code) < 8:
        raise ValueError("Access codes must contain at least 8 characters")
    active_salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(
        code.encode("utf-8"),
        salt=active_salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=32,
    )
    return (
        f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}"
        f"${_encode(active_salt)}${_encode(digest)}"
    )


def access_code_matches(code: str, encoded: str) -> bool:
    try:
        algorithm, raw_n, raw_r, raw_p, raw_salt, raw_digest = encoded.split("$", 5)
        if algorithm != "scrypt":
            return False
        expected = _decode(raw_digest)
        actual = hashlib.scrypt(
            code.encode("utf-8"),
            salt=_decode(raw_salt),
            n=int(raw_n),
            r=int(raw_r),
            p=int(raw_p),
            dklen=len(expected),
        )
        return secrets.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def validate_demo_gate_settings(settings: Settings) -> None:
    if not settings.demo_gate_required:
        return
    missing: list[str] = []
    if not settings.demo_gate_access_hash.get_secret_value():
        missing.append("DEMO_GATE_ACCESS_HASH")
    if not settings.demo_gate_operator_hash.get_secret_value():
        missing.append("DEMO_GATE_OPERATOR_HASH")
    if len(settings.demo_gate_jwt_secret.get_secret_value()) < 32:
        missing.append("DEMO_GATE_JWT_SECRET")
    if missing:
        raise RuntimeError("Missing or invalid demo gate settings: " + ", ".join(missing))


def access_level_for_code(code: str, settings: Settings) -> DemoGateLevel | None:
    if access_code_matches(code, settings.demo_gate_operator_hash.get_secret_value()):
        return DemoGateLevel.OPERATOR
    if access_code_matches(code, settings.demo_gate_access_hash.get_secret_value()):
        return DemoGateLevel.JUDGE
    return None


def mint_demo_gate(level: DemoGateLevel, settings: Settings) -> tuple[str, int]:
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=settings.demo_gate_minutes)
    token = jwt.encode(
        {
            "iss": _ISSUER,
            "aud": _AUDIENCE,
            "sub": f"demo:{level.value}",
            "level": level.value,
            "iat": now,
            "exp": expires,
            "jti": str(uuid.uuid4()),
        },
        settings.demo_gate_jwt_secret.get_secret_value(),
        algorithm="HS256",
    )
    return token, int((expires - now).total_seconds())


def decode_demo_gate(token: str, settings: Settings) -> DemoGateLevel:
    try:
        claims = jwt.decode(
            token,
            settings.demo_gate_jwt_secret.get_secret_value(),
            algorithms=["HS256"],
            audience=_AUDIENCE,
            issuer=_ISSUER,
        )
        return DemoGateLevel(str(claims["level"]))
    except (jwt.PyJWTError, KeyError, ValueError) as error:
        raise ApiError(
            "demo_access_required",
            "Enter the judge access code to continue",
            hint="Return to the access page",
            status_code=401,
        ) from error


def gate_level_from_request(request: Request, settings: Settings) -> DemoGateLevel:
    if not settings.demo_gate_required:
        return DemoGateLevel.OPERATOR
    token = request.cookies.get(settings.demo_gate_cookie_name)
    if not token:
        raise ApiError(
            "demo_access_required",
            "Enter the judge access code to continue",
            hint="Return to the access page",
            status_code=401,
        )
    return decode_demo_gate(token, settings)


def require_demo_role(request: Request, role: Role, settings: Settings) -> DemoGateLevel:
    level = gate_level_from_request(request, settings)
    if role in _OPERATOR_ROLES and level is not DemoGateLevel.OPERATOR:
        raise ApiError(
            "operator_access_required",
            "This role is reserved for the demo operator",
            hint="Use a judge-facing role",
            status_code=403,
        )
    return level


def set_gate_cookie(
    response: Response,
    *,
    token: str,
    max_age: int,
    settings: Settings,
) -> None:
    response.set_cookie(
        key=settings.demo_gate_cookie_name,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=settings.demo_gate_cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_gate_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.demo_gate_cookie_name,
        httponly=True,
        secure=settings.demo_gate_cookie_secure,
        samesite="lax",
        path="/",
    )


class DemoAccessLimiter:
    def __init__(self, *, attempts: int = 5, window_seconds: int = 15 * 60) -> None:
        self._attempts = attempts
        self._window_seconds = window_seconds
        self._events: defaultdict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def allow_attempt(self, client: str) -> bool:
        now = time.monotonic()
        async with self._lock:
            events = self._events[client]
            while events and events[0] <= now - self._window_seconds:
                events.popleft()
            if len(events) >= self._attempts:
                return False
            events.append(now)
            return True

    async def clear(self, client: str) -> None:
        async with self._lock:
            self._events.pop(client, None)


demo_access_limiter = DemoAccessLimiter()


def request_client_key(request: Request) -> str:
    # Behind Front Door the gateway copies the edge-observed socket IP into this header.
    # Front Door overwrites any client-supplied X-Azure-SocketIP and the gateway is not
    # reachable except through Front Door, so the value cannot be forged. Without it
    # (local development) fall back to the forwarded chain, then the direct peer.
    gateway_ip = request.headers.get("x-manobal-client-ip", "").strip()
    if gateway_ip:
        return gateway_ip
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"
