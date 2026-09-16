from __future__ import annotations

import json
import wave
from contextlib import suppress
from pathlib import Path

from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import BlobServiceClient

from .config import Settings, get_settings
from .scoring.ruleset import REPO_ROOT

LANGUAGES = ("en", "hi", "ta", "hi-Latn")
SCRIPTS = ("safety", "grounding", "breathing")
MANIFEST_PATH = REPO_ROOT / "apps" / "web" / "public" / "audio" / "manifest.json"


def manifest() -> dict[str, list[str]]:
    files = [f"{script}.{lang}.wav" for script in SCRIPTS for lang in LANGUAGES]
    return {"files": files, "live_tts": False}


def silent_wav(path: Path, seconds: float = 1.0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(8000 * seconds)
    with wave.open(str(path), "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        handle.writeframes(b"\x00\x00" * frames)


def generate_audio(settings: Settings | None = None) -> dict[str, object]:
    active = settings or get_settings()
    out_dir = REPO_ROOT / "apps" / "web" / "public" / "audio"
    files = manifest()["files"]
    key = None
    try:
        key = Path("/run/manobal/azure-speech.key")
        speech_key = key.read_text(encoding="utf-8").strip() if key.exists() else ""
    except OSError:
        speech_key = ""
    provider = "azure-speech" if speech_key else "silent-wav"
    for name in files:
        silent_wav(out_dir / name)
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps({"files": files, "provider": provider, "live_tts": False}, indent=2),
        encoding="utf-8",
    )
    uploaded = _upload_blob(active, out_dir, files) if provider == "azure-speech" else 0
    return {"provider": provider, "files": files, "uploaded": uploaded}


def sw_cache_list() -> list[str]:
    return [f"/audio/{name}" for name in manifest()["files"]]


def _upload_blob(settings: Settings, directory: Path, files: list[str]) -> int:
    service = BlobServiceClient(
        account_url=settings.blob_endpoint,
        credential=settings.blob_account_key.get_secret_value(),
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
    finally:
        service.close()
    return count
