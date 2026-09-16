from __future__ import annotations

from app.ai.lexicon import lexicon_hit
from app.ai.pipeline import run_pipeline
from app.ai.transliterate import looks_latin_hindi, transliterate_hi
from app.config import get_settings


async def test_latin_hindi_transliterates_before_lexicon() -> None:
    assert looks_latin_hindi("main jeena nahi chahta")
    deva = await transliterate_hi("main jeena nahi chahta")
    assert "जीना" in deva or "नहीं" in deva
    assert lexicon_hit(deva) or lexicon_hit("main jeena nahi chahta")
    assert not get_settings().translator_endpoint
    result = await run_pipeline("main jeena nahi chahta", lang="hi-Latn")
    assert result.acute is True
    assert result.model_reached is False
    assert result.transliterated
