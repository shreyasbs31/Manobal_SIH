from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal
from uuid import uuid4

import yaml
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from .auth import PERSONAS, Principal
from .config import get_settings
from .errors import ApiError
from .i18n import SCHEDULED, catalog_for, t
from .personalisation import PERSONALISATION_FIELDS, get_profile, public_profile, update_profile
from .privacy.rights import KILLSWITCHES, RECEIPTS, TREND_REQUESTS, purge
from .recommender import TOOLKIT_IDS, observe_reward, ranking_payload
from .scoring.forecast import ADVERSE_FEATURES, EXCLUDED_ATTRIBUTES, REGISTRY
from .scoring.ruleset import REPO_ROOT
from .security import RowPredicate, require

router = APIRouter(prefix="/api/v1")

JITAI_PATH = REPO_ROOT / "infra" / "rulesets" / "jitai.yaml"
SCORING_FIELDS = frozenset(
    {"mood", "energy", "sleep_quality", "sleep_hours", "tags", "token", "at", "channel"}
)
FORBIDDEN_OFFICER = frozenset(
    {
        "simple_mode",
        "helpers",
        "family_context",
        "voice_preference",
        "personal_goals",
        "what_helps",
        "remembers",
        "sunday_family_call",
        "checkin_style",
        "quiet_hours",
    }
)

CHECKINS: dict[str, list[dict[str, Any]]] = {}
ASSESSMENTS: dict[str, dict[str, dict[str, Any]]] = {}
BOOKINGS: dict[str, list[dict[str, Any]]] = {}
TALK_REQUESTS: dict[str, list[dict[str, Any]]] = {}
CONCERNS: dict[str, list[dict[str, Any]]] = {}
BUDDY: dict[str, dict[str, Any]] = {}
FAMILY: dict[str, dict[str, Any]] = {}
SAFETY_BACKUP: dict[str, dict[str, Any]] = {}
PULSES: dict[str, list[dict[str, Any]]] = {}
ONBOARD_RECEIPTS: dict[str, dict[str, Any]] = {}
EDGE_QUEUE: list[dict[str, Any]] = []
EDGE_LINK_UP = True
JITAI_LOG: dict[str, list[dict[str, Any]]] = {}
SCORING_INBOX: list[dict[str, Any]] = []

CONSENTS = (
    {
        "id": "hr_derived",
        "title": "Duty and leave from records",
        "leavesPhone": "Duty hours and leave balances, already on unit systems",
        "whoCanSee": "Welfare officer for your unit, never your commander by name",
        "default": True,
    },
    {
        "id": "self_report",
        "title": "Daily check-in",
        "leavesPhone": "Mood, energy, sleep, and tags you choose",
        "whoCanSee": "Only you unless you ask someone to help",
        "default": False,
    },
    {
        "id": "wearable",
        "title": "Wearable rest signals",
        "leavesPhone": "Rest and heart-rate summaries, not a live stream",
        "whoCanSee": "Only you, and a welfare officer if you later share a trend",
        "default": False,
    },
    {
        "id": "ai_conversation",
        "title": "Talks with Saathi",
        "leavesPhone": "A short session summary. Audio is cleared.",
        "whoCanSee": "Only you",
        "default": False,
    },
    {
        "id": "voice",
        "title": "Voice on this phone",
        "leavesPhone": "Speech is turned into text, then the audio is dropped",
        "whoCanSee": "Only you",
        "default": False,
    },
)

INSTRUMENTS = (
    {
        "id": "pss10",
        "title": "PSS-10",
        "badge": "validated",
        "self_only": False,
        "items": 10,
    },
    {
        "id": "who5",
        "title": "WHO-5",
        "badge": "validated",
        "self_only": False,
        "items": 5,
    },
    {
        "id": "cbi",
        "title": "CBI",
        "badge": "validated",
        "self_only": False,
        "items": 6,
    },
    {
        "id": "phq9",
        "title": "PHQ-9",
        "badge": "validated",
        "self_only": False,
        "items": 9,
    },
    {
        "id": "gad7",
        "title": "GAD-7",
        "badge": "validated",
        "self_only": False,
        "items": 7,
    },
    {
        "id": "pcptsd5",
        "title": "PC-PTSD-5",
        "badge": "validated",
        "self_only": False,
        "incident_only": True,
        "items": 5,
    },
    {
        "id": "auditc",
        "title": "AUDIT-C",
        "badge": "self_only",
        "self_only": True,
        "items": 3,
    },
)

TOOLKIT_COPY = {
    "box_breathing": ("Box breathing", "A four-count cycle. Two minutes."),
    "four_seven_eight": ("4-7-8 breathing", "A longer exhale to settle the body."),
    "grounding": ("5-4-3-2-1 grounding", "Name what you can see, feel, and hear."),
    "sleep_wind_down": ("Sleep wind-down", "Ten quiet minutes of audio."),
    "yoga_nidra": ("Short yoga nidra", "A guided rest while you stay awake."),
    "body_scan": ("Body scan", "Notice each part of the body without judging."),
    "post_duty": ("Post-duty decompression", "A short come-down after a long shift."),
    "tactical_nap": ("Tactical nap guide", "How to nap without wrecking tonight's sleep."),
    "heat_cold": ("Heat and cold tips", "Theatre-aware rest and water notes."),
    "anger_cooldown": ("Anger cool-down", "A paced walk-through when tempers rise."),
    "letter_home": ("Letter home", "A private prompt to write to someone who matters."),
    "journal": ("Private journal", "Stays on this phone."),
    "music_decompress": ("Music after duty", "A quiet listen to come down."),
    "articles": ("Short reads", "Articles from the care library, with audio."),
}

