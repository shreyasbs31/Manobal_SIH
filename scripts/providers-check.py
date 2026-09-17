#!/usr/bin/env python3
"""Call each real provider once. Print pass or fail. Never print secrets."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from typing import Any
from urllib.parse import urlparse

import httpx
import jwt
from pydantic_settings import BaseSettings, SettingsConfigDict


@dataclass
class Row:
    name: str
    status: str
    detail: str
    ms: int


def _silent_pcm(seconds: float = 0.35, rate: int = 16000) -> bytes:
    return b"\x00\x00" * int(rate * seconds)


def _exc_kind(exc: BaseException) -> str:
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
    if not settings.foundry_endpoint or not client.available(model_class):
        extra = "openai stand-in configured" if client._openai_companion_ok() else "local handler"
        return Row(f"Foundry {model_class}", "fail", f"unconfigured ({extra})", 0)
    started = time.perf_counter()
    try:
        await client.chat(
            model_class,
            [{"role": "user", "content": "Reply with the single word ping."}],
            temperature=0,
            max_tokens=8,
            timeout_s=8.0,
        )
    except Exception as exc:  # noqa: BLE001
        return Row(f"Foundry {model_class}", "fail", _exc_kind(exc), int((time.perf_counter() - started) * 1000))
    return Row(f"Foundry {model_class}", "pass", "chat completions", int((time.perf_counter() - started) * 1000))


async def _foundry_embed(settings: Any) -> Row:
    from app.providers.foundry import FoundryClient

    client = FoundryClient(settings)
    if not client.available("embeddings"):
        return Row("Foundry embeddings", "fail", "unconfigured (hash embeddings)", 0)
    started = time.perf_counter()
    try:
        vectors = await client.embed(["ping"], 8.0)
    except Exception as exc:  # noqa: BLE001
        return Row("Foundry embeddings", "fail", _exc_kind(exc), int((time.perf_counter() - started) * 1000))
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
    return Row("Deepgram", "pass", "listen", int((time.perf_counter() - started) * 1000))


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
    endpoint = (
        settings.speech_endpoint
        or f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
    )
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(
                endpoint,
                headers={
                    "Ocp-Apim-Subscription-Key": key,
                    "Content-Type": "application/ssml+xml",
                    "X-Microsoft-OutputFormat": "riff-16khz-16bit-mono-pcm",
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


def _acs_headers(method: str, url: str, body: bytes, access_key: str) -> dict[str, str]:
    parsed = urlparse(url)
    host = parsed.netloc
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    hashed = base64.b64encode(hashlib.sha256(body).digest()).decode("ascii")
    date = format_datetime(datetime.now(UTC), usegmt=True)
    string_to_sign = f"{method}\n{path}\n{date};{host};{hashed}"
    secret = base64.b64decode(access_key)
    signature = base64.b64encode(hmac.new(secret, string_to_sign.encode("utf-8"), hashlib.sha256).digest()).decode(
        "ascii"
    )
    return {
        "x-ms-date": date,
        "x-ms-content-sha256": hashed,
        "Authorization": (
            "HMAC-SHA256 SignedHeaders=x-ms-date;host;x-ms-content-sha256&Signature=" + signature
        ),
        "Content-Type": "application/json",
    }


async def _acs(settings: Any) -> Row:
    raw = settings.acs_connection_string.get_secret_value()
    if not raw:
        return Row("ACS", "fail", "unconfigured (labelled demo join)", 0)
    parts = _conn_parts(raw)
    endpoint = (parts.get("endpoint") or "").rstrip("/")
    access_key = parts.get("accesskey") or ""
    if not endpoint or not access_key:
        return Row("ACS", "fail", "connection string missing fields", 0)
    url = f"{endpoint}/identities?api-version=2023-10-01"
    body = b"{}"
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(url, headers=_acs_headers("POST", url, body, access_key), content=body)
            response.raise_for_status()
            _ = response.json()
    except Exception as exc:  # noqa: BLE001
        return Row("ACS", "fail", _exc_kind(exc), int((time.perf_counter() - started) * 1000))
    return Row("ACS", "pass", "identities create", int((time.perf_counter() - started) * 1000))


async def _webpubsub(settings: Any) -> Row:
    raw = settings.webpubsub_connection_string
    if not raw:
        return Row("Web PubSub", "fail", "unconfigured (local realtime hub)", 0)
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
        env_file=("infra/.env", ".env", "infra/secrets.env"),
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
        data_key = hashlib.sha256(b"manobal-providers-check").digest()
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
    from app.config import get_settings

    settings = get_settings()
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
