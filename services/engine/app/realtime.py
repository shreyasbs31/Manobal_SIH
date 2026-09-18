from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

import httpx
import jwt

from .auth import Principal, Role
from .config import Settings, get_settings

INDIVIDUAL_KEYS = frozenset({"token", "subject_token", "case_id", "person_id", "service_no"})

# Care desks only. Commander and HQ stay on aggregate groups without case keys.
ACUTE_OFFICER_ROLES = ("role:uwo", "role:mo", "role:counsellor")
WORLD_GROUPS = (
    "role:personnel",
    "role:uwo",
    "role:counsellor",
    "role:mo",
    "role:commander",
    "role:hq",
    "role:wdec",
    "role:director",
    "role:admin",
)


def acute_officer_groups(unit_path: str) -> list[str]:
    return [*ACUTE_OFFICER_ROLES, f"unit:{unit_path}"]


def groups_for(principal: Principal) -> list[str]:
    groups = [f"role:{principal.role.value}", f"unit:{principal.scope_path}"]
    if principal.role is Role.PERSONNEL and principal.subject_token:
        groups.append(f"token:{principal.subject_token}")
    return groups


def negotiate_token(principal: Principal, settings: Settings | None = None) -> str:
    active = settings or get_settings()
    now = datetime.now(UTC)
    groups = groups_for(principal)
    if principal.role in {Role.COMMANDER, Role.HQ}:
        groups = [group for group in groups if not group.startswith("token:")]
    return jwt.encode(
        {
            "iss": "manobal-engine",
            "aud": "manobal-realtime",
            "sub": principal.actor_id,
            "groups": groups,
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        active.realtime_jwt_secret.get_secret_value(),
        algorithm="HS256",
    )


def filter_payload(role: Role, payload: dict[str, Any]) -> dict[str, Any]:
    if role in {Role.COMMANDER, Role.HQ}:
        return {key: value for key, value in payload.items() if key.lower() not in INDIVIDUAL_KEYS}
    return payload


def _conn_parts(raw: str) -> dict[str, str]:
    parts: dict[str, str] = {}
    for item in raw.split(";"):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        parts[key.strip().lower()] = value.strip()
    return parts


async def _publish_azure(event_type: str, payload: dict[str, Any], groups: list[str], raw: str) -> None:
    parts = _conn_parts(raw)
    endpoint = (parts.get("endpoint") or "").rstrip("/")
    access_key = parts.get("accesskey") or ""
    if not endpoint or not access_key:
        return
    hub = "manobal"
    url = f"{endpoint}/api/hubs/{hub}/:send?api-version=2024-01-01"
    token = jwt.encode(
        {
            "aud": f"{endpoint}/api/hubs/{hub}",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=2),
            "role": ["webpubsub.sendToAll"],
        },
        access_key,
        algorithm="HS256",
    )
    async with httpx.AsyncClient(timeout=2.0) as client:
        await client.post(
            url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"type": event_type, "payload": payload, "groups": groups},
        )


async def publish(
    event_type: str,
    payload: dict[str, Any],
    groups: list[str],
    settings: Settings | None = None,
) -> None:
    active = settings or get_settings()
    if any(group in {"role:commander", "role:hq"} for group in groups):
        payload = filter_payload(Role.COMMANDER, payload)
    connection = getattr(active, "webpubsub_connection_string", "")
    hub = active.realtime_url.replace("ws://", "http://").replace("wss://", "https://")
    parsed = urlparse(hub)
    local_url = f"{parsed.scheme}://{parsed.netloc}/publish"
    async with httpx.AsyncClient(timeout=0.4) as client:
        try:
            await client.post(
                local_url,
                headers={
                    "authorization": f"Bearer {active.realtime_jwt_secret.get_secret_value()}"
                },
                json={"type": event_type, "payload": payload, "groups": groups},
            )
        except httpx.HTTPError:
            if connection:
                try:
                    await _publish_azure(event_type, payload, groups, connection)
                except httpx.HTTPError:
                    return
            return
    if connection:
        try:
            await _publish_azure(event_type, payload, groups, connection)
        except httpx.HTTPError:
            return


async def notify_world(reason: str) -> None:
    await publish("world.changed", {"reason": reason}, list(WORLD_GROUPS))


async def notify_acute_opened(*, case_id: str, unit_path: str, subject_token: str) -> None:
    await publish(
        "acute.opened",
        {"tier": "T4", "case_id": case_id},
        acute_officer_groups(unit_path),
    )
    if subject_token:
        await publish("acute.opened", {"tier": "T4"}, [f"token:{subject_token}"])


async def notify_ledger_viewed(*, subject_token: str, case_id: str) -> None:
    if not subject_token:
        return
    await publish(
        "ledger.viewed",
        {"action": "identity.viewed", "case_id": case_id},
        [f"token:{subject_token}"],
    )
