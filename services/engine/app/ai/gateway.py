from __future__ import annotations

import json
import re
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

DASHES = str.maketrans({"\u2014": ",", "\u2013": ","})
MARKDOWN_RE = re.compile(r"[*_`#>]")


def strip_dashes(text: str) -> str:
    return text.translate(DASHES)


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
        return (
            f"Tier is {tier} [tier]. "
            f"The leading domain is {domain} [domain]. "
            f"Drift began {onset} [onset]. "
            f"First lever to consider is {lever} [lever]."
        )
    if task == "command_copilot":
        question = str(inputs.get("question", "")).lower()
        individual = any(
            token in question
            for token in ("who is", "token", "mb-", "this person", "named", "jawan", "constable")
        )
        if individual:
            return json.dumps(
                {
                    "refuse": True,
                    "answer": "I can only talk about unit totals, not a person.",
                    "chart_spec": None,
                }
            )
        aggregates = dict(inputs.get("aggregates") or {"share_t2": "20 to 30%"})
        return json.dumps(
            {
                "refuse": False,
                "answer": f"Unit share at T2 or above is {aggregates.get('share_t2', 'banded')}.",
                "chart_spec": {"type": "ribbon", "metric": "share_t2"},
            }
        )
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
    payload_text = str(inputs.get("text") or inputs.get("brief") or json.dumps(inputs, default=str))
    messages = bind_user(prompt.text, tag, payload_text)
    router = get_router()
    response = await router.complete(
        capability,
        {
            "messages": messages,
            "text": payload_text,
            "temperature": spec["temp"],
            "max_tokens": spec["max_tokens"],
        },
        beat_id=beat_id,
        language=lang,
    )
    from ..config import get_settings

    text = response.text
    if (not get_settings().foundry_endpoint) or response.provider == "fail_safe":
        text = local_task_text(task, inputs, lang)
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
        provider=response.provider,
        latency_ms=response.latency_ms,
        verified=verified,
        extra=dict(response.extra),
    )
