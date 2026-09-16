from __future__ import annotations

import asyncio
from typing import Any

import httpx
from azure.identity import DefaultAzureCredential

from ..config import Settings, get_settings
from .router import ProviderResponse, ProviderRouter


class FoundryClient:
    """Azure OpenAI v1 on Foundry via Entra, plus optional sovereign and alt."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._credential = DefaultAzureCredential() if self.settings.foundry_endpoint else None

    def _token(self) -> str:
        if self._credential is None:
            return ""
        return self._credential.get_token("https://cognitiveservices.azure.com/.default").token

    def _deployment(self, model_class: str) -> str:
        mapping = {
            "main": self.settings.ai_deployment_main,
            "fast": self.settings.ai_deployment_fast,
            "open": self.settings.ai_deployment_open,
            "embeddings": self.settings.ai_deployment_embed,
            "alt": self.settings.ai_deployment_alt,
        }
        return mapping.get(model_class, model_class)

    def available(self, model_class: str) -> bool:
        if model_class == "alt":
            has_alt = bool(self.settings.ai_deployment_alt)
            has_xai = bool(self.settings.xai_api_key.get_secret_value())
            return has_alt or has_xai
        if model_class == "embeddings":
            return bool(self.settings.foundry_endpoint and self.settings.ai_deployment_embed)
        if model_class in {"main", "open"} and self._openai_companion_ok():
            if self.settings.foundry_endpoint and self._deployment(model_class):
                return True
            return True
        return bool(self.settings.foundry_endpoint and self._deployment(model_class))

    def _openai_companion_ok(self) -> bool:
        return bool(
            self.settings.openai_companion_fallback
            and self.settings.openai_api_key.get_secret_value()
        )

    async def chat(
        self,
        model_class: str,
        messages: list[dict[str, str]],
        *,
        temperature: float,
        max_tokens: int,
        timeout_s: float,
        sovereign: bool = False,
    ) -> ProviderResponse:
        if sovereign and self.settings.sovereign_llm_base_url:
            url = f"{self.settings.sovereign_llm_base_url.rstrip('/')}/chat/completions"
            headers = {"content-type": "application/json"}
            body: dict[str, Any] = {
                "model": self._deployment(model_class),
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        elif (
            model_class in {"main", "open"}
            and not self.settings.foundry_endpoint
            and self._openai_companion_ok()
        ):
            url = f"{self.settings.openai_base_url.rstrip('/')}/chat/completions"
            headers = {
                "content-type": "application/json",
                "authorization": f"Bearer {self.settings.openai_api_key.get_secret_value()}",
            }
            body = {
                "model": self.settings.openai_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        elif model_class == "alt" and self.settings.xai_api_key.get_secret_value():
            url = "https://api.x.ai/v1/chat/completions"
            headers = {
                "content-type": "application/json",
                "authorization": f"Bearer {self.settings.xai_api_key.get_secret_value()}",
            }
            body = {
                "model": "grok-4",
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        else:
            if not self.settings.foundry_endpoint:
                raise RuntimeError("foundry_unconfigured")
            deployment = self._deployment(model_class)
            url = (
                f"{self.settings.foundry_endpoint.rstrip('/')}"
                f"/openai/deployments/{deployment}/chat/completions?api-version=2024-10-21"
            )
            headers = {
                "content-type": "application/json",
                "authorization": f"Bearer {self._token()}",
            }
            body = {
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            response = await client.post(url, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()
        text = str(data["choices"][0]["message"]["content"])
        usage = data.get("usage") or {}
        return ProviderResponse(
            text=text,
            provider=model_class,
            latency_ms=0.0,
            usage={
                "prompt_tokens": int(usage.get("prompt_tokens", 0)),
                "completion_tokens": int(usage.get("completion_tokens", 0)),
            },
        )

    async def embed(self, texts: list[str], timeout_s: float) -> list[list[float]]:
        if not self.settings.foundry_endpoint:
            raise RuntimeError("foundry_unconfigured")
        url = (
            f"{self.settings.foundry_endpoint.rstrip('/')}"
            f"/openai/deployments/{self.settings.ai_deployment_embed}"
            "/embeddings?api-version=2024-10-21"
        )
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self._token()}",
        }
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            response = await client.post(
                url,
                headers=headers,
                json={"input": texts, "dimensions": 1024},
            )
            response.raise_for_status()
            data = response.json()
        return [row["embedding"] for row in data["data"]]


def local_handler(provider: str) -> Any:
    async def _handle(
        capability: str, payload: dict[str, Any], timeout_s: float
    ) -> ProviderResponse:
        del timeout_s
        if capability == "warmup":
            return ProviderResponse(text="ok", provider=provider, latency_ms=1.0)
        text = str(payload.get("text", ""))
        if capability == "crisis_classify":
            return ProviderResponse(
                text='{"crisis": false, "confidence": 0.1, "category": "none"}',
                provider=provider,
                latency_ms=5.0,
                extra={"crisis": False},
            )
        if capability == "output_guard":
            return ProviderResponse(text="pass", provider=provider, latency_ms=4.0)
        if capability == "brief_verify":
            return ProviderResponse(text="pass", provider=provider, latency_ms=4.0)
        if capability == "embeddings":
            return ProviderResponse(text="", provider=provider, latency_ms=2.0, extra={"dim": 1024})
        return ProviderResponse(text=text or "ok", provider=provider, latency_ms=8.0)

    return _handle


def build_default_router() -> ProviderRouter:
    settings = get_settings()
    client = FoundryClient(settings)
    handlers: dict[str, Any] = {}

    def wrap(model_class: str) -> Any:
        async def _handle(
            capability: str, payload: dict[str, Any], timeout_s: float
        ) -> ProviderResponse:
            if capability == "warmup":
                if not client.available(model_class):
                    raise RuntimeError("unconfigured")
                return await asyncio.wait_for(
                    client.chat(
                        model_class,
                        [{"role": "user", "content": "ping"}],
                        temperature=0,
                        max_tokens=4,
                        timeout_s=timeout_s,
                    ),
                    timeout=timeout_s,
                )
            messages = payload.get("messages") or [
                {"role": "user", "content": str(payload.get("text", ""))}
            ]
            return await asyncio.wait_for(
                client.chat(
                    model_class,
                    messages,
                    temperature=float(payload.get("temperature", 0)),
                    max_tokens=int(payload.get("max_tokens", 256)),
                    timeout_s=timeout_s,
                    sovereign=bool(payload.get("sovereign")),
                ),
                timeout=timeout_s,
            )

        return _handle

    for name in ("main", "fast", "open", "alt"):
        if client.available(name):
            handlers[name] = wrap(name)
        else:
            handlers[name] = local_handler(name)

    if client.available("embeddings"):

        async def _embed(
            capability: str, payload: dict[str, Any], timeout_s: float
        ) -> ProviderResponse:
            del capability
            vectors = await client.embed(list(payload.get("texts") or [""]), timeout_s)
            return ProviderResponse(
                text="",
                provider="embeddings",
                latency_ms=0.0,
                extra={"vectors": vectors},
            )

        handlers["embeddings"] = _embed
    else:
        handlers["embeddings"] = local_handler("embeddings")

    return ProviderRouter(handlers=handlers, resilience_mode=settings.resilience_mode)