CHECKIN_TAGS = (
    "Duty",
    "Family",
    "Health",
    "Money",
    "Colleagues",
    "Leave",
    "Land or property",
    "Nothing specific",
)

HELPERS = (
    "music",
    "prayer or reflection",
    "walking",
    "sport",
    "talking to someone",
    "breathing",
    "writing",
    "sleep",
)

PHQ9_ITEMS = (
    "Little interest or pleasure in doing things",
    "Feeling down, low, or hopeless",
    "Trouble falling or staying asleep, or sleeping too much",
    "Feeling tired or having little energy",
    "Poor appetite or overeating",
    "Feeling bad about yourself",
    "Trouble concentrating",
    "Moving or speaking slowly, or being fidgety",
    "Thoughts that you would be better off dead, or of hurting yourself",
)

PSS_ITEMS = (
    "In the last month, how often have you been upset because of something "
    "that happened unexpectedly?",
    "In the last month, how often have you felt that you were unable to control "
    "the important things in your life?",
    "In the last month, how often have you felt nervous and stressed?",
    "In the last month, how often have you felt confident about your ability "
    "to handle your personal problems?",
    "In the last month, how often have you felt that things were going your way?",
    "In the last month, how often have you found that you could not cope with "
    "all the things that you had to do?",
    "In the last month, how often have you been able to control irritations in your life?",
    "In the last month, how often have you felt that you were on top of things?",
    "In the last month, how often have you been angered because of things that "
    "were outside of your control?",
    "In the last month, how often have you felt difficulties were piling up so high "
    "that you could not overcome them?",
)


class OnboardingBody(BaseModel):
    language: str = "hi"
    consents: dict[str, bool] = Field(default_factory=dict)
    exception_understood: bool = False
    simple_mode: bool | None = None
    helpers: list[str] = Field(default_factory=list)
    family_context: str = ""
    skip_buddy: bool = True
    skip_safety_plan: bool = True
    skip_wearable: bool = True
    device_tier: str = "B"


class CheckInBody(BaseModel):
    mood: int | None = None
    energy: int | None = None
    sleep_quality: int | None = None
    sleep_hours: float | None = None
    tags: list[str] = Field(default_factory=list)
    channel: Literal["tap", "voice", "offline_voice"] = "tap"
    skipped: bool = False


class AssessmentAnswer(BaseModel):
    item: int
    value: int
    conversational: bool = False


class TalkBody(BaseModel):
    kind: Literal["uwo", "counsellor"]
    anonymous: bool = False
    mode: Literal["request", "book", "call_now"] = "request"
    voice: bool = True
    video: bool = False
    slot: str | None = None


class BuddyBody(BaseModel):
    action: Literal["pair", "unpair", "ping", "ok"]
    code: str | None = None


class PersonalisationBody(BaseModel):
    patch: dict[str, Any]


class JitaiBody(BaseModel):
    action: Literal["not_now", "open"]


class EdgeBody(BaseModel):
    up: bool


class SyncItem(BaseModel):
    kind: str
    payload: dict[str, Any]
    client_id: str


class PulseBody(BaseModel):
    kind: Literal["unit", "trust"]
    value: int


class ConcernBody(BaseModel):
    category: str = "leave"
    text: str = ""
    anonymous: bool = False


class RememberBody(BaseModel):
    opt_in: bool | None = None
    forget: bool = False
    item: str | None = None
    group: str = "what helps"


def _persona(token: str | None) -> Any:
    for persona in PERSONAS.values():
        if persona.token == token:
            return persona
    return PERSONAS["arjun"]


def _jitai_rules() -> dict[str, Any]:
    return yaml.safe_load(JITAI_PATH.read_text(encoding="utf-8"))


def scoring_payload(token: str, body: CheckInBody) -> dict[str, Any]:
    payload = {
        "token": token,
        "at": datetime.now(UTC).isoformat(),
        "mood": body.mood,
        "energy": body.energy,
        "sleep_quality": body.sleep_quality,
        "sleep_hours": body.sleep_hours,
        "tags": list(body.tags),
        "channel": body.channel,
    }
    extra = set(payload) - SCORING_FIELDS
    if extra:
        raise ValueError(f"scoring leak {extra}")
    for field in PERSONALISATION_FIELDS:
        if field in payload:
            raise ValueError(f"personalisation in scoring {field}")
    return payload


def assert_officer_clean(payload: object) -> None:
    blob = json.dumps(payload, default=str).lower()
    for field in FORBIDDEN_OFFICER:
        if field in blob:
            raise AssertionError(f"officer payload contains {field}")


def checkin_config(token: str | None) -> dict[str, Any]:
    profile = get_profile(token)
    skipped = int(profile.get("skipped_checkins") or 0)
    voice_streak = int(profile.get("checkin_voice_streak") or 0)
    busy = skipped >= 2 or profile.get("checkin_style") == "busy"
    questions = [{"id": "mood", "prompt": "How is your mood right now?"}]
    if not busy:
        questions.extend(
            [
                {"id": "energy", "prompt": "How is your energy right now?"},
                {"id": "sleep", "prompt": "How was your sleep?"},
            ]
        )
    return {
        "questions": questions,
        "busy_day": busy,
        "voice_default": voice_streak >= 3,
        "tags": list(CHECKIN_TAGS),
        "saved": t("checkin.saved", str(profile.get("language") or "en")),
    }


