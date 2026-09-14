"""Speech-to-text stays on the server. The device never holds a vendor key."""

from __future__ import annotations

from io import BytesIO

import httpx
import pytest
from rest_framework.test import APIClient

from manobal_core.apps.authz.principal import Principal
from manobal_core.apps.governance.enums import DataType, Role
from manobal_core.apps.governance.models import ConsentEntry, ConsentTextVersion, Subject
from manobal_core.speech.deepgram import transcribe_audio

pytestmark = pytest.mark.django_db(databases=["default", "psy"])


def _client(subject: Subject) -> APIClient:
    principal = Principal(
        actor_id=subject.subject_token,
        role=Role.PERSONNEL,
        force_code=subject.force_code,
        unit_code=subject.unit_id,
        subject_token=subject.subject_token,
    )
    client = APIClient()
    client.force_authenticate(user=principal)
    return client


def _grant(subject: Subject, text: ConsentTextVersion) -> None:
    ConsentEntry.objects.create(
        subject_token=subject.subject_token,
        data_type=DataType.SELF_REPORT,
        granted=True,
        consent_text=text,
    )


def test_transcribe_refuses_a_non_https_endpoint() -> None:
    assert (
        transcribe_audio(
            b"fake-audio",
            api_key="dg-test",
            base_url="http://evil.example/v1",
        )
        == ""
    )


def test_transcribe_reads_the_transcript_from_deepgram() -> None:
    payload = {
        "results": {"channels": [{"alternatives": [{"transcript": "Sleep has been thin."}]}]}
    }
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
    assert (
        transcribe_audio(
            b"fake-audio",
            api_key="dg-test",
            base_url="https://api.deepgram.com/v1",
            transport=transport,
        )
        == "Sleep has been thin."
    )


def test_transcribe_without_a_key_is_unavailable(
    subject: Subject, consent_text: ConsentTextVersion, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("manobal_core.apps.api.views_speech.deepgram_api_key", lambda: "")
    _grant(subject, consent_text)
    response = _client(subject).post(
        "/v1/me/transcribe",
        {"audio": BytesIO(b"fake-audio")},
        format="multipart",
    )
    assert response.status_code == 503
    assert response.json()["code"] == "MB-5030"


def test_transcribe_returns_text_for_a_consented_caller(
    subject: Subject, consent_text: ConsentTextVersion, monkeypatch: pytest.MonkeyPatch
) -> None:
    _grant(subject, consent_text)
    monkeypatch.setattr("manobal_core.apps.api.views_speech.deepgram_api_key", lambda: "dg-test")
    monkeypatch.setattr(
        "manobal_core.apps.api.views_speech.transcribe_audio",
        lambda *args, **kwargs: "I have not been sleeping well",
    )
    audio = BytesIO(b"fake-audio")
    audio.name = "talk.m4a"
    response = _client(subject).post(
        "/v1/me/transcribe",
        {"audio": audio, "language": "en"},
        format="multipart",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["transcript"] == "I have not been sleeping well"
    assert "tok_" not in str(body)


def test_transcribe_without_consent_is_refused(subject: Subject) -> None:
    audio = BytesIO(b"fake-audio")
    audio.name = "talk.m4a"
    response = _client(subject).post("/v1/me/transcribe", {"audio": audio}, format="multipart")
    assert response.status_code == 422
