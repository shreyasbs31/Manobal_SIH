from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import jwt

from .auth import Principal, Role
from .config import Settings, get_settings

INDIVIDUAL_KEYS = frozenset({"token", "subject_token", "case_id", "person_id", "service_no"})


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
    async with httpx.AsyncClient(timeout=2.0) as client:
        try:
            await client.post(
                f"{hub}/publish",
                headers={
                    "authorization": f"Bearer {active.realtime_jwt_secret.get_secret_value()}"
                },
                json={"type": event_type, "payload": payload, "groups": groups},
            )
        except httpx.HTTPError:
            if connection:
                return
            return