def _context_cards(profile: dict[str, Any], persona_id: str) -> list[dict[str, str]]:
    cards: list[dict[str, str]] = []
    lifecycle = str(profile.get("lifecycle_state") or "inducted")
    if lifecycle == "return_from_leave":
        cards.append(
            {
                "title": "Settling back",
                "detail": "Three quiet days to find your rhythm again.",
                "why": "You are returning from leave. This card is only for you.",
                "kind": "lifecycle",
            }
        )
    jitai = evaluate_jitai(profile, persona_id)
    if jitai:
        cards.append(jitai)
    has_leave = any(card.get("rule") == "LEAVE_WINDOW" or card["kind"] == "leave" for card in cards)
    if persona_id == "meena" and int(profile.get("el_days") or 0) >= 20 and not has_leave:
        cards.append(
            {
                "title": "A leave window looks possible",
                "detail": "EL 42 days. Open the planner when you have a minute.",
                "why": "Leave balance is high and a feasible window exists after de-induction.",
                "kind": "leave",
            }
        )
    if persona_id == "arjun" and not any(card["kind"] == "jitai" for card in cards):
        cards.append(
            {
                "title": "Sleep before tonight's duty",
                "detail": "A 20-minute nap plan",
                "why": "Roster days are running long this rotation. This is a private nudge.",
                "kind": "nudge",
            }
        )
    pending = [
        row
        for row in TREND_REQUESTS
        if row.get("token") == profile.get("token") and row.get("status") == "pending"
    ]
    if pending:
        cards.append(
            {
                "title": "A trend-share request is waiting",
                "detail": "You choose whether anyone sees a trend.",
                "why": (
                    "A welfare officer asked to view a trend. Nothing is shared until you agree."
                ),
                "kind": "trend_share",
            }
        )
    return cards[:2]


def evaluate_jitai(profile: dict[str, Any], persona_id: str) -> dict[str, str] | None:
    if KILLSWITCHES.get("jitai"):
        return None
    if profile.get("on_duty") or profile.get("quiet_hours_active"):
        return None
    rules = _jitai_rules()
    caps = rules.get("caps") or {}
    not_until = profile.get("jitai_not_now_until")
    now = datetime.now(UTC)
    if not_until:
        until = datetime.fromisoformat(str(not_until))
        if until > now:
            return None
    if int(profile.get("jitai_day_count") or 0) >= int(caps.get("per_day") or 1):
        return None
    if int(profile.get("jitai_week_count") or 0) >= int(caps.get("per_week") or 4):
        return None
    del persona_id
    candidates: list[dict[str, str]] = []
    table = rules.get("rules") or {}
    if profile.get("night_within_24h") and "NIGHT_TOMORROW" in table:
        candidates.append(
            {
                "title": "Nap and light plan for tonight",
                "detail": "A short wind-down before the next night duty.",
                "why": "A night shift starts within 24 hours. This is a private self-care prompt.",
                "kind": "jitai",
                "rule": "NIGHT_TOMORROW",
            }
        )
    if int(profile.get("consecutive_duty") or 0) >= 10 and "DUTY_STREAK_10" in table:
        candidates.append(
            {
                "title": "Five-minute recovery routine",
                "detail": "A short reset after many duty days in a row.",
                "why": "This is the tenth consecutive duty day in the cached roster.",
                "kind": "jitai",
                "rule": "DUTY_STREAK_10",
            }
        )
    if int(profile.get("el_days") or 0) >= 30 and "LEAVE_WINDOW" in table:
        candidates.append(
            {
                "title": "Leave planner suggestion",
                "detail": "A feasible window is on the planner.",
                "why": "Leave balance is high and a window exists. MANOBAL does not submit leave.",
                "kind": "jitai",
                "rule": "LEAVE_WINDOW",
            }
        )
    if int(profile.get("sleep_nights_low") or 0) >= 3 and "LOW_SLEEP_3" in table:
        candidates.append(
            {
                "title": "Sleep toolkit",
                "detail": "Wind-down audio is ready on this phone.",
                "why": "Three nights under your usual sleep. This stays with you.",
                "kind": "jitai",
                "rule": "LOW_SLEEP_3",
            }
        )
    if int(profile.get("hours_to_next_shift") or 99) < 11 and "QUICK_RETURN" in table:
        candidates.append(
            {
                "title": "Wind-down before the next shift",
                "detail": "Audio and a caffeine cut-off are on this phone.",
                "why": "The next shift starts in under 11 hours.",
                "kind": "jitai",
                "rule": "QUICK_RETURN",
            }
        )
    if profile.get("unit_incident_72h") and "POST_INCIDENT" in table:
        candidates.append(
            {
                "title": "A private check-in is open",
                "detail": "Your unit went through something hard. This card is only for you.",
                "why": (
                    "A unit incident was flagged in the last 72 hours. "
                    "Nobody is flagged for skipping."
                ),
                "kind": "jitai",
                "rule": "POST_INCIDENT",
            }
        )
    if int(profile.get("days_without_checkin") or 0) >= 7 and "SILENCE_7" in table:
        candidates.append(
            {
                "title": "We are here when you want a check-in",
                "detail": "No pressure. A two-minute check-in is enough.",
                "why": "It has been a week since the last check-in on this phone.",
                "kind": "jitai",
                "rule": "SILENCE_7",
            }
        )
    return candidates[0] if candidates else None


