from __future__ import annotations

from urllib.parse import urlparse

from ..config import Settings, live_providers_enabled


def _host(url: str) -> str:
    return urlparse(url).netloc.lower()


def _resource_name(url: str) -> str:
    host = _host(url)
    return host.split(".")[0] if host else ""


def foundry_v1_base_url(settings: Settings) -> str:
    """Azure OpenAI v1 base, derived from the Foundry resource, never a different project."""
    foundry = settings.foundry_endpoint.strip()
    azure = settings.azure_openai_endpoint.strip()
    if azure:
        azure_host = _host(azure)
        if foundry and _resource_name(azure) != _resource_name(foundry):
            azure = ""
        elif azure_host.endswith(".openai.azure.com"):
            base = azure.rstrip("/")
            return base if base.endswith("/openai/v1") else f"{base}/openai/v1"
        elif azure_host.endswith(".services.ai.azure.com") and "/openai/v1" in azure:
            return azure.rstrip("/")
    if not foundry:
        return ""
    parsed = urlparse(foundry)
    host = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    if host.endswith(".openai.azure.com"):
        base = f"{parsed.scheme}://{parsed.netloc}"
        return base if path.endswith("/openai/v1") else f"{base}/openai/v1"
    if host.endswith(".services.ai.azure.com"):
        if path.endswith("/openai/v1") or path == "/openai/v1":
            return f"{parsed.scheme}://{parsed.netloc}/openai/v1"
        resource = host.split(".")[0]
        return f"https://{resource}.openai.azure.com/openai/v1"
    return f"{foundry.rstrip('/')}/openai/v1"


def speech_tts_url(settings: Settings) -> str:
    endpoint = (settings.speech_endpoint or "").rstrip("/")
    region = settings.speech_region.strip()
    if endpoint.endswith("/cognitiveservices/v1"):
        return endpoint
    if endpoint and (
        "api.cognitive.microsoft.com" in endpoint or "cognitiveservices.azure.com" in endpoint
    ):
        return f"{endpoint}/tts/cognitiveservices/v1"
    if region:
        return f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
    return endpoint


def speech_stt_url(settings: Settings) -> str:
    region = settings.speech_region.strip()
    if region:
        return (
            f"https://{region}.stt.speech.microsoft.com"
            "/speech/recognition/conversation/cognitiveservices/v1"
        )
    endpoint = (settings.speech_endpoint or "").rstrip("/")
    if endpoint.endswith("/cognitiveservices/v1"):
        return endpoint
    if endpoint:
        return f"{endpoint}/speech/recognition/conversation/cognitiveservices/v1"
    return ""


def foundry_is_live(settings: Settings) -> bool:
    return live_providers_enabled() and bool(foundry_v1_base_url(settings))
