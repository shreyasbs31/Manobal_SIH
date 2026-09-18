from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal

from ..privacy.rights import KILLSWITCHES
from ..providers.router import get_router
from .prompts import bind_user, load_prompt

TaskName = Literal[
    "companion_turn",
    "crisis_classify",
    "output_guard",
    "checkin_extract",
    "instrument_conversational",
    "case_brief",
    "brief_verify",
    "command_copilot",
    "hq_brief",
    "transparency_report",
    "grievance_triage",
    "translate_ui",
    "conversation_coach",
]

TASK_KILL: dict[str, str] = {
    "companion_turn": "agent",
    "crisis_classify": "agent",
    "output_guard": "agent",
    "checkin_extract": "agent",
    "instrument_conversational": "agent",
    "case_brief": "briefs",
    "brief_verify": "briefs",
    "command_copilot": "copilot",
    "hq_brief": "briefs",
    "transparency_report": "briefs",
    "conversation_coach": "copilot",
}

TASK_SPEC: dict[str, dict[str, Any]] = {
    "companion_turn": {"capability": "companion_text", "temp": 0.3, "max_tokens": 220},
    "crisis_classify": {"capability": "crisis_classify", "temp": 0.0, "max_tokens": 80},
    "output_guard": {"capability": "output_guard", "temp": 0.0, "max_tokens": 80},
    "checkin_extract": {"capability": "checkin_extract", "temp": 0.0, "max_tokens": 160},
    "instrument_conversational": {"capability": "companion_text", "temp": 0.2, "max_tokens": 200},
    "case_brief": {"capability": "case_brief", "temp": 0.2, "max_tokens": 280},
    "brief_verify": {"capability": "brief_verify", "temp": 0.0, "max_tokens": 160},
    "command_copilot": {"capability": "command_copilot", "temp": 0.2, "max_tokens": 320},
    "hq_brief": {"capability": "hq_brief", "temp": 0.3, "max_tokens": 600},
    "transparency_report": {"capability": "hq_brief", "temp": 0.3, "max_tokens": 600},
    "grievance_triage": {"capability": "grievance_triage", "temp": 0.0, "max_tokens": 160},
    "translate_ui": {"capability": "translate", "temp": 0.0, "max_tokens": 400},
    "conversation_coach": {"capability": "command_copilot", "temp": 0.4, "max_tokens": 280},
}

MARKDOWN_RE = re.compile(r"[*_`#>]")


def strip_dashes(text: str) -> str:
    return text.replace("\u2014", ", ").replace("\u2013", ", ")


def strip_markdown(text: str) -> str:
    return MARKDOWN_RE.sub("", text)


@dataclass
class GatewayResult:
    task: str
    text: str
    provider: str
    latency_ms: float
    skipped: bool = False
    verified: bool | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def _paused_message(task: str) -> str:
    if task == "command_copilot":
        return "Copilot is paused."
    if task in {"case_brief", "hq_brief", "brief_verify", "transparency_report"}:
        return "Briefs are paused."
    return "Saathi is paused."


def local_brief_verify(brief: str, fields: dict[str, Any]) -> dict[str, Any]:
    allowed = {str(key).lower() for key in fields} | {
        str(value).lower() for value in fields.values() if isinstance(value, str)
    }
    for value in fields.values():
        if isinstance(value, list):
            allowed.update(str(item).lower() for item in value)
    unsupported: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", brief.strip()):
        if not sentence:
            continue
        lowered = sentence.lower()
        if not any(token in lowered for token in allowed if token):
            unsupported.append(sentence)
    return {"pass": not unsupported, "unsupported": unsupported}


def local_task_text(task: str, inputs: dict[str, Any], lang: str) -> str:
    if task == "crisis_classify":
        return json.dumps({"crisis": False, "confidence": 0.1, "category": "none"})
    if task == "output_guard":
        return json.dumps({"pass": True, "reason": ""})
    if task == "brief_verify":
        result = local_brief_verify(str(inputs.get("brief", "")), dict(inputs.get("fields") or {}))
        return json.dumps(result)
    if task == "checkin_extract":
        return json.dumps(
            {
                "mood": None,
                "energy": None,
                "sleep_quality": None,
                "sleep_hours": None,
                "tags": [],
            }
        )
    if task == "case_brief":
        fields = dict(inputs.get("fields") or {})
        tier = fields.get("tier", "T2")
        domain = fields.get("domain", "workload")
        onset = fields.get("onset", "about 20 days")
        lever = fields.get("lever", "REST_48H")
        if lang.startswith("hi"):
            return (
                f"स्तर {tier} है [tier]. "
                f"मुख्य क्षेत्र {domain} है [domain]. "
                f"बदलाव {onset} पहले दिखने लगा [onset]. "
                f"पहला लीवर {lever} है [lever]."
            )
        return (
            f"Tier is {tier} [tier]. "
            f"The leading domain is {domain} [domain]. "
            f"Drift began {onset} [onset]. "
            f"First lever to consider is {lever} [lever]."
        )
    if task == "command_copilot":
        from ..officers import copilot_answer

        result = copilot_answer(str(inputs.get("question", "")), lang)
        return json.dumps(result)
    if task == "grievance_triage":
        return json.dumps(
            {"category": "leave", "urgency": "medium", "redacted": "A leave delay was reported."}
        )
    if task == "companion_turn":
        if lang.startswith("hi"):
            return "Aapki baat samajh aa rahi hai. Aaj thoda aaram mil paya kya?"
        if lang.startswith("ta"):
            return "Ungalai ketkiren. Inru konjam ooyvu kidaithadha?"
        return "I hear you. Did you get a little rest today?"
    return "ok"


