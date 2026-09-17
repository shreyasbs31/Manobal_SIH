from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Annotated

import structlog
from fastapi import Depends, FastAPI, Path, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .audit import AuditVerification, append_audit
from .auth import (
    OFFICER_PERSONAS,
    PERSONAS,
    DemoLoginRequest,
    LoginResponse,
    Principal,
    Role,
    mint_access_token,
    principal_for_demo,
)
from .config import get_settings, live_providers_enabled
from .calls import acs_configured
from .providers.endpoints import foundry_is_live
from .database import apply_rls_context, close_database, core_ping, get_session
from .errors import ApiError, install_error_handlers
from .grants import GrantRequest, GrantToken, mint_grant
from .live import router as live_router
from .logging import configure_logging
from .passkeys import (
    PasskeyOptionsRequest,
    PasskeyOptionsResponse,
    PasskeyVerifyRequest,
    authentication_options,
    registration_options,
    verify_authentication,
    verify_registration,
)
from .personnel import router as personnel_router
from .security import RowPredicate, require
from .selftest import SelfTestReport, run_selftest
from .sim_clock import ClockState, ClockUpdate, get_clock, update_clock
from .voice.session import voice_router

configure_logging()
logger = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    if os.environ.get("MANOBAL_REQUIRE_LIVE_PROVIDERS") == "1" or settings.manobal_require_live_providers:
        missing = settings.missing_live_provider_names()
        if missing:
            raise RuntimeError("Missing live provider names: " + ", ".join(missing))
    report = await run_selftest()
    app.state.startup_selftest = report
    await logger.ainfo(
        "startup_selftest",
        healthy=report.healthy,
        vault_database_isolated=report.vault_database_isolated,
        vault_identity_keys_isolated=report.vault_identity_keys_isolated,
    )
    yield
    await close_database()


app = FastAPI(
    title="MANOBAL engine",
    version="0.1.0",
    description="Token-only foundation API",
    lifespan=lifespan,
)
install_error_handlers(app)
app.include_router(live_router)
app.include_router(personnel_router)
app.include_router(voice_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["authorization", "content-type", "x-trace-id"],
)


@app.middleware("http")
async def request_context(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    trace_id = request.headers.get("x-trace-id", str(uuid.uuid4()))
    request.state.trace_id = trace_id
    structlog.contextvars.bind_contextvars(trace_id=trace_id)
    started = datetime.now(UTC)
    try:
        response = await call_next(request)
        elapsed = (datetime.now(UTC) - started).total_seconds()
        from .observability import record_request

        record_request(request.url.path, elapsed, response.status_code)
        response.headers["x-trace-id"] = trace_id
        response.headers["x-content-type-options"] = "nosniff"
        response.headers["referrer-policy"] = "no-referrer"
        response.headers["permissions-policy"] = "camera=(), geolocation=(), microphone=()"
        response.headers["content-security-policy"] = "default-src 'none'; frame-ancestors 'none'"
        if settings.manobal_mode != "demo":
            response.headers["strict-transport-security"] = "max-age=31536000; includeSubDomains"
        return response
    finally:
        structlog.contextvars.clear_contextvars()


class DemoCatalog(BaseModel):
    roles: list[str]
    personas: list[dict[str, object]]
    officer_personas: list[dict[str, object]]


class ModeResponse(BaseModel):
    mode: str
    foundry: bool = False
    acs: bool = False
    speech: bool = False
    translator: bool = False
    content_safety: bool = False
    web_pubsub: bool = False


class HealthResponse(BaseModel):
    status: str
    service: str = "engine"
    at: datetime


class EntraCallbackResponse(LoginResponse):
    oidc_stub: bool = True


class WelfareGrantBody(BaseModel):
    token: str = Field(pattern=r"^st_[a-z2-7]{16}$")
    purpose_code: str = Field(min_length=2, max_length=64)
    justification: str = Field(min_length=8, max_length=500)


@app.post("/api/v1/auth/demo-login", response_model=LoginResponse)
async def demo_login(request: DemoLoginRequest) -> LoginResponse:
    if settings.manobal_mode != "demo":
        raise ApiError(
            "demo_login_disabled",
            "Demo sign-in is not available in this mode",
            hint="Use the configured identity provider",
            status_code=404,
        )
    return mint_access_token(principal_for_demo(request))


@app.get("/api/v1/auth/demo-catalog", response_model=DemoCatalog)
async def demo_catalog() -> DemoCatalog:
    return DemoCatalog(
        roles=[role.value for role in Role],
        personas=[persona.model_dump() for persona in PERSONAS.values()],
        officer_personas=[persona.model_dump(mode="json") for persona in OFFICER_PERSONAS.values()],
    )


@app.post(
    "/api/v1/auth/passkey/register/options",
    response_model=PasskeyOptionsResponse,
)
async def passkey_register_options(
    request: PasskeyOptionsRequest,
) -> PasskeyOptionsResponse:
    return await registration_options(request)


@app.post(
    "/api/v1/auth/passkey/register/verify",
    response_model=LoginResponse,
)
async def passkey_register_verify(
    request: PasskeyVerifyRequest,
) -> LoginResponse:
    return await verify_registration(request)


@app.post(
    "/api/v1/auth/passkey/login/options",
    response_model=PasskeyOptionsResponse,
)
async def passkey_login_options(
    request: PasskeyOptionsRequest,
) -> PasskeyOptionsResponse:
    return await authentication_options(request)


@app.post(
    "/api/v1/auth/passkey/login/verify",
    response_model=LoginResponse,
)
async def passkey_login_verify(
    request: PasskeyVerifyRequest,
) -> LoginResponse:
    return await verify_authentication(request)


@app.get("/api/v1/auth/entra/callback", response_model=EntraCallbackResponse)
async def entra_callback(
    code: Annotated[str, Query(min_length=4)],
    app_role: str,
) -> EntraCallbackResponse:
    del code
    if settings.manobal_mode != "demo":
        raise ApiError(
            "oidc_exchange_not_configured",
            "The OIDC token exchange is not configured",
            hint="Configure Entra tenant and client settings",
            status_code=501,
        )
    mapped_role = settings.entra_role_map.get(app_role)
    if mapped_role is None:
        raise ApiError(
            "entra_role_unmapped",
            "The Entra app role is not mapped",
            hint="Ask an administrator to map the app role",
            status_code=403,
        )
    role = Role(mapped_role)
    login = mint_access_token(
        principal_for_demo(
            DemoLoginRequest(
                role=role,
                persona_id="arjun" if role is Role.PERSONNEL else None,
            )
        )
    )
    return EntraCallbackResponse(**login.model_dump(), oidc_stub=True)


@app.get("/api/v1/system/health", response_model=HealthResponse)
async def health() -> HealthResponse | JSONResponse:
    if not await core_ping():
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "dependency_unavailable",
                    "message": "The core database is not reachable",
                    "hint": "Check the core database container",
                }
            },
        )
    return HealthResponse(status="ok", at=datetime.now(UTC))


