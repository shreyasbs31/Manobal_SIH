"""HTTPS Deepgram listen calls. Audio is not logged and is not sent to an LLM."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

MAX_AUDIO_BYTES = 4_000_000


def deepgram_api_key() -> str:
    return os.environ.get("MANOBAL_DEEPGRAM_API_KEY", "").strip()


def deepgram_base_url() -> str:
    return os.environ.get("MANOBAL_DEEPGRAM_BASE_URL", "https://api.deepgram.com/v1").rstrip("/")


def deepgram_model() -> str:
    return os.environ.get("MANOBAL_DEEPGRAM_MODEL", "nova-2")


def transcribe_audio(
    payload: bytes,
    *,
    content_type: str = "audio/m4a",
    language: str = "en",
    api_key: str = "",
    base_url: str = "",
    model: str = "",
    transport: httpx.BaseTransport | None = None,
) -> str:
    """Return the transcript, or empty on any failure."""
    key = api_key or deepgram_api_key()
    endpoint = (base_url or deepgram_base_url()).rstrip("/")
    if not key or not payload:
        return ""
    if not endpoint.startswith("https://"):
        logger.warning("stt_skipped_insecure")
        return ""
    if len(payload) > MAX_AUDIO_BYTES:
        logger.warning("stt_too_large")
        return ""
    lang = language.strip()[:8] or "en"
    query = f"model={model or deepgram_model()}&smart_format=true&language={lang}"
    try:
        with httpx.Client(timeout=20.0, transport=transport) as client:
            response = client.post(
                f"{endpoint}/listen?{query}",
                content=payload,
                headers={
                    "Authorization": f"Token {key}",
                    "Content-Type": content_type or "application/octet-stream",
                },
            )
        if not response.is_success:
            logger.warning("stt_http_%s", response.status_code)
            return ""
        body: Any = response.json()
    except (httpx.HTTPError, ValueError):
        logger.warning("stt_call_failed")
        return ""
    results = body.get("results") if isinstance(body, dict) else None
    channels = results.get("channels") if isinstance(results, dict) else None
    if not isinstance(channels, list) or not channels:
        return ""
    first = channels[0] if isinstance(channels[0], dict) else {}
    alts = first.get("alternatives") if isinstance(first, dict) else None
    if not isinstance(alts, list) or not alts or not isinstance(alts[0], dict):
        return ""
    transcript = alts[0].get("transcript")
    return transcript.strip() if isinstance(transcript, str) else ""
