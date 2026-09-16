from __future__ import annotations

from typing import Any

import yaml

from ..scoring.ruleset import REPO_ROOT

VOICES_PATH = REPO_ROOT / "infra" / "ai" / "voices.yaml"


def load_voices() -> dict[str, Any]:
    return yaml.safe_load(VOICES_PATH.read_text(encoding="utf-8"))


def stt_route(lang: str) -> dict[str, Any]:
    table = load_voices()["stt"]
    if lang.startswith("hi-Latn"):
        return dict(table["hi-Latn"])
    if lang.startswith("hi"):
        return dict(table["hi"])
    if lang.startswith("en"):
        return dict(table["en"])
    key = lang.split("-")[0]
    return dict(table.get(key) or {"provider": "text", "locale": None})


def tts_route(lang: str) -> dict[str, Any]:
    table = load_voices()["tts"]
    if lang.startswith("hi-Latn"):
        return dict(table["hi-Latn"])
    if lang.startswith("hi"):
        return dict(table["hi"])
    if lang.startswith("en"):
        return dict(table["en"])
    key = lang.split("-")[0]
    return dict(table.get(key) or {"provider": "none", "voice": None})


def keyterms() -> list[str]:
    return [str(item) for item in load_voices().get("keyterms") or []]
