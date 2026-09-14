"""HTTPS chat completions for the demo listener.

Production SDD keeps inference on-device. For a laptop demonstration the same
gates still run: crisis never reaches this function, and the output gate still
strips scores, tokens and clinical labels.
"""

from __future__ import annotations

import logging
import os
from collections.abc import MutableMapping
from typing import Any

import httpx

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are MANOBAL's welfare listener for a demonstration. "
    "Reply in the same language as the user (English or Hindi). "
    "Use two to four short sentences. "
    "Do not diagnose, do not name a disorder, do not mention scores, tiers, "
    "tokens, officers, or other people. "
    "You may suggest sleep hygiene, a peer, the in-app check-in, or a helpline. "
    "If they want urgent help, tell them to use SOS or the helpline numbers "
    "already on their screen."
)


def llm_api_key() -> str:
    return os.environ.get("MANOBAL_LLM_API_KEY", "").strip()


def llm_base_url() -> str:
    return os.environ.get("MANOBAL_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")


def llm_model() -> str:
    return os.environ.get("MANOBAL_LLM_MODEL", "gpt-4o-mini")


def llm_api_version() -> str:
    return (
        os.environ.get("MANOBAL_LLM_API_VERSION")
        or os.environ.get("AZURE_OPENAI_API_VERSION")
        or "2024-10-21"
    )


def _azure_host(url: str) -> bool:
    host = url.lower()
    return any(
        token in host
        for token in (
            "openai.azure.com",
            "cognitiveservices.azure.com",
            "services.ai.azure.com",
        )
    )


def bootstrap_demo_llm(environ: MutableMapping[str, str] | None = None) -> None:
    """Map common laptop secrets onto MANOBAL_LLM_* without overriding a dedicated key."""
    env = environ if environ is not None else os.environ
    if str(env.get("MANOBAL_LLM_API_KEY", "")).strip():
        return
    azure = str(env.get("AZURE_OPENAI_API_KEY", "")).strip()
    azure_base = str(
        env.get("AZURE_OPENAI_ENDPOINT") or env.get("AZURE_OPENAI_API_BASE") or ""
    ).strip()
    if azure and azure_base.startswith("https://"):
        env["MANOBAL_LLM_API_KEY"] = azure
        env.setdefault("MANOBAL_LLM_BASE_URL", azure_base)
        deployment = str(env.get("AZURE_OPENAI_DEPLOYMENT", "")).strip()
        if deployment:
            env.setdefault("MANOBAL_LLM_MODEL", deployment)
        version = str(env.get("AZURE_OPENAI_API_VERSION", "")).strip()
        if version:
            env.setdefault("MANOBAL_LLM_API_VERSION", version)
        return
    openai = str(env.get("OPENAI_API_KEY", "")).strip()
    if openai:
        env["MANOBAL_LLM_API_KEY"] = openai
        env.setdefault(
            "MANOBAL_LLM_BASE_URL",
            str(env.get("OPENAI_BASE_URL", "")).strip() or "https://api.openai.com/v1",
        )
        return
    xai = str(env.get("XAI_API_KEY") or env.get("GROK_API_KEY") or "").strip()
    if xai:
        env["MANOBAL_LLM_API_KEY"] = xai
        env.setdefault("MANOBAL_LLM_BASE_URL", "https://api.x.ai/v1")
        env.setdefault("MANOBAL_LLM_MODEL", "grok-4-fast")
        return
    groq = str(env.get("GROQ_API_KEY", "")).strip()
    if groq:
        env["MANOBAL_LLM_API_KEY"] = groq
        env.setdefault("MANOBAL_LLM_BASE_URL", "https://api.groq.com/openai/v1")
        env.setdefault("MANOBAL_LLM_MODEL", "llama-3.1-8b-instant")


def completions_url(base_url: str, model: str) -> str:
    root = base_url.rstrip("/")
    if _azure_host(root):
        version = llm_api_version()
        if "chat/completions" in root:
            return root if "api-version=" in root else f"{root}?api-version={version}"
        if root.endswith("/openai/v1"):
            return f"{root}/chat/completions"
        if "/deployments/" in root:
            return f"{root}/chat/completions?api-version={version}"
        if "services.ai.azure.com" in root.lower():
            return f"{root}/models/chat/completions?api-version={version}"
        return f"{root}/openai/deployments/{model}/chat/completions?api-version={version}"
    return f"{root}/chat/completions"


def auth_headers(api_key: str, base_url: str) -> dict[str, str]:
    if _azure_host(base_url):
        return {"api-key": api_key, "Content-Type": "application/json"}
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def complete_chat(
    message: str,
    *,
    api_key: str = "",
    base_url: str = "",
    model: str = "",
    transport: httpx.BaseTransport | None = None,
) -> str:
    """Return the assistant text, or empty on any failure."""
    key = api_key or llm_api_key()
    endpoint = (base_url or llm_base_url()).rstrip("/")
    if not key or not message.strip():
        return ""
    if not endpoint.startswith("https://"):
        logger.warning("llm_skipped_insecure")
        return ""
    payload: dict[str, Any] = {
        "model": model or llm_model(),
        "temperature": 0.3,
        "max_tokens": 180,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message.strip()[:2000]},
        ],
    }
    try:
        with httpx.Client(timeout=20.0, transport=transport) as client:
            response = client.post(
                completions_url(endpoint, payload["model"]),
                json=payload,
                headers=auth_headers(key, endpoint),
            )
        if not response.is_success:
            logger.warning("llm_http_%s %s", response.status_code, response.text[:180])
            return ""
        body = response.json()
    except (httpx.HTTPError, ValueError):
        logger.warning("llm_call_failed")
        return ""
    choices = body.get("choices") if isinstance(body, dict) else None
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0] if isinstance(choices[0], dict) else {}
    message_body = first.get("message") if isinstance(first, dict) else None
    content = message_body.get("content") if isinstance(message_body, dict) else None
    return content.strip() if isinstance(content, str) else ""
