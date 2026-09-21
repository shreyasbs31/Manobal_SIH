from __future__ import annotations

import asyncio
import json
from collections.abc import Coroutine
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from pathlib import Path
from typing import Any, TypedDict

from azure.core.exceptions import ResourceExistsError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

from .config import Settings, get_settings
from .i18n import t
from .scoring.ruleset import REPO_ROOT
from .voice.tts import silent_wav_bytes

LANGUAGES = ("en", "hi", "ta", "hi-Latn")
SCRIPTS = ("safety", "grounding", "breathing")
MANIFEST_PATH = REPO_ROOT / "apps" / "web" / "public" / "audio" / "manifest.json"


class AudioManifest(TypedDict):
    files: list[str]
    live_tts: bool

SCRIPT_TEXT: dict[str, dict[str, str]] = {
    "safety": {
        "en": t("safety.title", "en") + " " + t("safety.reaching", "en"),
        "hi": t("safety.title", "hi") + " " + t("safety.reaching", "hi"),
        "ta": t("safety.title", "ta") + " " + t("safety.reaching", "ta"),
        "hi-Latn": "Aap akele nahi hain. Kisi ko aapse baat karne ko kaha ja raha hai.",
    },
    "grounding": {
        "en": "Look around. Name five things you can see, then four you can feel.",
        "hi": "चारों ओर देखिए। पाँच चीज़ें नाम लीजिए जो दिख रही हैं, फिर चार जो छू सकते हैं।",
        "ta": "சுற்றிலும் பாருங்கள். காணும் ஐந்து பொருட்களையும், தொடும் நான்கையும் சொல்லுங்கள்.",
        "hi-Latn": "Chaaron ore dekhiye. Paanch cheezein naam lijiye jo dikh rahi hain.",
    },
    "breathing": {
        "en": "Breathe in for four. Hold for four. Breathe out for four.",
        "hi": "चार गिनती में साँस लीजिए। चार तक रोकिए। चार में छोड़िए।",
        "ta": "நான்கு எண்ணிக்கைக்குள் மூச்சு இழுங்கள். நான்கு பிடியுங்கள். நான்கு விடுங்கள்.",
        "hi-Latn": "Char ginti mein saans lijiye. Char tak rokiye. Char mein chhodiye.",
    },
}


def manifest() -> AudioManifest:
    files = [f"{script}.{lang}.wav" for script in SCRIPTS for lang in LANGUAGES]
    return {"files": files, "live_tts": False}


def silent_wav(path: Path, seconds: float = 1.0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(silent_wav_bytes(seconds=seconds, rate=16000))


def _run[ResultT](coro: Coroutine[Any, Any, ResultT]) -> ResultT:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(coro)).result()


async def _synth_all(out_dir: Path, files: list[str]) -> str:
    from .config import get_settings as _settings
    from .voice.routing import tts_route
    from .voice.tts import _provider_audio, _voice_candidates

    settings = _settings()
    provider = "silent-wav"
    for name in files:
        parts = name.split(".")
        script = parts[0]
        lang = parts[1]
        text = SCRIPT_TEXT.get(script, {}).get(lang) or SCRIPT_TEXT["safety"]["en"]
        route = tts_route(lang)
        audio = None
        for voice_name, provider_name, style in _voice_candidates(route):
            audio = await _provider_audio(
                text,
                {**route, "provider": provider_name},
                settings,
                voice_name,
                style,
            )
            if audio:
                break
        if audio:
            (out_dir / name).write_bytes(audio)
            provider = "live-tts"
        else:
            silent_wav(out_dir / name)
    return provider


def generate_audio(
    settings: Settings | None = None,
    *,
    out_dir: Path | None = None,
) -> dict[str, object]:
    active = settings or get_settings()
    target = out_dir or (REPO_ROOT / "apps" / "web" / "public" / "audio")
    files = manifest()["files"]
    target.mkdir(parents=True, exist_ok=True)
    provider = str(_run(_synth_all(target, files)))
    payload = {
        "files": files,
        "provider": provider,
        "live_tts": provider == "live-tts",
        "review": "pending",
    }
    if out_dir is None:
        MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        uploaded = _upload_blob(active, target, files) if provider == "live-tts" else 0
    else:
        uploaded = 0
    return {**payload, "uploaded": uploaded}


def sw_cache_list() -> list[str]:
    return [f"/audio/{name}" for name in manifest()["files"]]


def _upload_blob(settings: Settings, directory: Path, files: list[str]) -> int:
    identity_credential: DefaultAzureCredential | None = None
    if settings.blob_use_managed_identity:
        identity_credential = DefaultAzureCredential(
            managed_identity_client_id=settings.azure_client_id or None,
            exclude_interactive_browser_credential=True,
        )
        credential: str | DefaultAzureCredential = identity_credential
    else:
        credential = settings.blob_account_key.get_secret_value()
    service = BlobServiceClient(
        account_url=settings.blob_endpoint,
        credential=credential,
    )
    container = service.get_container_client("audio")
    count = 0
    try:
        with suppress(ResourceExistsError):
            container.create_container()
        for name in files:
            blob = container.get_blob_client(name)
            blob.upload_blob((directory / name).read_bytes(), overwrite=True)
            count += 1
    except Exception:  # noqa: BLE001
        return count
    finally:
        service.close()
        if identity_credential is not None:
            identity_credential.close()
    return count