def build_home(token: str | None) -> dict[str, Any]:
    persona = _persona(token)
    profile = get_profile(token)
    lang = str(profile.get("language") or persona.language)
    greetings = {
        "arjun": "Suprabhat, Arjun",
        "meena": "Namaste, Meena",
        "karthik": t("home.greeting.karthik", "ta"),
        "imran": "Good morning, Imran",
        "thomas": "Good morning, Thomas",
        "lalit": "Namaste, Lalit",
        "deepak": "Hello Deepak",
        "rajesh": "Namaste, Rajesh",
    }
    greeting = greetings.get(persona.id, f"Hello, {persona.display_label.split()[-1]}")
    sleep_n = int(profile.get("sleep_nights_low") or 0)
    if persona.id == "arjun" and sleep_n:
        takeaway = t("home.lay.sleepLow", "en" if lang == "en" else lang, n=sleep_n)
        if "{n}" in takeaway:
            takeaway = t("home.lay.sleepLow", "en", n=sleep_n)
    elif persona.id == "karthik":
        takeaway = "A few quiet days to settle back. This view is only yours."
    elif persona.id == "meena":
        takeaway = "A leave window is open after de-induction. This view is only yours."
    else:
        takeaway = t("home.lay.within", lang if lang in {"en", "hi"} else "en")
    cards = _context_cards(profile, persona.id)
    nudge = (
        cards[0]
        if cards
        else {
            "title": "A quiet check-in",
            "detail": "Optional, on your time",
            "why": "A private card when you want it.",
            "kind": "nudge",
        }
    )
    done = bool(CHECKINS.get(token or "", []))
    checkin_title = t("home.checkin.title", lang if lang in {"en", "hi", "ta"} else "en")
    return {
        "persona_id": persona.case_id,
        "persona": persona.id,
        "given_name": persona.display_label.split()[-1],
        "greeting": greeting,
        "shift_line": str(profile.get("shift_line") or "Duty"),
        "takeaway": takeaway,
        "checkin": {
            "title": "Done for today" if done else checkin_title,
            "duration_s": 20,
            "href": "/app/check-in",
            "done": done,
        },
        "nudge": {
            "title": nudge["title"],
            "detail": nudge["detail"],
            "why": nudge["why"],
        },
        "ribbon": [
            {"day": float(day), "value": value}
            for day, value in (
                (1, 6.4),
                (3, 6.2),
                (5, 6.1),
                (7, 5.8),
                (9, 5.4),
                (11, 4.9),
                (13, 4.4),
                (14, 4.2),
            )
        ],
        "simple_mode": bool(profile.get("simple_mode")),
        "language": lang,
        "context_cards": cards,
        "tiles": [
            {"href": "/app/saathi", "label": "Talk"},
            {"href": "/app/toolkit/breathe", "label": "Breathe"},
            {"href": "/app/talk", "label": "Counsellor"},
            {"href": "/app/rest", "label": "Leave"},
            {"href": "/app/concerns", "label": "Concern"},
        ],
        "status": {
            "wearable": "connected" if profile.get("consents", {}).get("wearable") else "off",
            "last_sync": profile.get("updated_at"),
            "queued": 0,
        },
        "checkin_done": done,
        "onboarding_done": bool(profile.get("onboarding_done")),
        "lifecycle_state": profile.get("lifecycle_state"),
        "device_tier": profile.get("device_tier"),
    }


def toolkit_for(token: str | None) -> dict[str, Any]:
    profile = get_profile(token)
    context = {
        "time_of_day": "morning",
        "shift_phase": "post_duty" if profile.get("night_within_24h") else "rest",
        "theatre": profile.get("theatre"),
        "lifecycle_state": profile.get("lifecycle_state"),
        "helpers": profile.get("what_helps") or profile.get("helpers") or [],
        "tags": "",
    }
    ranked = ranking_payload(context)
    items = []
    for item_id in ranked["order"]:
        title, detail = TOOLKIT_COPY[item_id]
        items.append(
            {
                "id": item_id,
                "title": title,
                "detail": detail,
                "href": f"/app/toolkit/{item_id}",
                "offline": True,
            }
        )
    return {"items": items, "ranking": ranked, "audio": ["/audio/breathing.en.wav"]}


