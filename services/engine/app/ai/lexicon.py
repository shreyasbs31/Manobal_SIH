from __future__ import annotations

import json
import re
import unicodedata

from ..scoring.ruleset import REPO_ROOT

LEXICON_PATH = REPO_ROOT / "infra" / "lexicon" / "phrases.json"
_CACHE: dict[str, object] | None = None


def load_lexicon() -> dict[str, object]:
    global _CACHE
    if _CACHE is None:
        _CACHE = json.loads(LEXICON_PATH.read_text(encoding="utf-8"))
    return _CACHE


def normalise(text: str) -> str:
    folded = unicodedata.normalize("NFKC", text).lower()
    folded = re.sub(r"[''`´]", "", folded)
    folded = re.sub(r"[^\w\s\u0900-\u097F\u0B80-\u0BFF]", " ", folded)
    return re.sub(r"\s+", " ", folded).strip()


def lexicon_hit(text: str, *, langs: tuple[str, ...] | None = None) -> str | None:
    data = load_lexicon()
    crisis = data["crisis"]
    assert isinstance(crisis, dict)
    blob = normalise(text)
    keys = langs or tuple(crisis.keys())
    for lang in keys:
        phrases = crisis.get(lang) or []
        assert isinstance(phrases, list)
        for phrase in phrases:
            if normalise(str(phrase)) and normalise(str(phrase)) in blob:
                return str(phrase)
    return None


def injection_hit(text: str) -> str | None:
    data = load_lexicon()
    blob = normalise(text)
    for phrase in data.get("injection") or []:
        if normalise(str(phrase)) in blob:
            return str(phrase)
    return None


def output_guard_hit(text: str) -> str | None:
    data = load_lexicon()
    blob = normalise(text)
    for phrase in data.get("output_block") or []:
        if normalise(str(phrase)) in blob:
            return str(phrase)
    return None
