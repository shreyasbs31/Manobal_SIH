from __future__ import annotations

import base64
import hashlib
import hmac
from datetime import UTC, datetime
from email.utils import format_datetime
from typing import Any
from urllib.parse import urlparse

import httpx

from .config import Settings, get_settings, live_providers_enabled


def _conn_parts(raw: str) -> dict[str, str]:
    parts: dict[str, str] = {}
    for item in raw.split(";"):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        parts[key.strip().lower()] = value.strip()
    return parts


def acs_headers(method: str, url: str, body: bytes, access_key: str) -> dict[str, str]:
    parsed = urlparse(url)
    host = parsed.netloc
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    hashed = base64.b64encode(hashlib.sha256(body).digest()).decode("ascii")
    date = format_datetime(datetime.now(UTC), usegmt=True)
    string_to_sign = f"{method}\n{path}\n{date};{host};{hashed}"
    secret = base64.b64decode(access_key)
    signature = base64.b64encode(
        hmac.new(secret, string_to_sign.encode("utf-8"), hashlib.sha256).digest()
    ).decode("ascii")
    return {
        "x-ms-date": date,
        "x-ms-content-sha256": hashed,
        "Authorization": (
            "HMAC-SHA256 SignedHeaders=x-ms-date;host;x-ms-content-sha256&Signature=" + signature
        ),
        "Content-Type": "application/json",
    }


def acs_parts(settings: Settings | None = None) -> tuple[str, str]:
    active = settings or get_settings()
    raw = active.acs_connection_string.get_secret_value()
    parts = _conn_parts(raw)
    endpoint = (parts.get("endpoint") or active.acs_endpoint or "").rstrip("/")
    access_key = parts.get("accesskey") or ""
    return endpoint, access_key


def acs_configured(settings: Settings | None = None) -> bool:
    if not live_providers_enabled():
        return False
    endpoint, access_key = acs_parts(settings)
    return bool(endpoint and access_key)


async def issue_call_token(settings: Settings | None = None) -> dict[str, Any]:
    if not acs_configured(settings):
        return {"configured": False, "demo_join": True, "token": None, "user_id": None}
    endpoint, access_key = acs_parts(settings)
    create_url = f"{endpoint}/identities?api-version=2023-10-01"
    body = b'{"createTokenWithScopes":["voip"]}'
    async with httpx.AsyncClient(timeout=8.0) as client:
        created = await client.post(
            create_url,
            headers=acs_headers("POST", create_url, body, access_key),
            content=body,
        )
        created.raise_for_status()
        payload = created.json()
    identity = str(payload.get("identity", {}).get("id") or "")
    token = str((payload.get("accessToken") or {}).get("token") or "")
    expires = str((payload.get("accessToken") or {}).get("expiresOn") or "")
    return {
        "configured": True,
        "demo_join": False,
        "token": token,
        "user_id": identity,
        "expires_on": expires,
        "label": "Join call",
    }
