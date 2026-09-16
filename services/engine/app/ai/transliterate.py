from __future__ import annotations

import re

import httpx

from ..config import get_settings

# Local Latin-to-Devanagari for Hinglish gating when Translator is unset (31.1).
LATIN_MAP = {
    "main": "मैं",
    "mujhe": "मुझे",
    "marna": "मरना",
    "chahta": "चाहता",
    "chahti": "चाहती",
    "hoon": "हूँ",
    "hun": "हूँ",
    "jeena": "जीना",
    "jeene": "जीने",
    "nahi": "नहीं",
    "nahin": "नहीं",
    "hai": "है",
    "ka": "का",
    "man": "मन",
    "khatam": "खत्म",
    "kar": "कर",
    "dunga": "दूँगा",
    "doongi": "दूँगी",
    "duniya": "दुनिया",
    "se": "से",
    "chala": "चला",
    "chali": "चली",
    "jaunga": "जाऊँगा",
    "jaungi": "जाऊँगी",
    "bas": "बस",
    "ho": "हो",
    "gaya": "गया",
    "ab": "अब",
    "rehna": "रहना",
    "rahoonga": "रहूँगा",
    "rahungi": "रहूँगी",
    "yaar": "यार",
}


def looks_latin_hindi(text: str) -> bool:
    latin = bool(re.search(r"[A-Za-z]", text))
    tokens = {token.lower() for token in re.findall(r"[A-Za-z]+", text)}
    return latin and bool(tokens.intersection(LATIN_MAP))


async def transliterate_hi(text: str) -> str:
    settings = get_settings()
    if settings.translator_endpoint and settings.translator_key.get_secret_value():
        url = f"{settings.translator_endpoint.rstrip('/')}/transliterate"
        headers = {
            "Ocp-Apim-Subscription-Key": settings.translator_key.get_secret_value(),
            "Ocp-Apim-Subscription-Region": settings.translator_region or "centralindia",
            "content-type": "application/json",
        }
        async with httpx.AsyncClient(timeout=4.0) as client:
            response = await client.post(
                url,
                headers=headers,
                params={
                    "api-version": "3.0",
                    "language": "hi",
                    "fromScript": "Latn",
                    "toScript": "Deva",
                },
                json=[{"text": text}],
            )
            response.raise_for_status()
            data = response.json()
            return str(data[0]["text"])
    parts: list[str] = []
    for token in re.findall(r"[A-Za-z]+|[^A-Za-z]+", text):
        mapped = LATIN_MAP.get(token.lower())
        parts.append(mapped if mapped is not None else token)
    return "".join(parts)