def rest_plan(token: str | None) -> dict[str, Any]:
    profile = get_profile(token)
    el = int(profile.get("el_days") or 0)
    cl = int(profile.get("cl_days") or 0)
    window = None
    if el >= 20:
        window = {
            "start": "2026-10-04",
            "end": "2026-10-12",
            "travel_days": 2,
            "note": (
                "Unit blackout windows are shown at unit level only. "
                "MANOBAL does not submit leave."
            ),
        }
    days = [
        {
            "label": "Mon",
            "start": 18,
            "end": 62,
            "sleep": "13:00-17:00 nap",
            "caffeine": "none after 14:00",
        },
        {"label": "Tue", "start": 0, "end": 0, "sleep": "22:00-06:00", "caffeine": "morning only"},
        {
            "label": "Wed",
            "start": 20,
            "end": 70,
            "sleep": "14:00-16:00 nap",
            "caffeine": "none after 15:00",
        },
        {
            "label": "Thu",
            "start": 20,
            "end": 70,
            "sleep": "14:00-16:00 nap",
            "caffeine": "none after 15:00",
        },
        {"label": "Fri", "start": 0, "end": 0, "sleep": "22:00-06:00", "caffeine": "morning only"},
        {"label": "Sat", "start": 8, "end": 50, "sleep": "23:00-07:00", "caffeine": "morning only"},
        {"label": "Sun", "start": 0, "end": 0, "sleep": "22:00-06:00", "caffeine": "morning only"},
    ]
    return {
        "el_days": el,
        "cl_days": cl,
        "window": window,
        "copy": "MANOBAL does not submit leave.",
        "days": days,
    }


def talk_state(token: str | None) -> dict[str, Any]:
    settings = get_settings()
    acs = bool(settings.acs_connection_string.get_secret_value())
    return {
        "requests": TALK_REQUESTS.get(token or "", []),
        "bookings": BOOKINGS.get(token or "", []),
        "acs_configured": acs,
        "demo_join": not acs,
        "demo_label": (
            "Demo join. Calls use Azure Communication Services when a connection string is set."
        ),
        "anonymous_handle": "River-17",
    }


@router.get("/me/onboarding")
async def get_onboarding(
    principal: Annotated[Principal, Depends(require("me:read", RowPredicate.OWN))],
) -> dict[str, Any]:
    profile = public_profile(principal.subject_token)
    return {
        "languages": list(SCHEDULED) + ["en"],
        "consents": CONSENTS,
        "exception": t("exception.body", str(profile.get("language") or "en")),
        "helpers": list(HELPERS),
        "profile": {
            "language": profile.get("language"),
            "simple_mode": profile.get("simple_mode"),
            "helpers": profile.get("helpers"),
            "family_context": profile.get("family_context"),
            "onboarding_done": profile.get("onboarding_done"),
            "device_tier": profile.get("device_tier"),
        },
        "receipt": ONBOARD_RECEIPTS.get(principal.subject_token or ""),
    }


@router.post("/me/onboarding")
async def post_onboarding(
    body: OnboardingBody,
    principal: Annotated[Principal, Depends(require("me:write", RowPredicate.OWN))],
) -> dict[str, Any]:
    if not body.exception_understood:
        raise ApiError(
            "exception_required",
            "Please confirm you understand the one exception",
            hint="Read the card and tap I understand",
            status_code=422,
        )
    consents = {
        "hr_derived": True,
        "self_report": False,
        "wearable": False,
        "ai_conversation": False,
        "voice": False,
    }
    consents.update(body.consents)
    consents["hr_derived"] = True
    patch: dict[str, Any] = {
        "language": body.language,
        "consents": consents,
        "exception_understood": True,
        "onboarding_done": True,
        "device_tier": body.device_tier,
        "helpers": body.helpers,
        "what_helps": body.helpers,
        "family_context": body.family_context,
    }
    if body.simple_mode is not None:
        patch["simple_mode"] = body.simple_mode
    if not body.skip_wearable:
        consents["wearable"] = True
        patch["consents"] = consents
    profile = update_profile(principal.subject_token, patch)
    digest = hashlib.sha256(
        json.dumps(
            {"token": principal.subject_token, "consents": consents, "at": profile["updated_at"]},
            sort_keys=True,
        ).encode()
    ).hexdigest()
    receipt = {
        "hash": digest,
        "time": profile["updated_at"],
        "skipped": {
            "buddy": body.skip_buddy,
            "safety_plan": body.skip_safety_plan,
            "wearable": body.skip_wearable,
        },
    }
    ONBOARD_RECEIPTS[principal.subject_token or ""] = receipt
    return {"receipt": receipt, "profile": {"onboarding_done": True, "language": body.language}}


@router.post("/me/check-in")
async def post_checkin(
    body: CheckInBody,
    principal: Annotated[Principal, Depends(require("me:write", RowPredicate.OWN))],
) -> dict[str, Any]:
    token = principal.subject_token or ""
    profile = get_profile(token)
    if body.skipped:
        update_profile(token, {"skipped_checkins": int(profile.get("skipped_checkins") or 0) + 1})
        return {"saved": False, "skipped": True}
    payload = scoring_payload(token, body)
    SCORING_INBOX.append(payload)
    CHECKINS.setdefault(token, []).append({**payload, "local_id": str(uuid4())})
    skipped = 0
    voice_streak = int(profile.get("checkin_voice_streak") or 0)
    if body.channel == "voice":
        voice_streak += 1
    else:
        voice_streak = 0
    update_profile(
        token,
        {
            "skipped_checkins": skipped,
            "checkin_voice_streak": voice_streak,
            "checkin_style": body.channel,
        },
    )
    lang = str(profile.get("language") or "en")
    return {
        "saved": True,
        "message": t("checkin.saved", lang if lang in {"en", "hi", "ta"} else "en"),
        "scoring": payload,
    }


@router.get("/me/assessments")
async def list_assessments(
    principal: Annotated[Principal, Depends(require("me:read", RowPredicate.OWN))],
) -> dict[str, Any]:
    del principal
    return {
        "items": [
            {
                **item,
                "due": "Optional",
                "badge_label": "Self-only" if item["self_only"] else "Validated translation",
            }
            for item in INSTRUMENTS
        ]
    }


