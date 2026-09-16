from __future__ import annotations

from typing import Any

import httpx

from ..config import Settings, get_settings
from .routing import keyterms, stt_route


async def transcribe_pcm(pcm: bytes, lang: str) -> str | None:
    if not pcm:
        return None
    route = stt_route(lang)
    settings = get_settings()
    try:
        if route.get("provider") == "deepgram":
            return await _deepgram(pcm, route, settings)
        if route.get("provider") == "azure":
            return await _azure(pcm, route, settings)
    except Exception:  # noqa: BLE001
        return None
    return None


async def _deepgram(pcm: bytes, route: dict[str, Any], settings: Settings) -> str | None:
    key = settings.deepgram_api_key.get_secret_value()
    if not key:
        return None
    params: dict[str, Any] = {
        "model": route.get("model") or settings.dg_stt_model_en,
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
    alts = payload.get("results", {}).get("channels", [{}])[0].get("alternatives", [])
    transcript = str(alts[0].get("transcript", "")).strip() if alts else ""
    return transcript or None


async def _azure(pcm: bytes, route: dict[str, Any], settings: Settings) -> str | None:
    key = settings.speech_key.get_secret_value()
    region = settings.speech_region
    if not key or not region:
        return None
    locale = str(route.get("locale") or "ta-IN")
    endpoint = (
        settings.speech_endpoint
        or f"https://{region}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1"
    )
    async with httpx.AsyncClient(timeout=8.0) as client:
        response = await client.post(
            endpoint,
            params={"language": locale, "format": "detailed"},
            headers={
                "Ocp-Apim-Subscription-Key": key,
                "Content-Type": "audio/wav; codecs=audio/pcm; samplerate=16000",
            },
            content=pcm,
        )
        response.raise_for_status()
        payload = response.json()
    return str(payload.get("DisplayText") or payload.get("Text") or "").strip() or None
