from __future__ import annotations

import re
from typing import Any

import httpx

from ..config import Settings, get_settings, live_providers_enabled
from ..providers.endpoints import speech_stt_url
from ..providers.outages import is_forced_outage
from .routing import keyterms, stt_route

_LETTER_RE = re.compile(r"[A-Za-z\u0900-\u097F\u0B80-\u0BFF]{2,}")


def usable_transcript(alt: dict[str, Any] | None, min_confidence: float = 0.6) -> str | None:
    if not alt:
        return None
    text = str(alt.get("transcript") or alt.get("Display") or alt.get("Text") or "").strip()
    if not text or not _LETTER_RE.search(text):
        return None
    confidence = alt.get("confidence")
    if confidence is None:
        confidence = alt.get("Confidence")
    if confidence is not None:
        try:
            if float(confidence) < min_confidence:
                return None
        except (TypeError, ValueError):
            return None
    words = alt.get("words") or []
    if words:
        scores = []
        for word in words:
            try:
                scores.append(float(word.get("confidence") or 0))
            except (TypeError, ValueError):
                scores.append(0.0)
        if scores and (sum(scores) / len(scores)) < 0.55:
            return None
    return text


async def transcribe_pcm(pcm: bytes, lang: str) -> str | None:
    if not pcm or not live_providers_enabled():
        return None
    route = stt_route(lang)
    settings = get_settings()
    try:
        if route.get("provider") == "deepgram":
            if is_forced_outage("deepgram"):
                return await _azure(pcm, route, settings)
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
        return usable_transcript(alts[0] if alts else None)
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
    status = str(payload.get("RecognitionStatus") or "Success")
    if status not in {"Success", ""}:
        return None
    nbest = payload.get("NBest") or []
    if nbest:
        return usable_transcript(nbest[0])
    return usable_transcript({"transcript": payload.get("DisplayText") or payload.get("Text") or ""})
