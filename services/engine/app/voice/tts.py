from __future__ import annotations

import io
import wave
from html import escape
from typing import Any

import httpx

from ..config import Settings, get_settings, live_providers_enabled
from ..providers.endpoints import speech_tts_url
from .routing import tts_route

TTS_TIMEOUT_S = 20.0

# Never send these, even if a route or fallback still names them.
MALE_VOICES = frozenset(
    {
        "hi-IN-MadhurNeural",
        "hi-IN-AaravNeural",
        "en-IN-PrabhatNeural",
        "ta-IN-ValluvarNeural",
        "flux-naveen-en",
        "aura-orion-en",
        "aura-arcas-en",
        "aura-2-apollo-en",
        "aura-2-arcas-en",
    }
)


def silent_wav_bytes(seconds: float = 0.35, rate: int = 16000) -> bytes:
    frames = int(rate * seconds)
    buffer = io.BytesIO()
    with wave.open(buffer, "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(b"\x00\x00" * frames)
    return buffer.getvalue()


def _locale_for(voice_name: str) -> str:
    if voice_name.startswith("ta-"):
        return "ta-IN"
    if voice_name.startswith("hi-"):
        return "hi-IN"
    return "en-IN"


def _voice_candidates(route: dict[str, Any]) -> list[tuple[str, str, str | None]]:
    pairs: list[tuple[str, str, str | None]] = []
    style = str(route.get("style") or "") or None
    primary = str(route.get("voice") or "").strip()
    provider = str(route.get("provider") or "")
    fallback = str(route.get("fallback") or "").strip()
    fallback_provider = str(route.get("fallback_provider") or "")
    if not fallback_provider:
        fallback_provider = "azure" if "Neural" in fallback else provider
    for voice_name, used_provider in ((primary, provider), (fallback, fallback_provider)):
        if not voice_name or not used_provider or voice_name in MALE_VOICES:
            continue
        item = (voice_name, used_provider, style if used_provider == "azure" else None)
        if item not in pairs:
            pairs.append(item)
    return pairs


async def synth_sentence(text: str, lang: str) -> tuple[bytes, str]:
    route = tts_route(lang)
    settings = get_settings()
    last_name = str(route.get("voice") or "silent")
    for voice_name, provider, style in _voice_candidates(route):
        last_name = voice_name
        audio = await _provider_audio(
            text,
            {**route, "provider": provider},
            settings,
            voice_name,
            style,
        )
        if audio:
            return audio, voice_name
    return silent_wav_bytes(), last_name


async def _provider_audio(
    text: str,
    route: dict[str, Any],
    settings: Settings,
    voice_name: str,
    style: str | None = None,
) -> bytes | None:
    if voice_name in MALE_VOICES:
        return None
    if not live_providers_enabled():
        return None
    try:
        if route.get("provider") == "deepgram":
            key = settings.deepgram_api_key.get_secret_value()
            if not key:
                return None
            async with httpx.AsyncClient(timeout=TTS_TIMEOUT_S) as client:
                response = await client.post(
                    "https://api.deepgram.com/v1/speak",
                    params={"model": voice_name, "encoding": "linear16", "container": "wav"},
                    headers={
                        "Authorization": f"Token {key}",
                        "Content-Type": "application/json",
                    },
                    json={"text": text},
                )
                if response.status_code < 300 and response.content:
                    return bytes(response.content)
        if route.get("provider") == "azure":
            key = settings.speech_key.get_secret_value()
            url = speech_tts_url(settings)
            if not key or not url:
                return None
            locale = _locale_for(voice_name)
            inner = escape(text)
            if style:
                inner = (
                    f"<mstts:express-as style='{escape(style)}'>{inner}</mstts:express-as>"
                )
            ssml = (
                "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' "
                "xmlns:mstts='https://www.w3.org/2001/mstts' "
                f"xml:lang='{locale}'>"
                f"<voice name='{escape(voice_name)}' gender='Female'>{inner}</voice>"
                "</speak>"
            )
            async with httpx.AsyncClient(timeout=TTS_TIMEOUT_S) as client:
                response = await client.post(
                    url,
                    headers={
                        "Ocp-Apim-Subscription-Key": key,
                        "Content-Type": "application/ssml+xml",
                        "X-Microsoft-OutputFormat": "riff-16khz-16bit-mono-pcm",
                        "User-Agent": "manobal",
                    },
                    content=ssml.encode("utf-8"),
                )
                if response.status_code < 300 and response.content:
                    return bytes(response.content)
    except Exception:  # noqa: BLE001
        return None
    return None
