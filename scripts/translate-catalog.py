#!/usr/bin/env python3
"""Regenerate machine-translated catalogs. Flag for human review. Never print secrets."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

_TOKEN = Path("infra/.cache/foundry.token")
if _TOKEN.is_file() and _TOKEN.stat().st_size > 20:
    os.environ.setdefault("FOUNDRY_AD_TOKEN_FILE", str(_TOKEN.resolve()))

import httpx

from app.config import get_settings
from app.i18n import EN, SCHEDULED
from app.scoring.ruleset import REPO_ROOT

OUT = REPO_ROOT / "infra" / "i18n" / "machine.json"
SKIP = {"en", "hi", "ta"}


async def _via_main(lang: str, keys: list[str], values: list[str]) -> dict[str, str] | None:
    from app.providers.foundry import FoundryClient

    settings = get_settings()
    client = FoundryClient(settings)
    if not client.available("main"):
        return None
    names = {"kok": "Konkani", "sa": "Sanskrit", "sat": "Santali"}
    label = names.get(lang, lang)
    payload = json.dumps({key: value for key, value in zip(keys, values, strict=True)}, ensure_ascii=False)
    result = await client.chat(
        "main",
        [
            {
                "role": "user",
                "content": (
                    f"Translate each JSON string value into {label} (language code {lang}). "
                    "Return only JSON with the same keys. Keep {{n}} placeholders. No markdown."
                    f"\n{payload}"
                ),
            }
        ],
        temperature=0,
        max_tokens=1600,
        timeout_s=60.0,
    )
    text = result.text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.split("\n", 1)[-1]
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    try:
        body = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(body, dict):
        return None
    cleaned: dict[str, str] = {}
    for key in keys:
        value = str(body.get(key) or EN[key])
        cleaned[key] = value.replace("\u2014", ", ").replace("\u2013", ", ")
    return cleaned


def main() -> int:
    settings = get_settings()
    key = settings.translator_key.get_secret_value()
    if not key:
        print("Translator unset; wrote no machine catalog")
        return 1
    endpoint = (settings.translator_endpoint or "https://api.cognitive.microsofttranslator.com").rstrip(
        "/"
    )
    existing: dict[str, dict[str, object]] = {}
    if OUT.exists():
        existing = json.loads(OUT.read_text(encoding="utf-8"))
    items = [{"text": value} for value in EN.values()]
    keys = list(EN.keys())
    values = list(EN.values())
    with httpx.Client(timeout=30.0) as client:
        for lang in SCHEDULED:
            if lang in SKIP:
                continue
            to_code = "mni" if lang == "mni" else lang
            response = client.post(
                f"{endpoint}/translate",
                params={"api-version": "3.0", "from": "en", "to": to_code},
                headers={
                    "Ocp-Apim-Subscription-Key": key,
                    "Ocp-Apim-Subscription-Region": settings.translator_region or "centralindia",
                    "content-type": "application/json",
                },
                json=items,
            )
            if response.status_code >= 300:
                fallback = asyncio.run(_via_main(lang, keys, values))
                if fallback is None:
                    fallback = {}
                    for start in range(0, len(keys), 4):
                        piece = asyncio.run(
                            _via_main(lang, keys[start : start + 4], values[start : start + 4])
                        )
                        if piece:
                            fallback.update(piece)
                existing[lang] = {
                    "review": "pending",
                    "machine_translated": True,
                    "source": "main_model" if fallback else "translator_error",
                    "error": f"HTTP {response.status_code}",
                    "strings": fallback or dict(EN),
                }
                continue
            translated = {}
            for key_name, row in zip(keys, response.json(), strict=True):
                value = str(row["translations"][0]["text"])
                translated[key_name] = value.replace("\u2014", ", ").replace("\u2013", ", ")
            existing[lang] = {
                "review": "pending",
                "machine_translated": True,
                "source": "translator",
                "strings": translated,
            }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO_ROOT)} review pending")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
