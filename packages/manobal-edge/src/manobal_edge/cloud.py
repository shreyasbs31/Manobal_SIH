"""Optional OpenAI-compatible inference for the Zone 1 demo stub."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

SYSTEM_PROMPT = (
    "You are MANOBAL's welfare listener. Two to four short sentences. "
    "No diagnosis, scores, tiers, tokens or names. Suggest check-in, a peer, "
    "or a helpline. Match the user's language."
)


def complete_chat(message: str) -> str:
    key = os.environ.get("MANOBAL_LLM_API_KEY", "").strip()
    base = os.environ.get("MANOBAL_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("MANOBAL_LLM_MODEL", "gpt-4o-mini")
    if not key or not message.strip() or not base.startswith("https://"):
        return ""
    payload = json.dumps(
        {
            "model": model,
            "temperature": 0.3,
            "max_tokens": 180,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message.strip()[:2000]},
            ],
        }
    ).encode()
    request = urllib.request.Request(  # noqa: S310
        f"{base}/chat/completions",
        data=payload,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=12) as response:  # noqa: S310
            body = json.loads(response.read().decode())
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return ""
    choices = body.get("choices") if isinstance(body, dict) else None
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        return ""
    content = (choices[0].get("message") or {}).get("content")
    return content.strip() if isinstance(content, str) else ""