@app.get("/api/v1/system/mode", response_model=ModeResponse)
async def mode() -> ModeResponse:
    return ModeResponse(
        mode=settings.manobal_mode,
        foundry=foundry_is_live(settings),
        acs=acs_configured(settings),
        speech=bool(settings.speech_key.get_secret_value()) and live_providers_enabled(),
        translator=bool(settings.translator_key.get_secret_value()) and live_providers_enabled(),
        content_safety=bool(settings.content_safety_endpoint) and live_providers_enabled(),
        web_pubsub=bool(settings.webpubsub_connection_string),
    )


@app.get("/api/v1/system/selftest", response_model=SelfTestReport)
async def selftest() -> SelfTestReport:
    return await run_selftest()


@app.post("/api/v1/gov/audit/verify", response_model=AuditVerification)
async def audit_verify(
    principal: Annotated[
        Principal,
        Depends(require("gov:read", RowPredicate.GOVERNANCE)),
    ],
) -> AuditVerification:
    from .oversight import verify_chain

    del principal
    body = verify_chain()
    return AuditVerification(
        valid=bool(body["valid"]),
        checked=int(body["checked"]),
        broken_seq=int(body["broken_seq"]) if body["broken_seq"] is not None else None,
        head_hash=str(body["head_hash"]),
    )


@app.get("/api/v1/demo/clock", response_model=ClockState)
async def read_demo_clock(
    principal: Annotated[
        Principal,
        Depends(require("demo:write", RowPredicate.DEMO_CONTROL)),
    ],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ClockState:
    del principal
    return await get_clock(session)


@app.post("/api/v1/demo/clock", response_model=ClockState)
async def change_demo_clock(
    update: ClockUpdate,
    principal: Annotated[
        Principal,
        Depends(require("demo:write", RowPredicate.DEMO_CONTROL)),
    ],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ClockState:
    state = await update_clock(session, update)
    await append_audit(
        session,
        actor=principal.actor_id,
        action="sim_clock.changed",
        object_ref="sim_clock:1",
        meta={"running": state.running, "speed": state.speed},
        sim_at=state.sim_now,
    )
    return state


@app.post(
    "/api/v1/welfare/cases/{case_id}/grant",
    response_model=GrantToken,
)
async def create_case_grant(
    case_id: Annotated[str, Path(pattern=r"^MB-[0-9]{4}$")],
    body: WelfareGrantBody,
    principal: Annotated[
        Principal,
        Depends(require("welfare:write", RowPredicate.UNIT_SUBTREE)),
    ],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> GrantToken:
    await apply_rls_context(session, principal)
    case_token = await session.scalar(
        text('SELECT token FROM "case" WHERE id = :case_id'),
        {"case_id": case_id},
    )
    if case_token is None or str(case_token) != body.token:
        raise ApiError(
            "case_not_found",
            "The case was not found in the assigned unit",
            hint="Refresh the queue and retry",
            status_code=404,
        )
    grant = mint_grant(
        GrantRequest(
            token=body.token,
            case_id=case_id,
            purpose_code=body.purpose_code,
        ),
        principal,
    )
    now = datetime.now(UTC)
    await session.execute(
        text(
            """
            INSERT INTO case_grant (
                case_id, actor, purpose_code, justification, granted_at,
                expires_at, contact_note_due_at, sim_at
            )
            VALUES (
                :case_id, :actor, :purpose_code, :justification, :granted_at,
                :expires_at, :contact_note_due_at, :sim_at
            )
            """
        ),
        {
            "case_id": case_id,
            "actor": principal.actor_id,
            "purpose_code": body.purpose_code,
            "justification": body.justification,
            "granted_at": now,
            "expires_at": grant.expires_at,
            "contact_note_due_at": min(
                grant.contact_note_due_at,
                now + timedelta(hours=24),
            ),
            "sim_at": now,
        },
    )
    await session.commit()
    await append_audit(
        session,
        actor=principal.actor_id,
        action="identity.grant_created",
        object_ref=f"case:{case_id}",
        meta={"purpose_code": body.purpose_code},
        sim_at=now,
    )
    return grant
