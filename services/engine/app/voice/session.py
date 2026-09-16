from __future__ import annotations

import base64
import json
import re
import time
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..auth import decode_access_token
from ..privacy.rights import KILLSWITCHES
from .acoustics import acoustic_features, cleared_event, zeroise
from .routing import stt_route
from .stt import transcribe_pcm
from .tts import synth_sentence

voice_router = APIRouter()

HOSTING_CAPTION = (
    "Prototype: open-weight model hosted on Azure. Deployable on force servers."
)
DEMO_BANNER = (
    "Demo mode: speech is processed by a cloud service. "
    "In deployment this runs on the phone or your unit's server."
)

FIXTURE_TURNS = {
    "en": "Sleep was short after night duty.",
    "hi": "रात की ड्यूटी के बाद नींद पूरी नहीं हुई",
    "ta": "இரவு டியூட்டிக்கு பிறகு தூக்கம் சரியில்லை",
    "hi-Latn": "raat ki duty ke baad neend kam thi",
}


def _sentences(text: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"(?<=[.!?।])\s+", text) if part.strip()]
    return parts or [text]


@voice_router.websocket("/api/v1/voice/session")
async def voice_session(websocket: WebSocket) -> None:
    token = websocket.query_params.get("access_token", "")
    try:
        principal = decode_access_token(token)
    except Exception:  # noqa: BLE001
        await websocket.close(code=4401)
        return
    if KILLSWITCHES.get("voice"):
        await websocket.close(code=4403)
        return
    await websocket.accept()
    lang = "en"
    mode = "checkin"
    pcm = bytearray()
    cancelled = False

    async def run_turn(transcript: str) -> None:
        nonlocal cancelled, pcm
        from ..ai.corpus import retrieve
        from ..ai.pipeline import run_pipeline

        cancelled = False
        end_of_speech = time.perf_counter()
        await websocket.send_json(
            {"type": "caption", "speaker": "you", "text": transcript, "lang": lang}
        )
        chunks = [{"id": chunk.id, "text": chunk.text} for chunk in retrieve(transcript, lang)]
        result = await run_pipeline(
            transcript,
            lang=lang,
            mode=mode,
            voice=True,
            token=principal.subject_token,
            chunks=chunks,
        )
        gate_ms = (time.perf_counter() - end_of_speech) * 1000
        if result.acute:
            await websocket.send_json(
                {
                    "type": "acute",
                    "script": result.script,
                    "model_reached": False,
                    "hosting_caption": HOSTING_CAPTION,
                    "gate_ms": gate_ms,
                }
            )
        elif not cancelled and result.reply:
            await websocket.send_json(
                {
                    "type": "caption",
                    "speaker": "saathi",
                    "text": result.reply,
                    "lang": lang,
                }
            )
            first = True
            first_audio_ms = 0.0
            for sentence in _sentences(result.reply):
                if cancelled:
                    break
                audio, voice_name = await synth_sentence(sentence, lang)
                event: dict[str, Any] = {
                    "type": "tts",
                    "voice": voice_name,
                    "audio_b64": base64.b64encode(audio).decode("ascii"),
                    "text": sentence,
                }
                if first:
                    first_audio_ms = (time.perf_counter() - end_of_speech) * 1000
                    event["first_audio_ms"] = first_audio_ms
                    first = False
                await websocket.send_json(event)
            await websocket.send_json(
                {
                    "type": "latency",
                    "marks": {
                        "gates_ms": gate_ms,
                        "first_audio_ms": first_audio_ms,
                        "budget_ms": 1800,
                    },
                }
            )
        features: list[float] = []
        if pcm:
            features = acoustic_features(bytes(pcm))
        elapsed = zeroise(pcm)
        await websocket.send_json(cleared_event(elapsed, features))
        pcm = bytearray()

    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break
            if message.get("bytes"):
                pcm.extend(message["bytes"])
                continue
            raw_text = message.get("text") or ""
            payload = json.loads(raw_text) if raw_text else {}
            kind = payload.get("type")
            if kind == "start":
                lang = str(payload.get("lang") or lang)
                mode = str(payload.get("mode") or mode)
                route = stt_route(lang)
                await websocket.send_json(
                    {
                        "type": "session.ready",
                        "stt": route,
                        "hosting_caption": HOSTING_CAPTION,
                        "demo_banner": DEMO_BANNER,
                    }
                )
            elif kind == "barge_in":
                cancelled = True
                await websocket.send_json({"type": "tts.cancelled"})
            elif kind == "transcript_partial":
                await websocket.send_json(
                    {
                        "type": "caption",
                        "speaker": "you",
                        "text": str(payload.get("text") or ""),
                        "interim": True,
                        "lang": lang,
                    }
                )
            elif kind in {"end_of_turn", "transcript_final"}:
                transcript = str(payload.get("text") or "").strip()
                if not transcript:
                    transcript = await transcribe_pcm(bytes(pcm), lang) or ""
                if not transcript:
                    transcript = FIXTURE_TURNS.get(lang, FIXTURE_TURNS["en"])
                await run_turn(transcript)
            elif kind == "pcm_meta":
                continue
    except WebSocketDisconnect:
        zeroise(pcm)
    finally:
        zeroise(pcm)
