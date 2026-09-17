#!/usr/bin/env python3
"""Regenerate machine-translated catalogs. Flag for human review. Never print secrets."""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import get_settings
from app.i18n import EN, SCHEDULED
from app.scoring.ruleset import REPO_ROOT

OUT = REPO_ROOT / "infra" / "i18n" / "machine.json"
SKIP = {"en", "hi", "ta"}


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
                existing[lang] = {
                    "review": "pending",
                    "error": f"HTTP {response.status_code}",
                    "strings": existing.get(lang, {}).get("strings") or dict(EN),
                }
                continue
            translated = {}
            for key_name, row in zip(keys, response.json(), strict=True):
                value = str(row["translations"][0]["text"])
                translated[key_name] = value.replace("\u2014", ", ").replace("\u2013", ", ")
            existing[lang] = {"review": "pending", "strings": translated}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO_ROOT)} review pending")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