@router.get("/me/assessments/{instrument_id}")
async def get_assessment(
    instrument_id: str,
    principal: Annotated[Principal, Depends(require("me:read", RowPredicate.OWN))],
) -> dict[str, Any]:
    del principal
    match = next((item for item in INSTRUMENTS if item["id"] == instrument_id), None)
    if match is None:
        raise ApiError(
            "not_found", "Instrument not found", hint="Pick from the list", status_code=404
        )
    if instrument_id == "phq9":
        prompts = list(PHQ9_ITEMS)
    elif instrument_id == "pss10":
        prompts = list(PSS_ITEMS)
    else:
        prompts = [f"Item {index + 1}" for index in range(int(match["items"]))]
    return {
        **match,
        "prompts": prompts,
        "options": ["Not at all", "Several days", "More than half the days", "Nearly every day"],
    }


@router.post("/me/assessments/{instrument_id}")
async def post_assessment(
    instrument_id: str,
    body: AssessmentAnswer,
    principal: Annotated[Principal, Depends(require("me:write", RowPredicate.OWN))],
) -> dict[str, Any]:
    token = principal.subject_token or ""
    store = ASSESSMENTS.setdefault(token, {}).setdefault(
        instrument_id, {"answers": {}, "self_only": instrument_id == "auditc"}
    )
    store["answers"][str(body.item)] = body.value
    safety = instrument_id == "phq9" and body.item == 9 and body.value > 0
    if instrument_id == "auditc":
        return {"saved": True, "self_only": True, "device_only": True, "safety": False}
    return {
        "saved": True,
        "self_only": False,
        "safety": safety,
        "verbatim": body.conversational,
        "confirm": f"Saved item {body.item} as {body.value}",
    }


@router.get("/me/toolkit")
async def get_toolkit(
    principal: Annotated[Principal, Depends(require("me:read", RowPredicate.OWN))],
) -> dict[str, Any]:
    return toolkit_for(principal.subject_token)


@router.post("/me/toolkit/{item_id}/reward")
async def toolkit_reward(
    item_id: str,
    principal: Annotated[Principal, Depends(require("me:write", RowPredicate.OWN))],
    reward: str = "completed",
) -> dict[str, Any]:
    if item_id not in TOOLKIT_IDS:
        raise ApiError(
            "not_found", "Toolkit item not found", hint="Use a listed item", status_code=404
        )
    profile = get_profile(principal.subject_token)
    context = {
        "time_of_day": "morning",
        "shift_phase": "post_duty" if profile.get("night_within_24h") else "rest",
        "theatre": profile.get("theatre"),
        "lifecycle_state": profile.get("lifecycle_state"),
        "helpers": profile.get("helpers") or [],
    }
    observe_reward(context, item_id, reward)
    return {"ok": True, "order": ranking_payload(context)["order"]}


@router.get("/me/rest")
async def get_rest(
    principal: Annotated[Principal, Depends(require("me:read", RowPredicate.OWN))],
) -> dict[str, Any]:
    return rest_plan(principal.subject_token)


@router.get("/me/talk")
async def get_talk(
    principal: Annotated[Principal, Depends(require("me:read", RowPredicate.OWN))],
) -> dict[str, Any]:
    return talk_state(principal.subject_token)


@router.post("/me/talk")
async def post_talk(
    body: TalkBody,
    principal: Annotated[Principal, Depends(require("me:write", RowPredicate.OWN))],
) -> dict[str, Any]:
    token = principal.subject_token or ""
    row = {
        "id": str(uuid4())[:8],
        "kind": body.kind,
        "anonymous": body.anonymous,
        "mode": body.mode,
        "voice": body.voice,
        "video": body.video,
        "slot": body.slot,
        "status": "queued" if body.mode == "request" else "booked",
        "handle": "River-17" if body.anonymous else None,
        "identity_shared": (not body.anonymous) and body.kind == "uwo",
    }
    TALK_REQUESTS.setdefault(token, []).append(row)
    if body.mode in {"book", "call_now"}:
        BOOKINGS.setdefault(token, []).append(row)
    return {"request": row, **talk_state(token)}


@router.get("/me/buddy")
async def get_buddy(
    principal: Annotated[Principal, Depends(require("me:read", RowPredicate.OWN))],
) -> dict[str, Any]:
    token = principal.subject_token or ""
    row = BUDDY.get(token) or {"paired": False}
    return {
        "paired": bool(row.get("paired")),
        "code": row.get("code"),
        "lessons": [
            "Notice a change in sleep or replies, then ask once, kindly.",
            "Listen more than you advise.",
            "If you are worried, ask the welfare officer for help. You will not see any data.",
        ],
        "privacy": "A buddy never sees any data, tier, or score.",
    }


@router.post("/me/buddy")
async def post_buddy(
    body: BuddyBody,
    principal: Annotated[Principal, Depends(require("me:write", RowPredicate.OWN))],
) -> dict[str, Any]:
    token = principal.subject_token or ""
    if body.action == "unpair":
        BUDDY.pop(token, None)
        return {"paired": False, "notified": False}
    if body.action == "pair":
        code = body.code or uuid4().hex[:6]
        BUDDY[token] = {"paired": True, "code": code, "pings": []}
        return {"paired": True, "code": code, "tier": None, "score": None, "other_token": None}
    row = BUDDY.setdefault(token, {"paired": True, "code": "buddy", "pings": []})
    if body.action == "ping":
        row["pings"].append({"kind": "check_in", "at": datetime.now(UTC).isoformat()})
    if body.action == "ok":
        row["pings"].append({"kind": "ok", "at": datetime.now(UTC).isoformat()})
    return {"paired": True, "event": body.action, "tier": None, "score": None}


