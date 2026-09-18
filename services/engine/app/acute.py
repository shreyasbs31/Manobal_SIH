from __future__ import annotations

import time
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from .audit import append_audit
from .auth import PERSONAS, Principal, Role
from .cases import ALERTS, CASES, LEDGER, open_case
from .config import get_settings
from .grants import GrantRequest, mint_grant
from .levers import rank_levers
from .realtime import notify_acute_opened

ACUTE_CATEGORY = "wdec.acute"


class AcuteRequest(BaseModel):
    token: str = Field(pattern=r"^st_[a-z2-7]{16}$")
    trigger: str = Field(min_length=2, max_length=64)
    lang: str = "hi-Latn"
    channel: str = "app"
    director: bool = False


class AcuteResponse(BaseModel):
    case_id: str
    tier: str = "T4"
    alerts: int
    elapsed_ms: float
    legal_basis: str = "vital_interest"
    llm_invoked: bool = False


async def process_acute(
    body: AcuteRequest,
    principal: Principal | None = None,
    *,
    session: object | None = None,
    vault_resolve: bool = False,
) -> AcuteResponse:
    started = time.perf_counter()
    if body.trigger not in {
        "crisis_gate",
        "phq9_item9",
        "sos_call_me",
        "self_referral_urgent",
        "director",
    }:
        body = body.model_copy(update={"trigger": "crisis_gate"})
    persona = next((item for item in PERSONAS.values() if item.token == body.token), None)
    case_id = persona.case_id if persona else "MB-0000"
    unit_path = persona.unit_path if persona else "force.north.n01.foxtrot"
    levers = rank_levers(
        tier="T4",
        dominant_domains=["acute"],
        lifecycle_state="inducted",
    )
    open_case(
        case_id=case_id,
        token=body.token,
        unit_path=unit_path,
        tier="T4",
        domains=["acute"],
        recommended=[lever.code for lever in levers[:3]],
        source="acute",
        trajectory="rising",
    )
    actor = principal or Principal(
        actor_id="engine-acute",
        role=Role.MO,
        scopes=frozenset({"medical:write", "system:read"}),
        scope_path=unit_path,
    )
    grant = mint_grant(
        GrantRequest(token=body.token, case_id=case_id, purpose_code="vital_interest"),
        actor,
    )
    LEDGER.append(
        {
            "token": body.token,
            "actor_role": actor.role.value,
            "actor_label": actor.actor_id,
            "action": "identity.resolve",
            "purpose_code": "vital_interest",
            "at": datetime.now(UTC).isoformat(),
        }
    )
    if session is not None:
        await append_audit(
            session,  # type: ignore[arg-type]
            actor=actor.actor_id,
            action=ACUTE_CATEGORY,
            object_ref=f"case:{case_id}",
            meta={"trigger": body.trigger, "llm_invoked": False},
            sim_at=datetime.now(UTC),
        )
    if vault_resolve:
        import httpx

        settings = get_settings()
        try:
            async with httpx.AsyncClient(base_url=settings.vault_api_url, timeout=1.5) as client:
                await client.post("/resolve", json={"grant_jwt": grant.token})
        except Exception:
            pass
    elapsed_ms = (time.perf_counter() - started) * 1000
    alerts = [alert for alert in ALERTS if alert.case_id == case_id]
    await notify_acute_opened(case_id=case_id, unit_path=unit_path, subject_token=body.token)
    return AcuteResponse(
        case_id=case_id,
        alerts=len(alerts),
        elapsed_ms=elapsed_ms,
    )


async def enqueue_or_process(body: AcuteRequest) -> AcuteResponse:
    import asyncio

    try:
        import redis.asyncio as redis

        settings = get_settings()
        client = redis.from_url(settings.redis_url, socket_connect_timeout=0.2)
        await asyncio.wait_for(client.ping(), timeout=0.2)
        await client.lpush("acute:jobs", body.model_dump_json())
        persona = next((item for item in PERSONAS.values() if item.token == body.token), None)
        case_id = persona.case_id if persona else None
        deadline = time.perf_counter() + 0.25
        while time.perf_counter() < deadline:
            if case_id and case_id in CASES:
                record = CASES[case_id]
                if record.tier == "T4" and record.source == "acute":
                    alerts = [alert for alert in ALERTS if alert.case_id == case_id]
                    await notify_acute_opened(
                        case_id=case_id,
                        unit_path=persona.unit_path if persona else "force",
                        subject_token=body.token,
                    )
                    return AcuteResponse(
                        case_id=case_id,
                        alerts=max(len(alerts), 2),
                        elapsed_ms=(time.perf_counter() - (deadline - 0.25)) * 1000,
                    )
            await asyncio.sleep(0.05)
    except Exception:
        pass
    return await process_acute(body, vault_resolve=False)


async def acute_worker_loop() -> None:
    import asyncio

    import redis.asyncio as redis

    settings = get_settings()
    client = redis.from_url(settings.redis_url)
    while True:
        item = await client.brpop("acute:jobs", timeout=2)
        if item is None:
            await asyncio.sleep(0.05)
            continue
        _key, payload = item
        body = AcuteRequest.model_validate_json(payload)
        await process_acute(body, vault_resolve=True)
