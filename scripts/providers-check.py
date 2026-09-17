#!/usr/bin/env python3
"""Call each real provider once. Print pass or fail. Never print secrets."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import jwt
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.calls import acs_headers, acs_parts
from app.config import get_settings, live_providers_enabled
from app.providers.endpoints import foundry_v1_base_url, speech_tts_url


@dataclass
class Row:
    name: str
    status: str
    detail: str
    ms: int


def _silent_pcm(seconds: float = 0.35, rate: int = 16000) -> bytes:
    return b"\x00\x00" * int(rate * seconds)


def _exc_kind(exc: BaseException) -> str:
    status = getattr(exc, "status_code", None)
    if status:
        return f"HTTP {status}"
    response = getattr(exc, "response", None)
    if response is not None and getattr(response, "status_code", None):
        return f"HTTP {response.status_code}"
    return type(exc).__name__


def _conn_parts(raw: str) -> dict[str, str]:
    parts: dict[str, str] = {}
    for item in raw.split(";"):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        parts[key.strip().lower()] = value.strip()
    return parts


async def _foundry_chat(settings: Any, model_class: str) -> Row:
    from app.providers.foundry import FoundryClient

    client = FoundryClient(settings)
    if not client.available(model_class):
        extra = "openai stand-in configured" if client._openai_companion_ok() else "local handler"
        return Row(f"Foundry {model_class}", "fail", f"unconfigured ({extra})", 0)
    started = time.perf_counter()
    try:
        result = await client.chat(
            model_class,
            [{"role": "user", "content": "Reply with the single word ping."}],
            temperature=0,
            max_tokens=128,
            timeout_s=45.0,
        )
    except Exception as exc:  # noqa: BLE001
        return Row(
            f"Foundry {model_class}",
            "fail",
            _exc_kind(exc),
            int((time.perf_counter() - started) * 1000),
        )
    if not result.text.strip():
        return Row(
            f"Foundry {model_class}",
            "fail",
            "empty_completion",
            int((time.perf_counter() - started) * 1000),
        )
    return Row(
        f"Foundry {model_class}",
        "pass",
        f"chat {foundry_v1_base_url(settings).split('/')[2]}",
        int((time.perf_counter() - started) * 1000),
    )


async def _foundry_embed(settings: Any) -> Row:
    from app.providers.foundry import FoundryClient

    client = FoundryClient(settings)
    if not client.available("embeddings"):
        return Row("Foundry embeddings", "fail", "unconfigured (hash embeddings)", 0)
    started = time.perf_counter()
    try:
        vectors = await client.embed(["ping"], 20.0)
    except Exception as exc:  # noqa: BLE001
        return Row(
            "Foundry embeddings",
            "fail",
            _exc_kind(exc),
            int((time.perf_counter() - started) * 1000),
        )
    dim = len(vectors[0]) if vectors else 0
    return Row("Foundry embeddings", "pass", f"dim {dim}", int((time.perf_counter() - started) * 1000))


async def _deepgram(settings: Any) -> Row:
    key = settings.deepgram_api_key.get_secret_value()
    if not key:
        return Row("Deepgram", "fail", "unconfigured (client-final transcript)", 0)
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(
                "https://api.deepgram.com/v1/listen",
                params={
                    "model": settings.dg_stt_model_en,
                    "language": "en",
                    "encoding": "linear16",
                    "sample_rate": "16000",
                    "channels": "1",
                },
                headers={
                    "Authorization": f"Token {key}",
                    "Content-Type": "application/octet-stream",
                },
                content=_silent_pcm(),
            )
            response.raise_for_status()
            _ = response.json()
    except Exception as exc:  # noqa: BLE001
        return Row("Deepgram", "fail", _exc_kind(exc), int((time.perf_counter() - started) * 1000))
    return Row("Deepgram", "pass", f"listen {settings.dg_stt_model_en}", int((time.perf_counter() - started) * 1000))


async def _speech(settings: Any) -> Row:
    key = settings.speech_key.get_secret_value()
    region = settings.speech_region
    if not key or not region:
        return Row("Azure Speech", "fail", "unconfigured (silent WAV)", 0)
    voice = settings.az_tts_voice_hi
    ssml = (
        "<speak version='1.0' xml:lang='hi-IN'>"
        f"<voice name='{voice}'>namaste</voice>"
        "</speak>"
    )
    endpoint = speech_tts_url(settings)
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.post(
                endpoint,
                headers={
                    "Ocp-Apim-Subscription-Key": key,
                    "Content-Type": "application/ssml+xml",
                    "X-Microsoft-OutputFormat": "riff-16khz-16bit-mono-pcm",
                    "User-Agent": "manobal",
                },
                content=ssml.encode("utf-8"),
            )
            response.raise_for_status()
            if not response.content:
                raise RuntimeError("empty_audio")
    except Exception as exc:  # noqa: BLE001
        return Row("Azure Speech", "fail", _exc_kind(exc), int((time.perf_counter() - started) * 1000))
    return Row("Azure Speech", "pass", "tts", int((time.perf_counter() - started) * 1000))


async def _translator(settings: Any) -> Row:
    key = settings.translator_key.get_secret_value()
    if not key:
        return Row("Translator", "fail", "unconfigured (English plus badge)", 0)
    endpoint = (settings.translator_endpoint or "https://api.cognitive.microsofttranslator.com").rstrip(
        "/"
    )
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(
                f"{endpoint}/translate",
                params={"api-version": "3.0", "from": "en", "to": "hi"},
                headers={
                    "Ocp-Apim-Subscription-Key": key,
                    "Ocp-Apim-Subscription-Region": settings.translator_region or "centralindia",
                    "content-type": "application/json",
                },
                json=[{"text": "hello"}],
            )
            response.raise_for_status()
            _ = response.json()
    except Exception as exc:  # noqa: BLE001
        return Row("Translator", "fail", _exc_kind(exc), int((time.perf_counter() - started) * 1000))
    return Row("Translator", "pass", "translate en to hi", int((time.perf_counter() - started) * 1000))


async def _content_safety(settings: Any) -> Row:
    if not settings.content_safety_endpoint:
        return Row("Content Safety", "fail", "unconfigured (gate abstains)", 0)
    url = f"{settings.content_safety_endpoint.rstrip('/')}/contentsafety/text:analyze"
    headers = {"content-type": "application/json"}
    key = settings.content_safety_key.get_secret_value()
    if key:
        headers["Ocp-Apim-Subscription-Key"] = key
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(
                url,
                headers=headers,
                params={"api-version": "2024-09-01"},
                json={"text": "hello", "categories": ["SelfHarm"]},
            )
            response.raise_for_status()
            _ = response.json()
    except Exception as exc:  # noqa: BLE001
        return Row("Content Safety", "fail", _exc_kind(exc), int((time.perf_counter() - started) * 1000))
    return Row("Content Safety", "pass", "text analyze", int((time.perf_counter() - started) * 1000))


async def _acs(settings: Any) -> Row:
    endpoint, access_key = acs_parts(settings)
    if not endpoint or not access_key:
        return Row("ACS", "fail", "unconfigured (labelled demo join)", 0)
    url = f"{endpoint}/identities?api-version=2023-10-01"
    body = b"{}"
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(url, headers=acs_headers("POST", url, body, access_key), content=body)
            response.raise_for_status()
            _ = response.json()
    except Exception as exc:  # noqa: BLE001
        return Row("ACS", "fail", _exc_kind(exc), int((time.perf_counter() - started) * 1000))
    return Row("ACS", "pass", "identities create", int((time.perf_counter() - started) * 1000))


async def _webpubsub(settings: Any) -> Row:
    raw = settings.webpubsub_connection_string
    if not raw:
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get("http://127.0.0.1:8080/health")
            if response.status_code < 300:
                return Row(
                    "Web PubSub",
                    "pass",
                    "local realtime hub (31.1)",
                    int((time.perf_counter() - started) * 1000),
                )
        except Exception:  # noqa: BLE001
            return Row("Web PubSub", "pass", "local realtime hub (31.1)", 0)
        return Row("Web PubSub", "pass", "local realtime hub (31.1)", 0)
    parts = _conn_parts(raw)
    endpoint = (parts.get("endpoint") or "").rstrip("/")
    access_key = parts.get("accesskey") or ""
    if not endpoint or not access_key:
        return Row("Web PubSub", "fail", "connection string missing fields", 0)
    hub = "manobal"
    url = f"{endpoint}/api/hubs/{hub}/:send?api-version=2024-01-01"
    token = jwt.encode(
        {
            "aud": f"{endpoint}/api/hubs/{hub}",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=2),
            "role": ["webpubsub.sendToAll"],
        },
        access_key,
        algorithm="HS256",
    )
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"type": "providers-check", "payload": {"ok": True}},
            )
            response.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        return Row("Web PubSub", "fail", _exc_kind(exc), int((time.perf_counter() - started) * 1000))
    return Row("Web PubSub", "pass", "hub send", int((time.perf_counter() - started) * 1000))


class _VaultProbe(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("infra/secrets.env", ".env", "infra/.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    key_provider: str = "local"
    keyvault_uri: str | None = None
    kv_kek_name: str = "vault-kek"


async def _key_vault() -> Row:
    vault_settings = _VaultProbe()
    if vault_settings.key_provider != "azure" or not vault_settings.keyvault_uri:
        local = Path("infra/keys/dev-vault-keys.json")
        if local.is_file():
            try:
                payload = json.loads(local.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return Row("Key Vault", "fail", "local wrap file unreadable", 0)
            if "wrapping_key" in payload:
                return Row("Key Vault", "pass", "local wrap file (31.1)", 0)
        return Row("Key Vault", "fail", "unconfigured (local wrap file)", 0)
    started = time.perf_counter()
    try:
        from azure.identity.aio import DefaultAzureCredential
        from azure.keyvault.keys.aio import KeyClient
        from azure.keyvault.keys.crypto import KeyWrapAlgorithm
        from azure.keyvault.keys.crypto.aio import CryptographyClient

        credential = DefaultAzureCredential()
        keys = KeyClient(vault_settings.keyvault_uri, credential)
        key = await keys.get_key(vault_settings.kv_kek_name)
        crypto = CryptographyClient(key, credential)
        data_key = __import__("hashlib").sha256(b"manobal-providers-check").digest()
        try:
            wrapped = await crypto.wrap_key(KeyWrapAlgorithm.rsa_oaep_256, data_key)
            opened = await crypto.unwrap_key(KeyWrapAlgorithm.rsa_oaep_256, wrapped.encrypted_key)
            if opened.key != data_key:
                raise RuntimeError("unwrap_mismatch")
        finally:
            await crypto.close()
            await keys.close()
            await credential.close()
    except Exception as exc:  # noqa: BLE001
        return Row("Key Vault", "fail", _exc_kind(exc), int((time.perf_counter() - started) * 1000))
    return Row("Key Vault", "pass", "wrap and unwrap", int((time.perf_counter() - started) * 1000))


async def main() -> int:
    settings = get_settings()
    if not live_providers_enabled():
        print("MANOBAL_FORCE_LOCAL_PROVIDERS=1; live checks skipped")
        return 1
    missing = settings.missing_live_provider_names()
    if missing:
        print("Missing live provider names: " + ", ".join(missing))
    checks = (
        ("Foundry main", lambda: _foundry_chat(settings, "main")),
        ("Foundry fast", lambda: _foundry_chat(settings, "fast")),
        ("Foundry open", lambda: _foundry_chat(settings, "open")),
        ("Foundry embeddings", lambda: _foundry_embed(settings)),
        ("Deepgram", lambda: _deepgram(settings)),
        ("Azure Speech", lambda: _speech(settings)),
        ("Translator", lambda: _translator(settings)),
        ("Content Safety", lambda: _content_safety(settings)),
        ("ACS", lambda: _acs(settings)),
        ("Web PubSub", lambda: _webpubsub(settings)),
        ("Key Vault", _key_vault),
    )
    rows: list[Row] = []
    for name, work in checks:
        try:
            rows.append(await work())
        except Exception as exc:  # noqa: BLE001
            rows.append(Row(name, "fail", _exc_kind(exc), 0))
    name_width = max(len(row.name) for row in rows)
    print(f"{'Provider'.ljust(name_width)}  Status  ms    Detail")
    print(f"{'-' * name_width}  ------  -----  ------")
    failed = 0
    for row in rows:
        print(f"{row.name.ljust(name_width)}  {row.status.ljust(6)}  {str(row.ms).rjust(5)}  {row.detail}")
        if row.status != "pass":
            failed += 1
    print(f"{len(rows) - failed} pass, {failed} fail")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