@router.get("/me/family")
async def get_family(
    principal: Annotated[Principal, Depends(require("me:read", RowPredicate.OWN))],
) -> dict[str, Any]:
    token = principal.subject_token or ""
    row = FAMILY.get(token) or {
        "reminder": "sunday" if get_profile(token).get("sunday_family_call") else None,
        "link": "/family",
    }
    return {
        "reminder": row.get("reminder"),
        "share_link": "/family",
        "personal_data": False,
        "resources": [
            "How to support someone far away",
            "Tele-MANAS 14416",
            "Force family welfare contacts",
        ],
    }


@router.post("/me/family")
async def post_family(
    principal: Annotated[Principal, Depends(require("me:write", RowPredicate.OWN))],
    reminder: str = "sunday",
) -> dict[str, Any]:
    token = principal.subject_token or ""
    FAMILY[token] = {"reminder": reminder, "link": "/family"}
    update_profile(token, {"sunday_family_call": reminder == "sunday"})
    return {"reminder": reminder, "share_link": "/family", "personal_data": False}


@router.get("/family")
async def family_public() -> dict[str, Any]:
    return {
        "title": "Family connect",
        "personal_data": False,
        "resources": [
            "How to support someone far away",
            "Tele-MANAS 14416",
            "Force family welfare contacts",
        ],
        "concern": "A family member can reach the sector counsellor without creating a flag.",
    }


@router.post("/me/safety-plan")
async def backup_safety_plan(
    principal: Annotated[Principal, Depends(require("me:write", RowPredicate.OWN))],
    body: dict[str, str],
) -> dict[str, Any]:
    token = principal.subject_token or ""
    SAFETY_BACKUP[token] = {**body, "at": datetime.now(UTC).isoformat()}
    return {"backed_up": True}


@router.get("/me/rights")
async def get_rights(
    principal: Annotated[Principal, Depends(require("me:read", RowPredicate.OWN))],
) -> dict[str, Any]:
    profile = public_profile(principal.subject_token)
    return {
        "notice": {
            "version": "2026.09",
            "hash": hashlib.sha256(b"manobal-privacy-notice-2026.09").hexdigest()[:16],
            "language": profile.get("language"),
        },
        "actions": [
            "Read the privacy notice",
            "See my data",
            "Correct my data",
            "Erase a data type",
            "Nominate a person",
            "Raise a grievance with the DPO",
            "See who accessed what and why",
        ],
        "receipts": [row for row in RECEIPTS if row.get("token") == principal.subject_token],
        "onboarding": ONBOARD_RECEIPTS.get(principal.subject_token or ""),
        "remembers_opt_in": profile.get("remembers_opt_in"),
        "simple_mode": profile.get("simple_mode"),
    }


@router.post("/me/rights/erase")
async def rights_erase(
    principal: Annotated[Principal, Depends(require("me:write", RowPredicate.OWN))],
    data_type: str = "self_report",
) -> dict[str, Any]:
    receipt = purge(principal.subject_token or "", data_type, 1)
    return receipt


@router.post("/me/concerns")
async def raise_concern(
    body: ConcernBody,
    principal: Annotated[Principal, Depends(require("me:write", RowPredicate.OWN))],
) -> dict[str, Any]:
    token = principal.subject_token or ""
    row = {
        "id": str(uuid4())[:8],
        "category": body.category,
        "text": body.text[:400],
        "anonymous": body.anonymous,
        "status": "received",
        "sla": "5 working days",
        "due": (datetime.now(UTC) + timedelta(days=5)).date().isoformat(),
    }
    CONCERNS.setdefault(token, []).append(row)
    return row


@router.get("/me/concerns")
async def list_concerns(
    principal: Annotated[Principal, Depends(require("me:read", RowPredicate.OWN))],
) -> dict[str, Any]:
    return {"items": CONCERNS.get(principal.subject_token or "", [])}


@router.get("/me/remembers")
async def get_remembers(
    principal: Annotated[Principal, Depends(require("me:read", RowPredicate.OWN))],
) -> dict[str, Any]:
    profile = get_profile(principal.subject_token)
    return {
        "opt_in": bool(profile.get("remembers_opt_in")),
        "items": list(profile.get("remembers") or []),
        "groups": ["people who matter", "what helps", "what to avoid talking about", "my goals"],
    }


@router.post("/me/remembers")
async def post_remembers(
    body: RememberBody,
    principal: Annotated[Principal, Depends(require("me:write", RowPredicate.OWN))],
) -> dict[str, Any]:
    profile = get_profile(principal.subject_token)
    remembers = list(profile.get("remembers") or [])
    if body.forget:
        remembers = []
        update_profile(principal.subject_token, {"remembers": [], "remembers_opt_in": False})
    elif body.opt_in is not None:
        update_profile(principal.subject_token, {"remembers_opt_in": body.opt_in})
    elif body.item and profile.get("remembers_opt_in"):
        remembers.append({"group": body.group, "text": body.item[:80]})
        update_profile(principal.subject_token, {"remembers": remembers[:20]})
    return {
        "opt_in": bool(get_profile(principal.subject_token).get("remembers_opt_in")),
        "items": list(get_profile(principal.subject_token).get("remembers") or []),
    }


