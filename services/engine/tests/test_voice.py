from __future__ import annotations

from app.auth import DemoLoginRequest, Role, mint_access_token, principal_for_demo
from app.privacy.rights import KILLSWITCHES
from app.voice.acoustics import acoustic_features, zeroise
from app.voice.routing import stt_route, tts_route
from app.voice.session import voice_router
from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI()
app.include_router(voice_router)
client = TestClient(app)


def _enable_voice() -> None:
    KILLSWITCHES["voice"] = False


def _token(persona: str = "arjun") -> str:
    _enable_voice()
    principal = principal_for_demo(DemoLoginRequest(role=Role.PERSONNEL, persona_id=persona))
    return mint_access_token(principal).access_token


def test_language_routes_match_spec() -> None:
    assert stt_route("en")["provider"] == "deepgram"
    assert stt_route("en")["end_of_turn"] == "flux"
    assert stt_route("hi")["language"] == "hi"
    assert stt_route("hi-Latn")["language"] == "multi"
    assert stt_route("ta")["provider"] == "azure"
    assert tts_route("en")["provider"] == "deepgram"
    assert tts_route("hi")["voice"] == "hi-IN-SwaraNeural"
    assert tts_route("ta")["voice"] == "ta-IN-PallaviNeural"


def test_buffer_is_zeros_after_audio_cleared() -> None:
    buf = bytearray(b"\x01\x02\x03\x04" * 80)
    features = acoustic_features(bytes(buf))
    assert len(features) == 88
    elapsed = zeroise(buf)
    assert elapsed >= 0
    assert buf == bytearray(len(buf))


def test_voice_en_hi_ta_first_audio_under_budget() -> None:
    token = _token("arjun")
    fixtures = {
        "en": "Sleep was short after night duty.",
        "hi": "रात की ड्यूटी के बाद नींद पूरी नहीं हुई",
        "ta": "இரவு டியூட்டிக்கு பிறகு தூக்கம் சரியில்லை",
    }
    for lang, text in fixtures.items():
        with client.websocket_connect(f"/api/v1/voice/session?access_token={token}") as ws:
            ws.send_json({"type": "start", "lang": lang, "mode": "checkin"})
            ready = ws.receive_json()
            assert ready["type"] == "session.ready"
            assert ready["hosting_caption"] == (
                "Prototype: open-weight model hosted on Azure. Deployable on force servers."
            )
            ws.send_bytes(b"\x00\x00" * 160)
            ws.send_json({"type": "transcript_final", "text": text})
            first_audio_ms = None
            cleared = False
            for _ in range(16):
                event = ws.receive_json()
                if event.get("type") == "tts" and "first_audio_ms" in event:
                    first_audio_ms = event["first_audio_ms"]
                if event.get("type") == "audio.cleared":
                    cleared = True
                    assert event["feature_count"] == 88
                    break
            assert first_audio_ms is not None
            assert first_audio_ms < 1800
            assert cleared is True


def test_barge_in_cancels_pending_tts() -> None:
    token = _token("arjun")
    with client.websocket_connect(f"/api/v1/voice/session?access_token={token}") as ws:
        ws.send_json({"type": "start", "lang": "en", "mode": "checkin"})
        ws.receive_json()
        ws.send_json({"type": "barge_in"})
        event = ws.receive_json()
        assert event["type"] == "tts.cancelled"


def test_spoken_hinglish_distress_does_not_reach_model() -> None:
    token = _token("deepak")
    with client.websocket_connect(f"/api/v1/voice/session?access_token={token}") as ws:
        ws.send_json({"type": "start", "lang": "hi-Latn", "mode": "checkin"})
        ws.receive_json()
        ws.send_json({"type": "transcript_final", "text": "main jeena nahi chahta"})
        events: list[dict[str, object]] = []
        for _ in range(8):
            event = ws.receive_json()
            events.append(event)
            if event.get("type") == "audio.cleared":
                break
        kinds = [event["type"] for event in events]
        assert "acute" in kinds
        acute = next(event for event in events if event["type"] == "acute")
        assert acute["model_reached"] is False


def test_saathi_page_wires_contour_captions_and_hosting_caption() -> None:
    from pathlib import Path

    page = Path("apps/web/src/app/(personnel)/app/saathi/page.tsx").read_text(encoding="utf-8")
    assert "VoiceContour amplitude={amplitude}" in page
    assert "CaptionStream" in page
    assert "Prototype: open-weight model hosted on Azure. Deployable on force servers." in page