async def run(
    task: TaskName,
    inputs: dict[str, Any],
    lang: str,
    *,
    voice: bool = False,
    beat_id: str | None = None,
) -> GatewayResult:
    kill = TASK_KILL.get(task)
    if kill and KILLSWITCHES.get(kill):
        return GatewayResult(
            task=task,
            text=_paused_message(task),
            provider="killswitch",
            latency_ms=0.0,
            skipped=True,
        )
    prompt = load_prompt(task)
    spec = TASK_SPEC[task]
    capability = spec["capability"]
    if task == "companion_turn" and voice:
        capability = "companion_voice"
    tag = {
        "companion_turn": "user",
        "crisis_classify": "user",
        "output_guard": "draft",
        "checkin_extract": "session",
        "instrument_conversational": "item",
        "case_brief": "fields",
        "brief_verify": "brief",
        "command_copilot": "question",
        "hq_brief": "aggregates",
        "transparency_report": "metrics",
        "grievance_triage": "grievance",
        "translate_ui": "catalog",
        "conversation_coach": "practice",
    }[task]
    if task == "command_copilot":
        payload_text = (
            f"<question>{inputs.get('question', '')}</question>\n"
            f"<aggregates>{json.dumps(inputs.get('aggregates') or {}, default=str)}</aggregates>"
        )
        messages = [
            {"role": "system", "content": prompt.text},
            {"role": "user", "content": payload_text},
        ]
    elif task == "case_brief":
        payload_text = json.dumps(
            {"language": lang, "fields": inputs.get("fields") or {}},
            default=str,
        )
        messages = bind_user(prompt.text, "fields", payload_text)
    else:
        payload_text = str(inputs.get("text") or inputs.get("brief") or json.dumps(inputs, default=str))
        messages = bind_user(prompt.text, tag, payload_text)
    from ..config import get_settings, live_providers_enabled

    use_local = (not live_providers_enabled()) or (not get_settings().foundry_endpoint)
    extra: dict[str, Any] = {}
    provider = "local"
    latency_ms = 0.0
    if use_local:
        text = local_task_text(task, inputs, lang)
        if task == "crisis_classify":
            try:
                extra = json.loads(text)
            except json.JSONDecodeError:
                extra = {"crisis": False}
    else:
        router = get_router()
        model_class = ""
        if task == "companion_turn":
            from .routing_gate import load_recorded_routing

            decision = load_recorded_routing()
            if lang.startswith("hi-Latn"):
                model_class = str(decision.get("hi-Latn") or decision.get("hi") or "main")
            elif lang.startswith("hi"):
                model_class = str(decision.get("hi") or "main")
            elif lang.startswith("ta"):
                model_class = str(decision.get("ta") or "main")
            elif lang.startswith("en"):
                model_class = str(decision.get("en") or "open")
            else:
                model_class = "main"
        max_tokens = spec["max_tokens"]
        if task == "companion_turn" and voice:
            max_tokens = 128
            model_class = model_class or "fast"
        extra_payload = {
            "messages": messages,
            "text": payload_text,
            "temperature": spec["temp"],
            "max_tokens": max_tokens,
            "model_class": model_class,
            "voice": voice,
        }
        if task == "command_copilot":
            extra_payload["model_class"] = "main"
        response = await router.complete(
            capability,
            extra_payload,
            beat_id=beat_id,
            language=lang,
        )
        text = response.text
        provider = response.provider
        latency_ms = response.latency_ms
        extra = dict(response.extra)
        if task == "crisis_classify" and "crisis" not in extra:
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    extra.update(parsed)
            except json.JSONDecodeError:
                extra = {"crisis": True, "error": True}
        if response.provider == "fail_safe":
            text = local_task_text(task, inputs, lang)
            provider = "fail_safe"
    text = strip_dashes(text)
    if voice:
        text = strip_markdown(text)
    verified: bool | None = None
    if task in {"case_brief", "hq_brief"}:
        fields = dict(inputs.get("fields") or inputs.get("aggregates") or {})
        check = local_brief_verify(text, fields)
        verified = bool(check["pass"])
        if not verified:
            raise ValueError("brief_verify_failed")
    return GatewayResult(
        task=task,
        text=text,
        provider=provider,
        latency_ms=latency_ms,
        verified=verified,
        extra=extra,
    )


async def stream_companion_sentences(
    inputs: dict[str, Any],
    lang: str,
) -> AsyncIterator[str]:
    from ..config import get_settings, live_providers_enabled
    from ..providers.foundry import FoundryClient

    if not live_providers_enabled() or not get_settings().foundry_endpoint:
        text = local_task_text("companion_turn", inputs, lang)
        yield text
        return
    prompt = load_prompt("companion_turn")
    payload_text = str(inputs.get("text") or json.dumps(inputs, default=str))
    messages = bind_user(prompt.text, "user", payload_text)
    client = FoundryClient()
    async for sentence in client.chat_stream(
        "fast",
        messages,
        max_tokens=220,
        timeout_s=20.0,
    ):
        yield strip_dashes(strip_markdown(sentence))