@router.post("/me/personalisation")
async def post_personalisation(
    body: PersonalisationBody,
    principal: Annotated[Principal, Depends(require("me:write", RowPredicate.OWN))],
) -> dict[str, Any]:
    allowed = {
        key: value
        for key, value in body.patch.items()
        if key in PERSONALISATION_FIELDS or key in {"consents"}
    }
    update_profile(principal.subject_token, allowed)
    return {"profile": public_profile(principal.subject_token)}


@router.post("/me/jitai/not-now")
async def jitai_not_now(
    principal: Annotated[Principal, Depends(require("me:write", RowPredicate.OWN))],
) -> dict[str, Any]:
    until = datetime.now(UTC) + timedelta(hours=72)
    update_profile(principal.subject_token, {"jitai_not_now_until": until.isoformat()})
    return {"silenced_until": until.isoformat()}


@router.post("/me/pulse")
async def post_pulse(
    body: PulseBody,
    principal: Annotated[Principal, Depends(require("me:write", RowPredicate.OWN))],
) -> dict[str, Any]:
    token = principal.subject_token or ""
    PULSES.setdefault(token, []).append(
        {"kind": body.kind, "value": body.value, "at": datetime.now(UTC).isoformat()}
    )
    return {"saved": True, "anonymous": True, "individual_hidden": True}


@router.get("/me/offline-snapshot")
async def offline_snapshot(
    principal: Annotated[Principal, Depends(require("me:read", RowPredicate.OWN))],
) -> dict[str, Any]:
    token = principal.subject_token
    return {
        "home": build_home(token),
        "checkin": checkin_config(token),
        "toolkit": toolkit_for(token),
        "assessments": [
            {"id": item["id"], "title": item["title"], "self_only": item["self_only"]}
            for item in INSTRUMENTS
        ],
        "trends": {"points": [{"day": day, "value": 6.2 - day * 0.03} for day in range(1, 15)]},
        "safety": {
            "title": t("safety.title", str(get_profile(token).get("language") or "en")),
            "sms": f"sms:{get_settings().unit_sms_number}?body=SOS%20from%20Saathi",
        },
        "lexicon": True,
        "nudges": local_nudge_rules(get_profile(token)),
    }


def local_nudge_rules(profile: dict[str, Any]) -> list[dict[str, str]]:
    cards = []
    if int(profile.get("sleep_nights_low") or 0) >= 3:
        cards.append({"title": "Sleep toolkit", "why": "Three nights of low sleep on this phone."})
    if int(profile.get("consecutive_duty") or 0) >= 10:
        cards.append(
            {"title": "Five-minute recovery", "why": "Ten duty days in a row in the cached roster."}
        )
    return cards


@router.post("/me/sync")
async def sync_queue(
    items: list[SyncItem],
    principal: Annotated[Principal, Depends(require("me:write", RowPredicate.OWN))],
) -> dict[str, Any]:
    global EDGE_LINK_UP
    accepted = []
    if not EDGE_LINK_UP:
        for item in items:
            EDGE_QUEUE.append(
                {"kind": item.kind, "client_id": item.client_id, "token": principal.subject_token}
            )
        return {"drained": 0, "held": len(items), "edge_up": False}
    for item in items:
        accepted.append(item.client_id)
        if item.kind == "checkin":
            body = CheckInBody.model_validate(item.payload)
            await post_checkin(body, principal)
    return {"drained": len(accepted), "ids": accepted, "edge_up": True}


@router.post("/demo/edge-link")
async def set_edge_link(
    body: EdgeBody,
    principal: Annotated[Principal, Depends(require("demo:write", RowPredicate.DEMO_CONTROL))],
) -> dict[str, Any]:
    global EDGE_LINK_UP
    del principal
    EDGE_LINK_UP = body.up
    drained = 0
    if EDGE_LINK_UP and EDGE_QUEUE:
        drained = len(EDGE_QUEUE)
        EDGE_QUEUE.clear()
    return {"up": EDGE_LINK_UP, "queued": len(EDGE_QUEUE), "drained": drained}


@router.get("/demo/edge-queue")
async def get_edge_queue(
    principal: Annotated[Principal, Depends(require("demo:write", RowPredicate.DEMO_CONTROL))],
) -> dict[str, Any]:
    del principal
    return {"up": EDGE_LINK_UP, "queued": len(EDGE_QUEUE), "items": list(EDGE_QUEUE[-20:])}


@router.get("/i18n/{lang}")
async def get_i18n(lang: str) -> dict[str, Any]:
    return catalog_for(lang)


def forecast_feature_names() -> list[str]:
    names: list[str] = []
    for model in REGISTRY.values():
        names.extend(getattr(model, "feature_names", []) or [])
    names.extend(ADVERSE_FEATURES)
    return names


def personalisation_isolated() -> dict[str, Any]:
    features = set(forecast_feature_names())
    leaked = sorted(field for field in PERSONALISATION_FIELDS if field in features)
    excluded_ok = "language" in EXCLUDED_ATTRIBUTES
    return {"leaked_into_features": leaked, "language_excluded": excluded_ok}
