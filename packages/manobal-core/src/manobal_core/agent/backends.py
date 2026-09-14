"""Pluggable inference. Cloud is used when a key is present; otherwise local."""

from __future__ import annotations

from typing import Protocol

import httpx
from django.conf import settings

from manobal_core.agent.cloud import complete_chat, llm_api_key


class InferenceBackend(Protocol):
    def complete(self, message: str) -> str: ...


class DeterministicBackend:
    """No model. Short, non-clinical replies. Safe when the edge is down."""

    def complete(self, message: str) -> str:
        text = message.lower()
        if any(word in text for word in ("sleep", "tired", "insomnia")):
            return (
                "Sleep is often the first thing that slips. A consistent wind-down "
                "and talking to someone you trust can help. I cannot diagnose."
            )
        if any(word in text for word in ("angry", "irritable", "fight")):
            return (
                "Feeling on edge after a hard rotation is common. A short walk or "
                "a check-in with a peer can take the edge off. I cannot diagnose."
            )
        return (
            "Thank you for writing. I can listen and point you to support. "
            "If you want structured help, use the check-in or speak with welfare."
        )


class EdgeBackend:
    """Forwards to the Zone 1 inference URL. Falls back if the edge is silent."""

    def complete(self, message: str) -> str:
        url = str(settings.AGENT.get("EDGE_URL") or "")
        if not url:
            return DeterministicBackend().complete(message)
        try:
            with httpx.Client(timeout=2.0) as client:
                response = client.post(
                    f"{url.rstrip('/')}/v1/infer", json={"message": message}
                )
            body = response.json() if response.is_success else {}
        except httpx.HTTPError:
            return DeterministicBackend().complete(message)
        reply = body.get("reply") if isinstance(body, dict) else None
        if isinstance(reply, str) and reply.strip():
            return reply
        return DeterministicBackend().complete(message)


class CloudBackend:
    """OpenAI-compatible chat. Falls back to the local listener if the call fails."""

    def complete(self, message: str) -> str:
        reply = complete_chat(message)
        if reply:
            return reply
        return DeterministicBackend().complete(message)


def backend_for_settings() -> InferenceBackend:
    name = str(settings.AGENT.get("BACKEND") or "auto")
    if name == "edge":
        return EdgeBackend()
    if name == "deterministic":
        return DeterministicBackend()
    if name in {"cloud", "auto"} and llm_api_key():
        return CloudBackend()
    return DeterministicBackend()
