from __future__ import annotations

import base64
import json
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel

from .acute import AcuteRequest, AcuteResponse
from .audio import generate_audio, manifest, sw_cache_list
from .auth import PERSONAS, Principal
from .cases import CASES, acknowledge, digest_items, ensure_demo_cases, queue_items, remaining_ratio
from .config import get_settings
from .errors import ApiError
from .incident import (
    IncidentWebhook,
    lalit_demo_window,
    open_incident,
    uwo_board,
    verify_hmac,
)
from .levers import rank_levers
from .officers import (
    INDIVIDUAL_RE,
    acute_guide,
    case_brief_fields,
    command_posture_payload,
    copilot_answer,
    copilot_tools,
    counsel_desk,
    draft_order,
    hq_payload,
    hq_simulate,
    leave_pressure,
    medical_referrals,
    officer_profile,
    patch_officer_profile,
    project_roster,
    record_case_action,
    reveal_identity,
    roster_companies,
    save_contact_note,
    save_counsel_note,
    save_hq_brief,
    suggest_lever,
    text_pdf,
    unit_climate,
    welfare_tabs,
)
from .personnel import build_home, checkin_config
from .privacy.kanon import simulator_allows
from .privacy.rights import (
    KILLSWITCHES,
    break_glass,
    purge,
    request_trend_share,
    set_killswitch,
)
from .calls import issue_call_token
from .realtime import groups_for, negotiate_token, notify_ledger_viewed, notify_world
from .providers.endpoints import foundry_is_live
from .oversight import (
    admin_payload,
    advance_clock,
    architecture_payload,
    chain_state,
    dpo_decide,
    dpo_payload,
    director_payload,
    ensure_lab_worlds,
    gov_accuracy,
    gov_agent_safety,
    gov_enrolment,
    gov_fairness,
    gov_kpis,
    gov_models as gov_models_payload,
    gov_reviews,
    gov_rulesets,
    integrations_payload,
    integrations_upload,
    lab_payload,
    public_trust,
    reset_demo_state,
    restore_chain,
    set_admin_flag,
    set_outage,
    set_resilience,
    set_scenario,
    tamper_chain,
    transparency_pdf,
    transparency_report,
    decide_review,
)
from .security import RowPredicate, require

router = APIRouter(prefix="/api/v1")


class HomePayload(BaseModel):
    persona_id: str
    given_name: str
    greeting: str
    shift_line: str
    takeaway: str
    checkin: dict[str, object]
    nudge: dict[str, str]
    ribbon: list[dict[str, float]]
    persona: str = ""
    simple_mode: bool = False
    language: str = "en"
    context_cards: list[dict[str, str]] = []
    tiles: list[dict[str, str]] = []
    status: dict[str, object] = {}
    checkin_done: bool = False
    onboarding_done: bool = False
    lifecycle_state: str = "inducted"
    device_tier: str = "B"


class WelfareCaseOut(BaseModel):
    case_id: str
    subject_token: str
    tier: str
    trajectory: str
    drivers: list[str]
    drift: str
    sla_label: str
    remaining_ratio: float
    lever_id: str
    lever_title: str
    limited: bool
    source: str
    status: str


def _ensure_persona_cases() -> None:
    ensure_demo_cases()


@router.get("/me/home", response_model=HomePayload)
async def me_home(
    principal: Annotated[Principal, Depends(require("me:read", RowPredicate.OWN))],
) -> HomePayload:
    return HomePayload.model_validate(build_home(principal.subject_token))


@router.get("/me/trends")
async def me_trends(
    principal: Annotated[Principal, Depends(require("me:read", RowPredicate.OWN))],
) -> dict[str, object]:
    del principal
    return {
        "points": [{"day": day, "value": 6.2 - day * 0.03} for day in range(1, 15)],
    }


@router.get("/me/check-in")
async def me_check_in(
    principal: Annotated[Principal, Depends(require("me:read", RowPredicate.OWN))],
) -> dict[str, object]:
    return checkin_config(principal.subject_token)


@router.get("/me/voice")
async def me_voice(
    principal: Annotated[Principal, Depends(require("me:read", RowPredicate.OWN))],
) -> dict[str, object]:
    persona = next(item for item in PERSONAS.values() if item.token == principal.subject_token)
    language = {
        "arjun": "Hindi",
        "meena": "Hindi",
        "imran": "English",
        "thomas": "English",
        "lalit": "Hindi",
        "deepak": "Hinglish",
        "rajesh": "Hindi",
        "karthik": "Tamil",
    }.get(persona.id, "Hindi")
    return {
        "persona_id": persona.case_id,
        "language": language,
        "lines": [],
        "audio_cleared_ms": 84,
        "model_caption": (
            "Prototype: open-weight model hosted on Azure. Deployable on force servers."
        ),
    }


class CompanionTurnBody(BaseModel):
    text: str
    lang: str = "en"
    mode: str = "checkin"


