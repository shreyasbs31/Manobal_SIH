from __future__ import annotations

from app.config import Settings
from app.providers.endpoints import foundry_v1_base_url, speech_stt_url, speech_tts_url


def test_foundry_v1_from_project_url() -> None:
    settings = Settings.model_construct(
        foundry_endpoint="https://manobal-ai-resource.services.ai.azure.com/api/projects/manobal-ai",
        azure_openai_endpoint="https://other-resource.services.ai.azure.com/api/projects/other",
    )
    assert foundry_v1_base_url(settings) == "https://manobal-ai-resource.openai.azure.com/openai/v1"


def test_foundry_v1_matching_azure_openai_endpoint() -> None:
    settings = Settings.model_construct(
        foundry_endpoint="https://manobal-ai-resource.services.ai.azure.com/api/projects/manobal-ai",
        azure_openai_endpoint="https://manobal-ai-resource.openai.azure.com/openai/v1",
    )
    assert foundry_v1_base_url(settings) == "https://manobal-ai-resource.openai.azure.com/openai/v1"


def test_speech_tts_appends_tts_path() -> None:
    settings = Settings.model_construct(
        speech_endpoint="https://centralindia.api.cognitive.microsoft.com/",
        speech_region="centralindia",
    )
    assert speech_tts_url(settings).endswith("/tts/cognitiveservices/v1")


def test_speech_stt_uses_regional_host() -> None:
    settings = Settings.model_construct(
        speech_endpoint="https://centralindia.api.cognitive.microsoft.com/",
        speech_region="centralindia",
    )
    assert "stt.speech.microsoft.com" in speech_stt_url(settings)
