from __future__ import annotations

import base64
import json
import re
import time
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..auth import decode_access_token
from ..privacy.rights import KILLSWITCHES
from .acoustics import acoustic_features, cleared_event, pcm_has_speech, zeroise
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

def _sentences(text: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"(?<=[.!?।])\s+", text) if part.strip()]
    return parts or [text]


async def _send_tts(
    websocket: WebSocket,
    sentence: str,
    lang: str,
    end_of_speech: float,
    first: bool,
) -> None:
    audio, voice_name = await synth_sentence(sentence, lang)
    event: dict[str, Any] = {
        "type": "tts",
        "voice": voice_name,
        "audio_b64": base64.b64encode(audio).decode("ascii"),
        "text": sentence,
    }
    if first:
        event["first_audio_ms"] = (time.perf_counter() - end_of_speech) * 1000
    await websocket.send_json(event)


def _principal_from_token(token: str):
    if not token.strip():
        return None
    try:
        return decode_access_token(token)
    except Exception:  # noqa: BLE001
        return None


@voice_router.websocket("/api/v1/voice/session")
async def voice_session(websocket: WebSocket) -> None:
    await websocket.accept()
    principal = _principal_from_token(str(websocket.query_params.get("access_token") or ""))
    if principal is not None and KILLSWITCHES.get("voice"):
        await websocket.send_json(
            {"type": "auth.failed", "hint": "Voice is switched off for this demo."}
        )
        await websocket.close(code=4403)
        return
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
        from ..config import live_providers_enabled
        from ..ai.gateway import stream_companion_sentences
        from ..ai.lexicon import output_guard_hit

        if principal is None:
            return
        gated = await run_pipeline(
            transcript,
            lang=lang,
            mode=mode,
            voice=True,
            token=principal.subject_token,
            chunks=chunks,
            skip_model=True,
        )
        gate_ms = (time.perf_counter() - end_of_speech) * 1000
        if gated.acute:
            import logging

            logging.getLogger("uvicorn.error").warning(
                "voice_turn acute gate=%s provider=%s lang=%s",
                gated.gate,
                gated.provider,
                lang,
            )
            await websocket.send_json(
                {
                    "type": "acute",
                    "script": gated.script,
                    "model_reached": False,
                    "hosting_caption": HOSTING_CAPTION,
                    "gate_ms": gate_ms,
                }
            )
        elif gated.injection or gated.gate == "killswitch":
            await websocket.send_json(
                {
                    "type": "caption",
                    "speaker": "saathi",
                    "text": gated.reply or "",
                    "lang": lang,
                }
            )
        elif not cancelled:
            sentences: list[str] = []
            if live_providers_enabled():
                try:
                    async for sentence in stream_companion_sentences(gated.context, lang):
                        if cancelled:
                            break
                        if output_guard_hit(sentence):
                            sentences = []
                            break
                        sentences.append(sentence)
                        await websocket.send_json(
                            {
                                "type": "caption",
                                "speaker": "saathi",
                                "text": sentence,
                                "lang": lang,
                            }
                        )
                        await _send_tts(
                            websocket,
                            sentence,
                            lang,
                            end_of_speech,
                            len(sentences) == 1,
                        )
                except Exception:  # noqa: BLE001
                    sentences = []
            if not sentences and not cancelled:
                result = await run_pipeline(
                    transcript,
                    lang=lang,
                    mode=mode,
                    voice=True,
                    token=principal.subject_token,
                    chunks=chunks,
                )
                if result.reply:
                    await websocket.send_json(
                        {
                            "type": "caption",
                            "speaker": "saathi",
                            "text": result.reply,
                            "lang": lang,
                        }
                    )
                    first = True
                    for sentence in _sentences(result.reply):
                        if cancelled:
                            break
                        await _send_tts(websocket, sentence, lang, end_of_speech, first)
                        first = False
            first_audio_ms = (time.perf_counter() - end_of_speech) * 1000
            await websocket.send_json(
                {
                    "type": "latency",
                    "marks": {
                        "gates_ms": gate_ms,
                        "first_audio_ms": first_audio_ms,
                        "budget_ms": 2500,
                    },
                }
            )
            import logging

            logging.getLogger("uvicorn.error").warning(
                "voice_turn first_audio_ms=%.0f gates_ms=%.0f lang=%s",
                first_audio_ms,
                gate_ms,
                lang,
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
                if principal is None:
                    continue
                pcm.extend(message["bytes"])
                continue
            raw_text = message.get("text") or ""
            payload = json.loads(raw_text) if raw_text else {}
            kind = payload.get("type")
            if kind == "start":
                offered = str(payload.get("access_token") or "")
                if principal is None:
                    principal = _principal_from_token(offered)
                if principal is None:
                    await websocket.send_json(
                        {"type": "auth.failed", "hint": "Sign in again."}
                    )
                    await websocket.close(code=4401)
                    return
                if KILLSWITCHES.get("voice"):
                    await websocket.send_json(
                        {"type": "auth.failed", "hint": "Voice is switched off for this demo."}
                    )
                    await websocket.close(code=4403)
                    return
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
            elif principal is None:
                await websocket.send_json({"type": "auth.failed", "hint": "Sign in again."})
                await websocket.close(code=4401)
                return
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
                heard = payload.get("heard")
                if not transcript and heard is False:
                    elapsed = zeroise(pcm)
                    pcm = bytearray()
                    await websocket.send_json({"type": "no_speech", "elapsed_ms": elapsed})
                    continue
                if not transcript and not pcm_has_speech(bytes(pcm)):
                    elapsed = zeroise(pcm)
                    pcm = bytearray()
                    await websocket.send_json({"type": "no_speech", "elapsed_ms": elapsed})
                    continue
                if not transcript:
                    transcript = await transcribe_pcm(bytes(pcm), lang) or ""
                if not transcript:
                    elapsed = zeroise(pcm)
                    pcm = bytearray()
                    await websocket.send_json({"type": "no_speech", "elapsed_ms": elapsed})
                    continue
                await run_turn(transcript)
            elif kind == "pcm_meta":
                continue
    except WebSocketDisconnect:
        zeroise(pcm)
    finally:
        zeroise(pcm)