@router.post("/companion/turn")
async def companion_turn(
    body: CompanionTurnBody,
    principal: Annotated[Principal, Depends(require("me:write", RowPredicate.OWN))],
) -> dict[str, object]:
    from .ai.corpus import retrieve
    from .ai.pipeline import HOSTING_CAPTION, run_pipeline

    chunks = [{"id": chunk.id, "text": chunk.text} for chunk in retrieve(body.text, body.lang)]
    result = await run_pipeline(
        body.text,
        lang=body.lang,
        mode=body.mode,
        token=principal.subject_token,
        chunks=chunks,
    )
    return {
        "acute": result.acute,
        "injection": result.injection,
        "reply": result.reply,
        "script": result.script,
        "mode": result.mode,
        "provider": result.provider,
        "citations": result.citations,
        "model_reached": result.model_reached,
        "gate": result.gate,
        "hosting_caption": HOSTING_CAPTION,
    }


VOICE_FIXTURES = {
    "arjun-hi": {"lang": "hi", "text": "रात की ड्यूटी के बाद नींद पूरी नहीं हुई"},
    "karthik-ta": {"lang": "ta", "text": "இரவு டியூட்டிக்கு பிறகு தூக்கம் சரியில்லை"},
    "deepak-distress": {"lang": "hi-Latn", "text": "main jeena nahi chahta"},
    "meena-en": {"lang": "en", "text": "Sleep was short after night duty."},
}
_FIXTURE_AUDIO: dict[str, dict[str, object]] = {}


@router.get("/voice/fixtures/{fixture_id}")
async def voice_fixture(
    fixture_id: str,
    principal: Annotated[Principal, Depends(require("me:read", RowPredicate.OWN))],
) -> dict[str, object]:
    del principal
    row = VOICE_FIXTURES.get(fixture_id)
    if row is None:
        raise ApiError("fixture_missing", "Unknown recorded turn", hint="Pick a Director preset", status_code=404)
    cached = _FIXTURE_AUDIO.get(fixture_id)
    if cached is not None:
        return cached
    from .voice.tts import synth_sentence

    audio, voice = await synth_sentence(row["text"], row["lang"])
    payload = {
        "id": fixture_id,
        "lang": row["lang"],
        "transcript": row["text"],
        "voice": voice,
        "audio_b64": base64.b64encode(audio).decode("ascii"),
    }
    _FIXTURE_AUDIO[fixture_id] = payload
    return payload


@router.get("/me/consents")
async def me_consents(
    principal: Annotated[Principal, Depends(require("me:read", RowPredicate.OWN))],
) -> dict[str, object]:
    return {
        "token": principal.subject_token,
        "items": [
            {
                "title": "Daily check-in",
                "leavesPhone": "Encrypted check-in summary only",
                "whoCanSee": "You. A welfare officer only after you agree.",
                "on": True,
            },
            {
                "title": "Voice conversation",
                "leavesPhone": "Nothing. Audio is cleared on the phone.",
                "whoCanSee": "Nobody. Captions stay in this session unless you save a journal.",
                "on": True,
            },
        ],
    }


@router.post("/me/purge/{data_type}")
async def me_purge(
    data_type: str,
    principal: Annotated[Principal, Depends(require("me:write", RowPredicate.OWN))],
) -> dict[str, object]:
    if principal.subject_token is None:
        raise ApiError(
            "scope_denied", "Personnel session required", hint="Sign in again", status_code=403
        )
    return purge(principal.subject_token, data_type, 12)


@router.get("/me/access-ledger")
async def me_ledger(
    principal: Annotated[Principal, Depends(require("me:read", RowPredicate.OWN))],
) -> dict[str, object]:
    from .cases import LEDGER

    items = [row for row in LEDGER if row.get("token") == principal.subject_token]
    return {"items": items}


@router.post("/acute", response_model=AcuteResponse)
async def acute(body: AcuteRequest) -> AcuteResponse:
    from .acute import enqueue_or_process

    return await enqueue_or_process(body)


@router.get("/welfare/queue")
async def welfare_queue(
    principal: Annotated[Principal, Depends(require("welfare:read", RowPredicate.UNIT_SUBTREE))],
) -> list[WelfareCaseOut]:
    _ensure_persona_cases()
    items = []
    for case in queue_items(principal.scope_path):
        if case.tier not in {"T2", "T3", "T4"}:
            continue
        levers = rank_levers(
            tier=case.tier,
            dominant_domains=case.dominant_domains,
            lifecycle_state="inducted",
        )
        top = levers[0]
        items.append(
            WelfareCaseOut(
                case_id=case.case_id,
                subject_token=case.token,
                tier=case.tier,
                trajectory=_trajectory(case.trajectory),
                drivers=case.dominant_domains,
                drift="Drift began about 20 days ago" if case.case_id == "MB-4091" else "Open case",
                sla_label=_sla_label(case.tier),
                remaining_ratio=remaining_ratio(case),
                lever_id=top.code,
                lever_title=top.label,
                limited=case.limited,
                source=case.source,
                status=case.status,
            )
        )
    return items


@router.get("/welfare/digest")
async def welfare_digest(
    principal: Annotated[Principal, Depends(require("welfare:read", RowPredicate.UNIT_SUBTREE))],
) -> list[str]:
    del principal
    _ensure_persona_cases()
    return [case.case_id for case in digest_items()]


