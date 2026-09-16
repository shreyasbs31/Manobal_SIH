from __future__ import annotations

from typing import Any

import httpx

from ..config import get_settings


async def content_safety_self_harm(text: str) -> bool | None:
    """Return True/False, or None when the gate abstains (spec 3.2)."""
    settings = get_settings()
    if not settings.content_safety_endpoint:
        return None
    url = f"{settings.content_safety_endpoint.rstrip('/')}/contentsafety/text:analyze"
    headers = {"content-type": "application/json"}
    key = settings.content_safety_key.get_secret_value()
    if key:
        headers["Ocp-Apim-Subscription-Key"] = key
    try:
        async with httpx.AsyncClient(timeout=1.2) as client:
            response = await client.post(
                url,
                headers=headers,
                params={"api-version": "2024-09-01"},
                json={"text": text, "categories": ["SelfHarm"]},
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()
    except Exception:  # noqa: BLE001
        return True
    for row in data.get("categoriesAnalysis") or []:
        if str(row.get("category", "")).lower() == "selfharm" and int(row.get("severity", 0)) >= 2:
            return True
    return False


async def prompt_shields_attack(text: str) -> bool | None:
    settings = get_settings()
    if not settings.content_safety_endpoint:
        return None
    url = f"{settings.content_safety_endpoint.rstrip('/')}/contentsafety/text:shieldPrompt"
    headers = {"content-type": "application/json"}
    key = settings.content_safety_key.get_secret_value()
    if key:
        headers["Ocp-Apim-Subscription-Key"] = key
    try:
        async with httpx.AsyncClient(timeout=1.2) as client:
            response = await client.post(
                url,
                headers=headers,
                params={"api-version": "2024-09-01"},
                json={"userPrompt": text, "documents": []},
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()
    except Exception:  # noqa: BLE001
        return False
    analysis = data.get("userPromptAnalysis") or {}
    return bool(analysis.get("attackDetected"))
