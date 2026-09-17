from __future__ import annotations

import io
import wave
from html import escape
from typing import Any

import httpx

from ..config import Settings, get_settings, live_providers_enabled
from ..providers.endpoints import speech_tts_url
from .routing import tts_route

TTS_TIMEOUT_S = 8.0


def silent_wav_bytes(seconds: float = 0.35, rate: int = 16000) -> bytes:
    frames = int(rate * seconds)
    buffer = io.BytesIO()
    with wave.open(buffer, "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(b"\x00\x00" * frames)
    return buffer.getvalue()


async def synth_sentence(text: str, lang: str) -> tuple[bytes, str]:
    route = tts_route(lang)
    settings = get_settings()
    voice_name = str(route.get("voice") or "silent")
    audio = await _provider_audio(text, route, settings, voice_name)
    if audio:
        return audio, voice_name
    return silent_wav_bytes(), voice_name


async def _provider_audio(
    text: str,
    route: dict[str, Any],
    settings: Settings,
    voice_name: str,
) -> bytes | None:
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
            locale = "hi-IN" if voice_name.startswith("hi-") else "en-IN"
            if voice_name.startswith("ta-"):
                locale = "ta-IN"
            ssml = (
                f"<speak version='1.0' xml:lang='{locale}'>"
                f"<voice name='{escape(voice_name)}'>{escape(text)}</voice>"
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