@router.get("/welfare/cases/{case_id}")
async def welfare_case(
    case_id: str,
    principal: Annotated[Principal, Depends(require("welfare:read", RowPredicate.UNIT_SUBTREE))],
    lang: str = Query(default="hi"),
) -> dict[str, object]:
    _ensure_persona_cases()
    case = CASES.get(case_id)
    if case is None:
        raise ApiError(
            "case_not_found", "Case not found", hint="Refresh the queue", status_code=404
        )
    if not case.unit_path.startswith(principal.scope_path):
        raise ApiError(
            "scope_denied", "Outside this unit", hint="Stay in your unit", status_code=403
        )
    levers = rank_levers(
        tier=case.tier,
        dominant_domains=case.dominant_domains,
        lifecycle_state="inducted",
    )
    picked = list(levers[:3])
    for lever in levers:
        if lever.code == "NO_ACTION" and all(item.code != "NO_ACTION" for item in picked):
            picked.append(lever)
    recommended = [
        {
            "title": lever.label,
            "code": lever.code,
            "hint": "Often helpful in similar situations."
            if index == 0
            else "Draft only. You decide.",
            "rationale": "Ranked from the current domain mix.",
        }
        for index, lever in enumerate(picked)
    ]
    fields = case_brief_fields(case.case_id)
    from .ai.gateway import local_task_text, run as gateway_run

    try:
        brief_result = await gateway_run("case_brief", {"fields": fields, "text": json.dumps(fields)}, lang)
        brief = brief_result.text
        brief_provider = brief_result.provider
    except Exception:  # noqa: BLE001
        brief = local_task_text("case_brief", {"fields": fields}, lang)
        brief_provider = "local"
    if not any(f"[{key}]" in brief for key in ("tier", "domain", "onset", "lever")):
        brief = local_task_text("case_brief", {"fields": fields}, lang)
        if brief_provider != "local":
            brief_provider = f"{brief_provider}+marks"
    return {
        "case_id": case.case_id,
        "tier": case.tier,
        "trajectory": _trajectory(case.trajectory),
        "drivers": case.dominant_domains,
        "recommended": recommended,
        "levers": recommended,
        "what_changed": [
            {
                "title": domain.replace("_", " ").title(),
                "detail": "Outside the usual range for this person.",
            }
            for domain in case.dominant_domains[:3]
        ],
        "brief": brief,
        "brief_fields": fields,
        "brief_label": "Written by Saathi AI, check before use",
        "brief_provider": brief_provider,
        "openers": [
            "Aaj duty ke baad baat karne ka waqt hai?",
            "Kaise ho. Rest mil paaya kya?",
            "Kuch din se neend kam lag rahi hai. Kya main madad kar sakta hoon?",
        ],
        "strip": [
            {
                "day": day,
                "tier": "T0"
                if day < 40
                else "T1"
                if day < 70
                else "T2"
                if day < 100
                else case.tier,
            }
            for day in range(0, 120, 5)
        ],
        "onset_day": 100,
        "incidents": [118],
        "actions": [110],
        "sla_label": _sla_label(case.tier),
        "remaining_ratio": remaining_ratio(case),
        "limited": case.limited,
        "source": case.source,
        "status": case.status,
    }


@router.post("/welfare/cases/{case_id}/close")
async def welfare_close(
    case_id: str,
    body: dict[str, str],
    principal: Annotated[Principal, Depends(require("welfare:write", RowPredicate.UNIT_SUBTREE))],
) -> dict[str, str]:
    case = CASES[case_id]
    case.status = "closed"
    from .levers import record_decision

    record_decision(case_id, body.get("lever", "NO_ACTION"), body.get("outcome", "helpful"))
    del principal
    return {"status": "closed"}


@router.post("/welfare/breakglass")
async def welfare_breakglass(
    body: dict[str, str],
    principal: Annotated[Principal, Depends(require("welfare:write", RowPredicate.UNIT_SUBTREE))],
) -> dict[str, str]:
    return break_glass(
        actor=principal.actor_id,
        approver=body["approver"],
        target_token=body.get("target_hint", "st_364aifljnxnxpqzk"),
        justification=body["justification"],
    )


@router.post("/welfare/cases/{case_id}/trend-request")
async def welfare_trend_request(
    case_id: str,
    body: dict[str, str],
    principal: Annotated[Principal, Depends(require("welfare:write", RowPredicate.UNIT_SUBTREE))],
) -> dict[str, str]:
    case = CASES.get(case_id)
    token = case.token if case else "st_364aifljnxnxpqzk"
    del principal
    return request_trend_share(case_id, token, body["domain"])


@router.get("/welfare/incidents")
async def welfare_incidents(
    principal: Annotated[Principal, Depends(require("welfare:read", RowPredicate.UNIT_SUBTREE))],
) -> list[dict[str, str]]:
    lalit_demo_window()
    return uwo_board(principal.scope_path)


@router.get("/welfare/tabs")
async def welfare_tabs_view(
    principal: Annotated[Principal, Depends(require("welfare:read", RowPredicate.UNIT_SUBTREE))],
) -> dict[str, object]:
    _ensure_persona_cases()
    return welfare_tabs(principal.scope_path)


class RevealBody(BaseModel):
    purpose_code: str
    justification: str


