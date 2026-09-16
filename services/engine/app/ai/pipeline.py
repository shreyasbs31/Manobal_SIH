from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal

from ..acute import AcuteRequest, process_acute
from ..privacy.rights import KILLSWITCHES
from .gateway import run
from .lexicon import injection_hit, lexicon_hit, output_guard_hit
from .safety import content_safety_self_harm, prompt_shields_attack
from .sanitise import sanitise
from .transliterate import looks_latin_hindi, transliterate_hi

Mode = Literal["checkin", "ask", "reflect"]

FIXED_SAFETY = "You are not alone. Someone is being asked to reach you."
INJECTION_REFUSAL = (
    "I cannot follow that request. If you want to talk about rest, sleep, or leave, I am here."
)
SAFE_FALLBACK = (
    "I may have said that poorly. A person can help more than I can. "
    "Would you like me to offer contact?"
)
HOSTING_CAPTION = "Prototype: open-weight model hosted on Azure. Deployable on force servers."


@dataclass
class PipelineResult:
    acute: bool
    injection: bool
    reply: str | None
    script: str | None
    mode: str
    provider: str
    citations: list[str] = field(default_factory=list)
    tools: list[dict[str, Any]] = field(default_factory=list)
    latency_ms: dict[str, float] = field(default_factory=dict)
    model_reached: bool = False
    gate: str | None = None
    transliterated: str | None = None
    hosting_caption: str = HOSTING_CAPTION


def resolve_mode(requested: str, *, tier: str, reflect_allowed: bool) -> Mode:
    blocked = tier in {"T3", "T4"} or not reflect_allowed or KILLSWITCHES.get("agent")
    if requested == "reflect" and blocked:
        return "checkin"
    if requested in {"checkin", "ask", "reflect"}:
        return requested  # type: ignore[return-value]
    return "checkin"


async def _classifier_crisis(text: str, lang: str) -> bool:
    try:
        result = await run("crisis_classify", {"text": text}, lang)
        if result.extra.get("crisis") is True or result.extra.get("error") is True:
            return True
        payload = json.loads(result.text)
        return bool(payload.get("crisis"))
    except Exception:  # noqa: BLE001
        return True


async def _open_acute(token: str | None, lang: str, voice: bool) -> None:
    if not token:
        return
    channel = "voice" if voice else "app"
    await process_acute(
        AcuteRequest(token=token, trigger="crisis_gate", lang=lang, channel=channel)
    )


async def run_pipeline(
    text: str,
    *,
    lang: str,
    mode: str = "checkin",
    tier: str = "T0",
    voice: bool = False,
    token: str | None = None,
    remembers: list[str] | None = None,
    opt_in_remembers: bool = False,
    chunks: list[dict[str, str]] | None = None,
    beat_id: str | None = None,
) -> PipelineResult:
    import time

    started = time.perf_counter()
    attack = injection_hit(text)
    raw = sanitise(text)
    transliterated = raw
    if lang in {"hi", "hi-Latn", "hi-Latn-IN"} or looks_latin_hindi(raw):
        transliterated = await transliterate_hi(raw)
    gated = f"{raw} {transliterated}"
    t_gate = time.perf_counter()
    if lexicon_hit(gated):
        await _open_acute(token, lang, voice)
        return PipelineResult(
            acute=True,
            injection=False,
            reply=None,
            script=FIXED_SAFETY,
            mode=mode,
            provider="lexicon",
            model_reached=False,
            gate="lexicon",
            transliterated=transliterated,
            latency_ms={"gates": (time.perf_counter() - t_gate) * 1000},
        )
    if attack or injection_hit(raw):
        return PipelineResult(
            acute=False,
            injection=True,
            reply=INJECTION_REFUSAL,
            script=None,
            mode=mode,
            provider="prompt_shields",
            model_reached=False,
            gate="injection",
            transliterated=transliterated,
        )
    crisis = await _classifier_crisis(transliterated, lang)
    safety = await content_safety_self_harm(transliterated)
    if crisis or safety is True:
        await _open_acute(token, lang, voice)
        return PipelineResult(
            acute=True,
            injection=False,
            reply=None,
            script=FIXED_SAFETY,
            mode=mode,
            provider="crisis_classify" if crisis else "content_safety",
            model_reached=False,
            gate="crisis_classify" if crisis else "content_safety",
            transliterated=transliterated,
            latency_ms={"gates": (time.perf_counter() - started) * 1000},
        )
    shield = await prompt_shields_attack(raw)
    if shield is True:
        return PipelineResult(
            acute=False,
            injection=True,
            reply=INJECTION_REFUSAL,
            script=None,
            mode=mode,
            provider="prompt_shields",
            model_reached=False,
            gate="prompt_shields",
            transliterated=transliterated,
        )
    chosen = resolve_mode(mode, tier=tier, reflect_allowed=not KILLSWITCHES.get("agent", False))
    if KILLSWITCHES.get("agent"):
        return PipelineResult(
            acute=False,
            injection=False,
            reply="Saathi is paused.",
            script=None,
            mode=chosen,
            provider="killswitch",
            model_reached=False,
            gate="killswitch",
        )
    context: dict[str, Any] = {
        "text": raw,
        "mode": chosen,
        "lang": lang,
        "tier_band": "T3+" if tier in {"T3", "T4"} else "T0-T2",
    }
    if opt_in_remembers and remembers:
        context["remembers"] = remembers[:20]
    if chosen == "ask":
        context["chunks"] = chunks or []
    result = await run("companion_turn", context, lang, voice=voice, beat_id=beat_id)
    reply = result.text
    citations: list[str] = []
    if chosen == "ask":
        from .corpus import grounded_reply

        reply, citations = grounded_reply(raw, chunks or [], lang)
    if output_guard_hit(reply):
        return PipelineResult(
            acute=False,
            injection=False,
            reply=SAFE_FALLBACK,
            script=None,
            mode=chosen,
            provider=result.provider,
            model_reached=True,
            gate="output_guard",
            transliterated=transliterated,
            latency_ms={"total": (time.perf_counter() - started) * 1000},
        )
    return PipelineResult(
        acute=False,
        injection=False,
        reply=reply,
        script=None,
        mode=chosen,
        provider=result.provider,
        citations=citations,
        model_reached=True,
        transliterated=transliterated,
        latency_ms={"total": (time.perf_counter() - started) * 1000},
        hosting_caption=HOSTING_CAPTION,
    )
