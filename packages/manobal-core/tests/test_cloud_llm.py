"""Cloud inference is optional, HTTPS-only, and never sees a crisis turn."""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from manobal_core.agent.backends import CloudBackend, DeterministicBackend, backend_for_settings
from manobal_core.agent.cloud import (
    auth_headers,
    bootstrap_demo_llm,
    complete_chat,
    completions_url,
)


def test_foundry_host_uses_the_models_chat_path() -> None:
    url = completions_url("https://demo.services.ai.azure.com", "gpt-4.1-mini")
    assert url.startswith("https://demo.services.ai.azure.com/models/chat/completions")


def test_azure_v1_base_uses_the_openai_compatible_path() -> None:
    url = completions_url(
        "https://demo.cognitiveservices.azure.com/openai/v1",
        "gpt-4.1-mini",
    )
    assert url == "https://demo.cognitiveservices.azure.com/openai/v1/chat/completions"


def test_bootstrap_maps_azure_without_overriding_a_dedicated_key() -> None:
    env = {
        "AZURE_OPENAI_API_KEY": "azure-key",
        "AZURE_OPENAI_ENDPOINT": "https://demo.cognitiveservices.azure.com",
        "AZURE_OPENAI_DEPLOYMENT": "gpt-4.1-mini",
        "AZURE_OPENAI_API_VERSION": "2025-01-01-preview",
    }
    bootstrap_demo_llm(env)
    assert env["MANOBAL_LLM_API_KEY"] == "azure-key"
    assert env["MANOBAL_LLM_BASE_URL"] == "https://demo.cognitiveservices.azure.com"
    assert env["MANOBAL_LLM_MODEL"] == "gpt-4.1-mini"
    assert env["MANOBAL_LLM_API_VERSION"] == "2025-01-01-preview"
    env["MANOBAL_LLM_API_KEY"] = "already-set"
    bootstrap_demo_llm(env)
    assert env["MANOBAL_LLM_API_KEY"] == "already-set"


def test_azure_completions_use_the_deployment_path_and_api_key() -> None:
    url = completions_url("https://demo.openai.azure.com", "gpt-4o-mini")
    assert "deployments/gpt-4o-mini/chat/completions" in url
    assert "api-version=" in url
    headers = auth_headers("azure-key", "https://demo.openai.azure.com")
    assert headers["api-key"] == "azure-key"
    assert "Authorization" not in headers


def test_bootstrap_maps_xai_when_openai_is_absent() -> None:
    env = {"XAI_API_KEY": "xai-test"}
    bootstrap_demo_llm(env)
    assert env["MANOBAL_LLM_API_KEY"] == "xai-test"
    assert env["MANOBAL_LLM_BASE_URL"] == "https://api.x.ai/v1"
    assert env["MANOBAL_LLM_MODEL"] == "grok-4-fast"


def test_bootstrap_prefers_openai_over_xai() -> None:
    env = {"OPENAI_API_KEY": "sk-test", "XAI_API_KEY": "xai-test"}
    bootstrap_demo_llm(env)
    assert env["MANOBAL_LLM_API_KEY"] == "sk-test"
    assert env["MANOBAL_LLM_BASE_URL"] == "https://api.openai.com/v1"


def test_complete_chat_refuses_a_non_https_endpoint() -> None:
    assert complete_chat("hello", api_key="k", base_url="http://evil.example/v1") == ""


def test_complete_chat_reads_the_assistant_message() -> None:
    payload = {"choices": [{"message": {"content": "A short, non-clinical reply."}}]}
    response = httpx.Response(200, json=payload)
    transport = httpx.MockTransport(lambda _: response)
    reply = complete_chat(
        "I am tired",
        api_key="sk-test",
        base_url="https://api.openai.com/v1",
        transport=transport,
    )
    assert reply == "A short, non-clinical reply."


def test_cloud_backend_falls_back_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MANOBAL_LLM_API_KEY", raising=False)
    monkeypatch.setenv("MANOBAL_AGENT_BACKEND", "cloud")
    backend = backend_for_settings()
    assert isinstance(backend, DeterministicBackend)


def test_cloud_backend_uses_the_model_when_a_key_is_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MANOBAL_LLM_API_KEY", "sk-test")
    monkeypatch.setenv("MANOBAL_AGENT_BACKEND", "cloud")
    backend = backend_for_settings()
    assert isinstance(backend, CloudBackend)
    with patch("manobal_core.agent.backends.complete_chat", return_value="Cloud reply.") as mocked:
        assert backend.complete("hello") == "Cloud reply."
        mocked.assert_called_once()


def test_a_failed_cloud_call_falls_back_to_the_local_listener() -> None:
    with patch("manobal_core.agent.backends.complete_chat", return_value=""):
        reply = CloudBackend().complete("I have not been sleeping well")
    assert "Sleep" in reply or "sleep" in reply.lower()