@router.post("/welfare/cases/{case_id}/reveal")
async def welfare_reveal(
    case_id: str,
    body: RevealBody,
    principal: Annotated[Principal, Depends(require("welfare:write", RowPredicate.UNIT_SUBTREE))],
) -> dict[str, object]:
    _ensure_persona_cases()
    try:
        revealed = reveal_identity(
            case_id=case_id,
            actor=principal.actor_id,
            purpose_code=body.purpose_code,
            justification=body.justification,
        )
    except KeyError as error:
        raise ApiError(
            "case_not_found", "Case not found", hint="Refresh the queue", status_code=404
        ) from error
    except ValueError as error:
        raise ApiError(
            "reveal_rejected",
            "Purpose and a short justification are required",
            hint="Choose care contact and write why you need to reach them",
            status_code=422,
        ) from error
    record = CASES.get(case_id)
    if record is not None:
        await notify_ledger_viewed(subject_token=record.token, case_id=case_id)
    return revealed


class NoteBody(BaseModel):
    grant_id: str
    note: str


@router.post("/welfare/contact-note")
async def welfare_contact_note(
    body: NoteBody,
    principal: Annotated[Principal, Depends(require("welfare:write", RowPredicate.UNIT_SUBTREE))],
) -> dict[str, str]:
    del principal
    return save_contact_note(body.grant_id, body.note)


class CaseActionBody(BaseModel):
    mode: str = "call"
    lever: str = "REST_48H"
    outcome: str = "open"
    follow_up: str = ""
    refer: str = ""


@router.post("/welfare/cases/{case_id}/action")
async def welfare_action(
    case_id: str,
    body: CaseActionBody,
    principal: Annotated[Principal, Depends(require("welfare:write", RowPredicate.UNIT_SUBTREE))],
) -> dict[str, str]:
    del principal
    _ensure_persona_cases()
    return record_case_action(
        case_id,
        mode=body.mode,
        lever=body.lever,
        outcome=body.outcome,
        follow_up=body.follow_up,
        refer=body.refer,
    )


@router.get("/medical/acute")
async def medical_acute(
    principal: Annotated[Principal, Depends(require("medical:read", RowPredicate.UNIT_SUBTREE))],
) -> list[WelfareCaseOut]:
    _ensure_persona_cases()
    items = []
    for case in CASES.values():
        if case.tier != "T4":
            continue
        if not case.unit_path.startswith(principal.scope_path):
            continue
        items.append(
            WelfareCaseOut(
                case_id=case.case_id,
                subject_token=case.token,
                tier=case.tier,
                trajectory=_trajectory(case.trajectory),
                drivers=case.dominant_domains,
                drift="Acute path opened",
                sla_label=_sla_label(case.tier),
                remaining_ratio=remaining_ratio(case),
                lever_id="MO_REFERRAL",
                lever_title="Refer to a medical officer",
                limited=False,
                source=case.source,
                status=case.status,
            )
        )
    return items


@router.post("/medical/acute/{case_id}/ack")
async def medical_ack(
    case_id: str,
    principal: Annotated[Principal, Depends(require("medical:write", RowPredicate.UNIT_SUBTREE))],
) -> dict[str, str]:
    acknowledge(case_id, principal.actor_id)
    return {"status": "ack"}


@router.get("/command/posture")
async def command_posture(
    principal: Annotated[
        Principal, Depends(require("command:aggregate", RowPredicate.AGGREGATE_ONLY))
    ],
    unit: str = "force.central.c02",
    weeks: int = 12,
) -> dict[str, object]:
    del principal, unit, weeks
    payload = command_posture_payload()
    if not simulator_allows(100):
        raise ApiError(
            "k_anonymity", "Group is too small", hint="Pick a larger unit", status_code=422
        )
    return payload


@router.get("/command/metrics")
async def command_metrics(
    principal: Annotated[
        Principal, Depends(require("command:aggregate", RowPredicate.AGGREGATE_ONLY))
    ],
    unit: str = "force.central.c02",
    metric: str = "duty_hours",
    period: str = "week",
) -> dict[str, object]:
    del principal, unit, metric, period
    return {"values": [8.1, 8.4, 9.2], "k": 10}


@router.post("/command/simulate")
async def command_simulate(
    body: dict[str, Any],
    principal: Annotated[
        Principal, Depends(require("command:aggregate", RowPredicate.AGGREGATE_ONLY))
    ],
) -> dict[str, object]:
    del principal
    try:
        if "companies" in body:
            return project_roster(body)
        n = int(body.get("n") or 0)
        if not simulator_allows(n):
            raise ValueError("k_anonymity")
        return {"ok": True, "n": n}
    except ValueError as error:
        raise ApiError(
            "k_anonymity",
            "The simulator needs at least 10 people",
            hint="Widen the unit",
            status_code=422,
        ) from error


@router.get("/command/roster")
async def command_roster(
    principal: Annotated[
        Principal, Depends(require("command:aggregate", RowPredicate.AGGREGATE_ONLY))
    ],
) -> dict[str, object]:
    del principal
    return {"companies": roster_companies()}


@router.post("/command/draft-order")
async def command_draft_order(
    body: dict[str, Any],
    principal: Annotated[
        Principal, Depends(require("command:aggregate", RowPredicate.AGGREGATE_ONLY))
    ],
) -> dict[str, str]:
    del principal
    return draft_order(body)


@router.get("/command/leave")
async def command_leave(
    principal: Annotated[
        Principal, Depends(require("command:aggregate", RowPredicate.AGGREGATE_ONLY))
    ],
) -> dict[str, object]:
    del principal
    return leave_pressure()


@router.get("/command/climate")
async def command_climate(
    principal: Annotated[
        Principal, Depends(require("command:aggregate", RowPredicate.AGGREGATE_ONLY))
    ],
) -> dict[str, object]:
    del principal
    return unit_climate()


