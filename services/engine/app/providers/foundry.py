from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from azure.core.credentials import AccessToken
from azure.identity import DefaultAzureCredential
from openai import AsyncOpenAI

from ..config import Settings, get_settings, live_providers_enabled
from .endpoints import foundry_is_live, foundry_v1_base_url
from .router import ProviderResponse, ProviderRouter

_COGNITIVE_SCOPE = "https://cognitiveservices.azure.com/.default"


class _FileTokenCredential:
    def __init__(self, path: Path) -> None:
        self.path = path

    def get_token(self, *scopes: str, **kwargs: Any) -> AccessToken:
        del scopes, kwargs
        token = self.path.read_text(encoding="utf-8").strip()
        if not token:
            raise RuntimeError("foundry_token_file_empty")
        return AccessToken(token, int(time.time()) + 3000)


def _is_deployment_missing(exc: BaseException) -> bool:
    text = str(exc).lower()
    return "deploymentnotfound" in text or "does not exist" in text


class FoundryClient:
    """Azure OpenAI v1 on Foundry via Entra, plus optional sovereign and alt."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._openai: AsyncOpenAI | None = None
        self._credential: _FileTokenCredential | DefaultAzureCredential | None = None

    def _token_credential(self) -> _FileTokenCredential | DefaultAzureCredential:
        if self._credential is not None:
            return self._credential
        token_file = self.settings.foundry_ad_token_file
        if token_file and Path(token_file).is_file() and Path(token_file).stat().st_size > 0:
            self._credential = _FileTokenCredential(Path(token_file))
            return self._credential
        self._credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
        return self._credential

    def _client(self) -> AsyncOpenAI:
        if self._openai is not None:
            return self._openai
        base = foundry_v1_base_url(self.settings)
        if not base:
            raise RuntimeError("foundry_unconfigured")
        async def _api_key() -> str:
            return self._token_credential().get_token(_COGNITIVE_SCOPE).token

        self._openai = AsyncOpenAI(base_url=base, api_key=_api_key)
        return self._openai

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
        if not live_providers_enabled():
            return False
        if model_class == "alt":
            has_alt = bool(self.settings.ai_deployment_alt)
            has_xai = bool(self.settings.xai_api_key.get_secret_value())
            return has_alt or has_xai
        if model_class == "embeddings":
            return foundry_is_live(self.settings) and bool(self.settings.ai_deployment_embed)
        if model_class in {"main", "open"} and self._openai_companion_ok():
            if foundry_is_live(self.settings) and self._deployment(model_class):
                return True
            return True
        return foundry_is_live(self.settings) and bool(self._deployment(model_class))

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
        del temperature
        if sovereign and self.settings.sovereign_llm_base_url:
            client = AsyncOpenAI(base_url=self.settings.sovereign_llm_base_url.rstrip("/"), api_key="x")
            completion = await client.chat.completions.create(
                model=self._deployment(model_class),
                messages=messages,  # type: ignore[arg-type]
                max_tokens=max(16, max_tokens),
                timeout=timeout_s,
            )
        elif (
            model_class in {"main", "open"}
            and not foundry_is_live(self.settings)
            and self._openai_companion_ok()
        ):
            client = AsyncOpenAI(
                base_url=self.settings.openai_base_url.rstrip("/"),
                api_key=self.settings.openai_api_key.get_secret_value(),
            )
            completion = await client.chat.completions.create(
                model=self.settings.openai_model,
                messages=messages,  # type: ignore[arg-type]
                max_tokens=max(16, max_tokens),
                timeout=timeout_s,
            )
        elif model_class == "alt" and self.settings.xai_api_key.get_secret_value():
            client = AsyncOpenAI(
                base_url="https://api.x.ai/v1",
                api_key=self.settings.xai_api_key.get_secret_value(),
            )
            completion = await client.chat.completions.create(
                model="grok-4",
                messages=messages,  # type: ignore[arg-type]
                max_tokens=max(16, max_tokens),
                timeout=timeout_s,
            )
        else:
            if not foundry_is_live(self.settings):
                raise RuntimeError("foundry_unconfigured")
            client = self._client()
            deployment = self._deployment(model_class)
            token_budget = max(128, max_tokens)

            async def _complete(model: str, budget: int) -> Any:
                return await client.chat.completions.create(
                    model=model,
                    messages=messages,  # type: ignore[arg-type]
                    max_completion_tokens=budget,
                    timeout=timeout_s,
                )

            try:
                completion = await _complete(deployment, token_budget)
            except Exception as exc:
                if _is_deployment_missing(exc) and deployment != model_class and model_class:
                    deployment = model_class
                    completion = await _complete(deployment, token_budget)
                else:
                    raise
            if not str(completion.choices[0].message.content or "").strip():
                completion = await _complete(deployment, max(256, token_budget))
        message = completion.choices[0].message
        text = str(message.content or "")
        usage = completion.usage
        return ProviderResponse(
            text=text,
            provider=model_class,
            latency_ms=0.0,
            usage={
                "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
                "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
            },
        )

    async def embed(self, texts: list[str], timeout_s: float) -> list[list[float]]:
        if not foundry_is_live(self.settings):
            raise RuntimeError("foundry_unconfigured")
        client = self._client()
        response = await client.embeddings.create(
            model=self.settings.ai_deployment_embed,
            input=texts,
            dimensions=1024,
            timeout=timeout_s,
        )
        return [list(row.embedding) for row in response.data]


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
    import asyncio

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
                        [{"role": "user", "content": "Reply with the single word ping."}],
                        temperature=0,
                        max_tokens=128,
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
