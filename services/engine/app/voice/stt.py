from __future__ import annotations

from typing import Any

import httpx

from ..config import Settings, get_settings, live_providers_enabled
from ..providers.endpoints import speech_stt_url
from .routing import keyterms, stt_route


async def transcribe_pcm(pcm: bytes, lang: str) -> str | None:
    if not pcm or not live_providers_enabled():
        return None
    route = stt_route(lang)
    settings = get_settings()
    try:
        if route.get("provider") == "deepgram":
            text = await _deepgram(pcm, route, settings)
            if text:
                return text
            return await _azure(pcm, route, settings)
        if route.get("provider") == "azure":
            return await _azure(pcm, route, settings)
    except Exception:  # noqa: BLE001
        return None
    return None


async def _deepgram(pcm: bytes, route: dict[str, Any], settings: Settings) -> str | None:
    key = settings.deepgram_api_key.get_secret_value()
    if not key:
        return None
    models = [
        str(route.get("model") or settings.dg_stt_model_en),
        settings.dg_stt_model_en,
        "nova-3",
        "nova-2",
    ]
    seen: set[str] = set()
    last_error: Exception | None = None
    for model in models:
        if not model or model in seen:
            continue
        seen.add(model)
        params: dict[str, Any] = {
            "model": model,
            "language": route.get("language") or "en",
            "smart_format": "true",
            "encoding": "linear16",
            "sample_rate": "16000",
            "channels": "1",
        }
        if route.get("end_of_turn") == "flux":
            params["endpointing"] = "300"
        if route.get("keyterms"):
            params["keyterm"] = keyterms()
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.post(
                    "https://api.deepgram.com/v1/listen",
                    params=params,
                    headers={
                        "Authorization": f"Token {key}",
                        "Content-Type": "application/octet-stream",
                    },
                    content=pcm,
                )
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue
        alts = payload.get("results", {}).get("channels", [{}])[0].get("alternatives", [])
        transcript = str(alts[0].get("transcript", "")).strip() if alts else ""
        return transcript or None
    if last_error:
        return None
    return None


async def _azure(pcm: bytes, route: dict[str, Any], settings: Settings) -> str | None:
    key = settings.speech_key.get_secret_value()
    url = speech_stt_url(settings)
    if not key or not url:
        return None
    locale = str(route.get("locale") or route.get("language") or "ta-IN")
    if locale == "hi":
        locale = "hi-IN"
    if locale == "en":
        locale = "en-IN"
    async with httpx.AsyncClient(timeout=8.0) as client:
        response = await client.post(
            url,
            params={"language": locale, "format": "detailed"},
            headers={
                "Ocp-Apim-Subscription-Key": key,
                "Content-Type": "audio/wav; codecs=audio/pcm; samplerate=16000",
                "User-Agent": "manobal",
            },
            content=pcm,
        )
        response.raise_for_status()
        payload = response.json()
    return str(payload.get("DisplayText") or payload.get("Text") or "").strip() or None