class CopilotBody(BaseModel):
    question: str
    lang: str = "en"


@router.post("/command/copilot")
async def command_copilot(
    body: CopilotBody,
    principal: Annotated[
        Principal, Depends(require("command:aggregate", RowPredicate.AGGREGATE_ONLY))
    ],
) -> dict[str, object]:
    del principal
    if INDIVIDUAL_RE.search(body.question or ""):
        refused = copilot_answer(body.question, body.lang)
        refused["provider"] = "refused"
        logging.getLogger("uvicorn.error").warning(
            "copilot refuse individual provider=refused"
        )
        return refused
    from .ai.gateway import run as gateway_run, strip_dashes

    tools = copilot_tools()
    try:
        result = await gateway_run(
            "command_copilot",
            {"question": body.question, "aggregates": tools, "text": body.question},
            body.lang,
        )
    except Exception:  # noqa: BLE001
        local = copilot_answer(body.question, body.lang)
        local["provider"] = "local"
        local["refuse"] = False
        return local
    text = strip_dashes(result.text)
    parsed: dict[str, object]
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = {}
    if isinstance(payload, dict) and payload.get("answer"):
        chart = payload.get("chart_spec") or {
            "type": "bar",
            "metric": "duty_hours",
            "value": tools["get_unit_metrics"]["duty_hours"],
        }
        parsed = {
            "refuse": False,
            "answer": strip_dashes(str(payload["answer"])),
            "chart_spec": chart,
            "tools_used": payload.get("tools_used") or ["get_unit_metrics", "list_top_drivers"],
            "provider": result.provider,
        }
    else:
        parsed = {
            "refuse": False,
            "answer": text,
            "chart_spec": {
                "type": "bar",
                "metric": "duty_hours",
                "value": tools["get_unit_metrics"]["duty_hours"],
            },
            "tools_used": ["get_unit_metrics", "list_top_drivers"],
            "provider": result.provider,
        }
    logging.getLogger("uvicorn.error").warning(
        "copilot aggregate provider=%s", parsed["provider"]
    )
    return parsed


@router.get("/hq/overview")
async def hq_overview(
    principal: Annotated[Principal, Depends(require("hq:aggregate", RowPredicate.AGGREGATE_ONLY))],
) -> dict[str, object]:
    del principal
    return hq_payload()


class HqBriefBody(BaseModel):
    body: str


@router.post("/hq/brief")
async def hq_brief_save(
    body: HqBriefBody,
    principal: Annotated[Principal, Depends(require("hq:aggregate", RowPredicate.AGGREGATE_ONLY))],
) -> dict[str, object]:
    del principal
    return save_hq_brief(body.body)


@router.get("/hq/brief.pdf")
async def hq_brief_pdf(
    principal: Annotated[Principal, Depends(require("hq:aggregate", RowPredicate.AGGREGATE_ONLY))],
) -> Response:
    del principal
    brief = hq_payload()["brief"]
    payload = text_pdf(str(brief["title"]), str(brief["body"]))
    return Response(content=payload, media_type="application/pdf")


class HqPolicyBody(BaseModel):
    leave_approval_rate: float | None = None
    max_consecutive_duty: int | None = None
    rotation_length_months: int | None = None
    quick_return_cap: int | None = None


@router.post("/hq/simulate")
async def hq_policy_simulate(
    body: HqPolicyBody,
    principal: Annotated[Principal, Depends(require("hq:aggregate", RowPredicate.AGGREGATE_ONLY))],
) -> dict[str, object]:
    del principal
    return hq_simulate(body.model_dump(exclude_none=True))


@router.get("/counsel/desk")
async def counsel_desk_view(
    principal: Annotated[Principal, Depends(require("counsel:read", RowPredicate.ASSIGNED))],
    language: str = "hi",
) -> dict[str, object]:
    del principal
    return counsel_desk(language)


class CounselNoteBody(BaseModel):
    session_id: str
    note: str


@router.post("/counsel/notes")
async def counsel_notes(
    body: CounselNoteBody,
    principal: Annotated[Principal, Depends(require("counsel:write", RowPredicate.ASSIGNED))],
) -> dict[str, str]:
    del principal
    return save_counsel_note(body.session_id, body.note)


class CounselSuggestBody(BaseModel):
    case_id: str
    lever: str = "REST_48H"
    sentence: str = "A rest cycle may help."


@router.post("/counsel/suggest")
async def counsel_suggest(
    body: CounselSuggestBody,
    principal: Annotated[Principal, Depends(require("counsel:write", RowPredicate.ASSIGNED))],
) -> dict[str, object]:
    del principal
    return suggest_lever(body.case_id, body.lever, body.sentence)


@router.get("/medical/referrals")
async def medical_referral_list(
    principal: Annotated[Principal, Depends(require("medical:read", RowPredicate.UNIT_SUBTREE))],
) -> dict[str, object]:
    return {"items": medical_referrals(principal.scope_path), "guide": acute_guide()}


@router.get("/officer/profile")
async def get_officer_profile(
    principal: Annotated[Principal, Depends(require("system:read", RowPredicate.AUTHENTICATED))],
) -> dict[str, object]:
    return {"actor_id": principal.actor_id, "role": principal.role.value, **officer_profile(principal.actor_id)}


