from __future__ import annotations

import hmac
import json
import os
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated, Literal, cast

from fastapi import Depends, FastAPI, Header, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .crypto import decrypt_identity, encrypt_field, encrypt_identity
from .database import close_database, get_session, vault_ping
from .errors import ApiError, install_error_handlers
from .grants import verify_grant
from .key_provider import KeyProvider, build_key_provider
from .rate_limit import (
    InMemoryResolveRateLimiter,
    RedisResolveRateLimiter,
    ResolveRateLimiter,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.key_provider = build_key_provider(settings)
    try:
        limiter: ResolveRateLimiter = RedisResolveRateLimiter(
            settings.redis_url,
            limit=settings.resolve_rate_limit,
            window_seconds=settings.resolve_window_seconds,
        )
        await limiter.allow("__startup_probe__")
    except Exception:
        limiter = InMemoryResolveRateLimiter(
            limit=settings.resolve_rate_limit,
            window_seconds=settings.resolve_window_seconds,
        )
    app.state.resolve_limiter = limiter
    yield
    await cast(KeyProvider, app.state.key_provider).close()
    await cast(ResolveRateLimiter, app.state.resolve_limiter).close()
    await close_database()


app = FastAPI(
    title="MANOBAL identity vault",
    version="0.1.0",
    description="Directional tokenisation and purpose-bound identity resolution",
    lifespan=lifespan,
)
install_error_handlers(app)


@app.middleware("http")
async def request_context(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    trace_id = request.headers.get("x-trace-id", str(uuid.uuid4()))
    request.state.trace_id = trace_id
    response = await call_next(request)
    response.headers["x-trace-id"] = trace_id
    response.headers["x-content-type-options"] = "nosniff"
    response.headers["cache-control"] = "no-store"
    response.headers["content-security-policy"] = "default-src 'none'"
    return response


class TokeniseRequest(BaseModel):
    service_no: str = Field(pattern=r"^SYN-[A-Z0-9-]{4,32}$")
    name: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=32)
    posting: str | None = Field(default=None, max_length=200)
    synthetic: Literal[True] = True


class TokeniseResponse(BaseModel):
    token: str
    synthetic: bool = True


class ResolveRequest(BaseModel):
    grant_jwt: str = Field(min_length=64)


class ResolveResponse(BaseModel):
    token: str
    service_no: str
    name: str
    phone: str | None
    posting: str | None
    case_id: str
    purpose_code: str
    synthetic: bool = True


class NomineeRequest(BaseModel):
    token: str = Field(pattern=r"^st_[a-z2-7]{16}$")
    payload: dict[str, str]
    synthetic: Literal[True] = True


class HealthResponse(BaseModel):
    status: str
    service: str = "vault"
    database: bool
    key_provider: bool
    core_settings_isolated: bool
    at: datetime


def key_provider(request: Request) -> KeyProvider:
    return cast(KeyProvider, request.app.state.key_provider)


def resolve_limiter(request: Request) -> ResolveRateLimiter:
    return cast(ResolveRateLimiter, request.app.state.resolve_limiter)


async def require_ingest(
    x_ingest_token: Annotated[str | None, Header(alias="x-ingest-token")] = None,
) -> None:
    expected = settings.tokenise_ingest_secret.get_secret_value()
    if x_ingest_token is None or not hmac.compare_digest(x_ingest_token, expected):
        raise ApiError(
            "ingest_unauthorized",
            "The ingest credential is invalid",
            hint="Use the configured integration identity",
            status_code=401,
        )


@app.post("/tokenise", response_model=TokeniseResponse)
async def tokenise(
    body: TokeniseRequest,
    _authorized: Annotated[None, Depends(require_ingest)],
    session: Annotated[AsyncSession, Depends(get_session)],
    provider: Annotated[KeyProvider, Depends(key_provider)],
) -> TokeniseResponse:
    encrypted = await encrypt_identity(
        service_number=body.service_no,
        name=body.name,
        phone=body.phone,
        posting=body.posting,
        provider=provider,
    )
    await session.execute(
        text(
            """
            INSERT INTO identity (
                token, service_no_enc, name_enc, phone_enc, posting_enc,
                dek_wrapped, kek_version
            )
            VALUES (
                :token, :service_no_enc, :name_enc, :phone_enc, :posting_enc,
                :dek_wrapped, :kek_version
            )
            ON CONFLICT (token) DO UPDATE SET
                service_no_enc = EXCLUDED.service_no_enc,
                name_enc = EXCLUDED.name_enc,
                phone_enc = EXCLUDED.phone_enc,
                posting_enc = EXCLUDED.posting_enc,
                dek_wrapped = EXCLUDED.dek_wrapped,
                kek_version = EXCLUDED.kek_version
            """
        ),
        {
            "token": encrypted.token,
            "service_no_enc": encrypted.service_no_enc,
            "name_enc": encrypted.name_enc,
            "phone_enc": encrypted.phone_enc,
            "posting_enc": encrypted.posting_enc,
            "dek_wrapped": encrypted.dek_wrapped,
            "kek_version": encrypted.kek_version,
        },
    )
    await session.commit()
    return TokeniseResponse(token=encrypted.token)


@app.post("/resolve", response_model=ResolveResponse)
async def resolve(
    body: ResolveRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    provider: Annotated[KeyProvider, Depends(key_provider)],
    limiter: Annotated[ResolveRateLimiter, Depends(resolve_limiter)],
) -> ResolveResponse:
    grant = verify_grant(body.grant_jwt, settings)
    if not await limiter.allow(grant.actor):
        raise ApiError(
            "resolve_rate_limited",
            "The identity reveal limit has been reached",
            hint="Wait before requesting another reveal",
            status_code=429,
        )
    row = (
        (
            await session.execute(
                text(
                    """
                SELECT
                    token,
                    service_no_enc,
                    name_enc,
                    phone_enc,
                    posting_enc,
                    dek_wrapped,
                    kek_version
                FROM identity
                WHERE token = :token
                """
                ),
                {"token": grant.token},
            )
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise ApiError(
            "identity_not_found",
            "The granted identity was not found",
            hint="Check the case and request a new grant",
            status_code=404,
        )
    decrypted = await decrypt_identity(
        token=str(row["token"]),
        service_no_enc=bytes(row["service_no_enc"]),
        name_enc=bytes(row["name_enc"]),
        phone_enc=bytes(row["phone_enc"]) if row["phone_enc"] is not None else None,
        posting_enc=(bytes(row["posting_enc"]) if row["posting_enc"] is not None else None),
        dek_wrapped=bytes(row["dek_wrapped"]),
        kek_version=str(row["kek_version"]),
        provider=provider,
    )
    await session.execute(
        text(
            """
            SELECT id
              FROM append_resolve_log(
                :token,
                :requester,
                :case_id,
                :purpose_code,
                clock_timestamp()
              )
            """
        ),
        {
            "token": grant.token,
            "requester": grant.actor,
            "case_id": grant.case_id,
            "purpose_code": grant.purpose_code,
        },
    )
    await session.commit()
    return ResolveResponse(
        token=decrypted.token,
        service_no=decrypted.service_no,
        name=decrypted.name,
        phone=decrypted.phone,
        posting=decrypted.posting,
        case_id=grant.case_id,
        purpose_code=grant.purpose_code,
    )


@app.post("/nominee", response_model=TokeniseResponse)
async def store_nominee(
    body: NomineeRequest,
    _authorized: Annotated[None, Depends(require_ingest)],
    session: Annotated[AsyncSession, Depends(get_session)],
    provider: Annotated[KeyProvider, Depends(key_provider)],
) -> TokeniseResponse:
    data_key = bytearray(os.urandom(32))
    try:
        key_bytes = bytes(data_key)
        wrapped = await provider.wrap_key(key_bytes)
        payload = json.dumps(
            body.payload,
            sort_keys=True,
            separators=(",", ":"),
        )
        payload_enc = encrypt_field(
            key_bytes,
            body.token,
            "nominee_payload",
            payload,
        )
    finally:
        for index in range(len(data_key)):
            data_key[index] = 0
    await session.execute(
        text(
            """
            INSERT INTO nominee_store (
                token, payload_enc, dek_wrapped, kek_version
            )
            VALUES (:token, :payload_enc, :dek_wrapped, :kek_version)
            ON CONFLICT (token) DO UPDATE SET
                payload_enc = EXCLUDED.payload_enc,
                dek_wrapped = EXCLUDED.dek_wrapped,
                kek_version = EXCLUDED.kek_version
            """
        ),
        {
            "token": body.token,
            "payload_enc": payload_enc,
            "dek_wrapped": wrapped.ciphertext,
            "kek_version": wrapped.version,
        },
    )
    await session.commit()
    return TokeniseResponse(token=body.token)


@app.get("/health", response_model=HealthResponse)
async def health(
    provider: Annotated[KeyProvider, Depends(key_provider)],
) -> HealthResponse | JSONResponse:
    database_ok = await vault_ping()
    try:
        key_ok = len(await provider.token_digest("health-check")) == 32
    except Exception:
        key_ok = False
    core_isolated = not any(
        os.environ.get(name) for name in ("CORE_DATABASE_URL", "CORE_DB_HOST", "CORE_DB_NAME")
    )
    response = HealthResponse(
        status="ok" if database_ok and key_ok and core_isolated else "error",
        database=database_ok,
        key_provider=key_ok,
        core_settings_isolated=core_isolated,
        at=datetime.now(UTC),
    )
    if response.status != "ok":
        return JSONResponse(status_code=503, content=response.model_dump(mode="json"))
    return response