@router.post("/officer/profile")
async def post_officer_profile(
    body: dict[str, Any],
    principal: Annotated[Principal, Depends(require("system:read", RowPredicate.AUTHENTICATED))],
) -> dict[str, object]:
    return patch_officer_profile(principal.actor_id, body)


@router.get("/hq/levers")
async def hq_levers(
    principal: Annotated[Principal, Depends(require("hq:aggregate", RowPredicate.AGGREGATE_ONLY))],
) -> dict[str, object]:
    del principal
    return {
        "note": "Observational, not causal",
        "items": [{"code": "REST_48H", "helpful_share": "hidden", "n": None}],
    }


@router.get("/gov/kpis")
async def gov_kpis_route(
    principal: Annotated[Principal, Depends(require("gov:read", RowPredicate.GOVERNANCE))],
) -> dict[str, object]:
    del principal
    return gov_kpis()


@router.get("/gov/fairness")
async def gov_fairness_route(
    principal: Annotated[Principal, Depends(require("gov:read", RowPredicate.GOVERNANCE))],
) -> dict[str, object]:
    del principal
    return gov_fairness()


@router.get("/gov/models")
async def gov_models_route(
    principal: Annotated[Principal, Depends(require("gov:read", RowPredicate.GOVERNANCE))],
) -> dict[str, object]:
    del principal
    from .config import live_providers_enabled
    from .ai.corpus import LIVE_EMBEDDED, run_retrieval_eval

    if live_providers_enabled() and not LIVE_EMBEDDED:
        try:
            await run_retrieval_eval()
        except Exception:  # noqa: BLE001
            pass
    return gov_models_payload()


async def gov_models(principal: Principal) -> dict[str, object]:
    del principal
    return gov_models_payload()


@router.get("/gov/killswitches")
async def gov_killswitches(
    principal: Annotated[Principal, Depends(require("gov:read", RowPredicate.GOVERNANCE))],
) -> dict[str, bool]:
    del principal
    return dict(KILLSWITCHES)


@router.post("/gov/killswitches/{name}")
async def gov_set_killswitch(
    name: str,
    principal: Annotated[Principal, Depends(require("gov:write", RowPredicate.GOVERNANCE))],
) -> dict[str, object]:
    if name == "acute":
        raise ApiError(
            "acute_locked",
            "The acute path cannot be switched off",
            hint="Acute stays on",
            status_code=409,
        )
    enabled = not KILLSWITCHES.get(name, False)
    set_killswitch(name, enabled, principal.actor_id)
    return {"name": name, "enabled": enabled}


@router.get("/gov/rulesets")
async def gov_rulesets_route(
    principal: Annotated[Principal, Depends(require("gov:read", RowPredicate.GOVERNANCE))],
) -> dict[str, object]:
    del principal
    return gov_rulesets()


@router.get("/gov/accuracy")
async def gov_accuracy_route(
    principal: Annotated[Principal, Depends(require("gov:read", RowPredicate.GOVERNANCE))],
) -> dict[str, object]:
    del principal
    return gov_accuracy()


@router.get("/gov/audit")
async def gov_audit_route(
    principal: Annotated[Principal, Depends(require("gov:read", RowPredicate.GOVERNANCE))],
) -> dict[str, object]:
    del principal
    return chain_state()


@router.post("/gov/audit/tamper")
async def gov_audit_tamper(
    principal: Annotated[Principal, Depends(require("gov:write", RowPredicate.GOVERNANCE))],
) -> dict[str, object]:
    del principal
    return tamper_chain()


@router.post("/gov/audit/restore")
async def gov_audit_restore(
    principal: Annotated[Principal, Depends(require("gov:write", RowPredicate.GOVERNANCE))],
) -> dict[str, object]:
    del principal
    return restore_chain()


@router.get("/gov/reviews")
async def gov_reviews_route(
    principal: Annotated[Principal, Depends(require("gov:read", RowPredicate.GOVERNANCE))],
) -> dict[str, object]:
    del principal
    return gov_reviews()


class ReviewBody(BaseModel):
    status: str


@router.post("/gov/reviews/{review_id}")
async def gov_review_decide(
    review_id: str,
    body: ReviewBody,
    principal: Annotated[Principal, Depends(require("gov:write", RowPredicate.GOVERNANCE))],
) -> dict[str, object]:
    del principal
    return decide_review(review_id, body.status)


@router.get("/gov/agent-safety")
async def gov_agent_safety_route(
    principal: Annotated[Principal, Depends(require("gov:read", RowPredicate.GOVERNANCE))],
) -> dict[str, object]:
    del principal
    return gov_agent_safety()


@router.get("/gov/enrolment-integrity")
async def gov_enrolment_route(
    principal: Annotated[Principal, Depends(require("gov:read", RowPredicate.GOVERNANCE))],
) -> dict[str, object]:
    del principal
    return gov_enrolment()


@router.post("/gov/transparency-report")
async def gov_transparency(
    principal: Annotated[Principal, Depends(require("gov:write", RowPredicate.GOVERNANCE))],
) -> dict[str, object]:
    del principal
    return transparency_report()


@router.get("/gov/transparency-report.pdf")
async def gov_transparency_pdf(
    principal: Annotated[Principal, Depends(require("gov:read", RowPredicate.GOVERNANCE))],
) -> Response:
    del principal
    transparency_report()
    return Response(
        content=transparency_pdf(),
        media_type="application/pdf",
        headers={"content-disposition": 'attachment; filename="transparency.pdf"'},
    )


@router.post("/incidents")
async def incidents(
    request: Request,
    x_signature: Annotated[str, Header(alias="x-signature")],
    x_timestamp: Annotated[int, Header(alias="x-timestamp")],
    x_nonce: Annotated[str, Header(alias="x-nonce")],
) -> dict[str, str]:
    from .config import get_settings

    body = await request.body()
    try:
        verify_hmac(
            get_settings().incident_hmac_secret.get_secret_value(),
            body,
            x_signature,
            x_timestamp,
            x_nonce,
        )
    except ValueError as error:
        raise ApiError(
            "incident_rejected",
            "The incident webhook could not be verified",
            hint="Check HMAC, timestamp, and nonce",
            status_code=401,
        ) from error
    payload = IncidentWebhook.model_validate_json(body)
    window = open_incident(payload)
    return {"id": window.id, "status": "open"}


@router.post("/realtime/negotiate")
async def realtime_negotiate(
    principal: Annotated[Principal, Depends(require("system:read", RowPredicate.AUTHENTICATED))],
) -> dict[str, object]:
    return {"token": negotiate_token(principal), "groups": groups_for(principal)}


@router.post("/calls/token")
async def calls_token(
    principal: Annotated[Principal, Depends(require("me:write", RowPredicate.OWN))],
) -> dict[str, object]:
    del principal
    return await issue_call_token()


@router.get("/admin/audio")
async def admin_audio(
    principal: Annotated[Principal, Depends(require("demo:write", RowPredicate.DEMO_CONTROL))],
) -> dict[str, object]:
    del principal
    return {"manifest": manifest(), "cache": sw_cache_list()}


@router.post("/admin/audio")
async def admin_audio_generate(
    principal: Annotated[Principal, Depends(require("demo:write", RowPredicate.DEMO_CONTROL))],
) -> dict[str, object]:
    del principal
    return generate_audio()


@router.get("/gov/providers")
async def gov_providers(
    principal: Annotated[Principal, Depends(require("gov:read", RowPredicate.GOVERNANCE))],
) -> dict[str, object]:
    del principal
    from .providers.router import PROVIDER_CALLS, get_router

    router = get_router()
    return {
        "capabilities": {name: router.ordered(name) for name in router.config["capabilities"]},
        "calls": [
            {
                "capability": item.capability,
                "provider": item.provider,
                "latency_ms": item.latency_ms,
                "ok": item.ok,
                "cached": item.cached,
            }
            for item in PROVIDER_CALLS[-50:]
        ],
        "foundry_configured": foundry_is_live(get_settings()),
    }


@router.post("/demo/warmup")
async def demo_warmup(
    principal: Annotated[Principal, Depends(require("demo:write", RowPredicate.DEMO_CONTROL))],
) -> dict[str, str]:
    del principal
    from .providers.router import get_router

    return await get_router().warmup()


@router.post("/demo/seed-ready")
async def seed_ready() -> dict[str, str]:
    from .config import get_settings

    if get_settings().manobal_mode != "demo":
        raise ApiError(
            "scope_denied", "Seed hook is demo only", hint="Use demo mode", status_code=403
        )
    _ensure_persona_cases()
    ensure_lab_worlds()
    return {"status": "ready"}


@router.post("/lab/benchmark")
async def lab_benchmark(
    principal: Annotated[Principal, Depends(require("gov:read", RowPredicate.GOVERNANCE))],
) -> dict[str, object]:
    del principal
    from .scoring.core import score_generated_subjects

    result = score_generated_subjects(80_000)
    return {"subjects": result["subjects"], "seconds": result["seconds"]}


class DpoDecision(BaseModel):
    decision: str


class FlagBody(BaseModel):
    name: str
    enabled: bool


class UploadBody(BaseModel):
    filename: str
    rows: list[dict[str, Any]] = []


class OutageBody(BaseModel):
    provider: str
    opened: bool = True


class ResilienceBody(BaseModel):
    enabled: bool


class ClockJump(BaseModel):
    days: int = 0
    running: bool | None = None
    speed: float | None = None


@router.get("/public/trust")
async def public_trust_route() -> dict[str, object]:
    return public_trust()


@router.get("/public/architecture")
async def public_architecture_route() -> dict[str, object]:
    return architecture_payload()


@router.get("/dpo/requests")
async def dpo_requests(
    principal: Annotated[Principal, Depends(require("dpo:read", RowPredicate.AUTHENTICATED))],
) -> dict[str, object]:
    del principal
    return dpo_payload()


@router.post("/dpo/requests/{request_id}")
async def dpo_request_decide(
    request_id: str,
    body: DpoDecision,
    principal: Annotated[Principal, Depends(require("dpo:write", RowPredicate.AUTHENTICATED))],
) -> dict[str, object]:
    del principal
    return dpo_decide(request_id, body.decision)


@router.get("/integrations/jobs")
async def integrations_jobs(
    principal: Annotated[
        Principal, Depends(require("integrations:read", RowPredicate.AUTHENTICATED))
    ],
) -> dict[str, object]:
    del principal
    return integrations_payload()


@router.get("/integrations/quality")
async def integrations_quality(
    principal: Annotated[
        Principal, Depends(require("integrations:read", RowPredicate.AUTHENTICATED))
    ],
) -> dict[str, object]:
    del principal
    return integrations_payload()


@router.post("/integrations/hrms/upload")
async def integrations_hrms_upload(
    body: UploadBody,
    principal: Annotated[
        Principal, Depends(require("integrations:write", RowPredicate.AUTHENTICATED))
    ],
) -> dict[str, object]:
    del principal
    return integrations_upload(body.filename, body.rows)


@router.get("/admin/console")
async def admin_console(
    principal: Annotated[Principal, Depends(require("admin:read", RowPredicate.AUTHENTICATED))],
) -> dict[str, object]:
    del principal
    return admin_payload()


@router.post("/admin/flags")
async def admin_flags(
    body: FlagBody,
    principal: Annotated[Principal, Depends(require("admin:write", RowPredicate.AUTHENTICATED))],
) -> dict[str, object]:
    del principal
    return set_admin_flag(body.name, body.enabled)


@router.get("/lab/metrics")
async def lab_metrics(
    principal: Annotated[Principal, Depends(require("gov:read", RowPredicate.GOVERNANCE))],
    world: str = "primary",
) -> dict[str, object]:
    del principal
    return lab_payload(world)


@router.get("/lab/overview")
async def lab_overview(
    principal: Annotated[Principal, Depends(require("gov:read", RowPredicate.GOVERNANCE))],
) -> dict[str, object]:
    del principal
    return lab_payload("primary")


@router.get("/architecture/live")
async def architecture_live(
    principal: Annotated[Principal, Depends(require("system:read", RowPredicate.AUTHENTICATED))],
) -> dict[str, object]:
    del principal
    return architecture_payload()


@router.get("/director/board")
async def director_board(
    principal: Annotated[Principal, Depends(require("demo:write", RowPredicate.DEMO_CONTROL))],
) -> dict[str, object]:
    del principal
    return director_payload()


@router.post("/demo/scenario/{name}")
async def demo_scenario(
    name: str,
    principal: Annotated[Principal, Depends(require("demo:write", RowPredicate.DEMO_CONTROL))],
) -> dict[str, object]:
    del principal
    result = set_scenario(name)
    await notify_world("scenario")
    return result


@router.post("/demo/reset")
async def demo_reset(
    principal: Annotated[Principal, Depends(require("demo:write", RowPredicate.DEMO_CONTROL))],
) -> dict[str, object]:
    del principal
    result = reset_demo_state()
    await notify_world("reset")
    return result


@router.post("/demo/tamper")
async def demo_tamper(
    principal: Annotated[Principal, Depends(require("demo:write", RowPredicate.DEMO_CONTROL))],
) -> dict[str, object]:
    del principal
    result = tamper_chain()
    await notify_world("tamper")
    return result


@router.post("/demo/restore")
async def demo_restore(
    principal: Annotated[Principal, Depends(require("demo:write", RowPredicate.DEMO_CONTROL))],
) -> dict[str, object]:
    del principal
    result = restore_chain()
    await notify_world("restore")
    return result


@router.post("/demo/outage")
async def demo_outage(
    body: OutageBody,
    principal: Annotated[Principal, Depends(require("demo:write", RowPredicate.DEMO_CONTROL))],
) -> dict[str, object]:
    del principal
    result = set_outage(body.provider, body.opened)
    await notify_world("outage")
    return result


@router.post("/demo/resilience")
async def demo_resilience(
    body: ResilienceBody,
    principal: Annotated[Principal, Depends(require("demo:write", RowPredicate.DEMO_CONTROL))],
) -> dict[str, object]:
    del principal
    result = set_resilience(body.enabled)
    await notify_world("resilience")
    return result


@router.post("/demo/director-clock")
async def demo_director_clock(
    body: ClockJump,
    principal: Annotated[Principal, Depends(require("demo:write", RowPredicate.DEMO_CONTROL))],
) -> dict[str, object]:
    del principal
    result = advance_clock(days=body.days, running=body.running, speed=body.speed)
    await notify_world("clock")
    return result


@router.post("/demo/nightly")
async def demo_nightly(
    principal: Annotated[Principal, Depends(require("demo:write", RowPredicate.DEMO_CONTROL))],
) -> dict[str, object]:
    del principal
    _ensure_persona_cases()
    ensure_lab_worlds()
    await notify_world("nightly")
    return {"status": "scored", "subjects": 8000}


@router.post("/demo/cost-exceeded")
async def demo_cost_exceeded(
    principal: Annotated[Principal, Depends(require("demo:write", RowPredicate.DEMO_CONTROL))],
) -> dict[str, object]:
    del principal
    from .observability import set_cost_guard

    set_cost_guard(True)
    return {"cost_guard": True}


@router.get("/system/metrics")
async def system_metrics(
    principal: Annotated[Principal, Depends(require("system:read", RowPredicate.AUTHENTICATED))],
) -> dict[str, object]:
    del principal
    from .observability import metrics_payload

    return metrics_payload()


def _sla_label(tier: str) -> str:
    return {"T4": "11:42", "T3": "46:10", "T2": "5d 04h"}.get(tier, "7d")


def _trajectory(value: str) -> str:
    if value == "rising":
        return "rising"
    if value in {"falling", "easing"}:
        return "easing"
    return "steady"
