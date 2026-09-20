from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from .auth import PERSONAS
from .scoring.forecast import ADVERSE_FEATURES, EXCLUDED_ATTRIBUTES

PERSONALISATION_FIELDS = frozenset(
    {
        "simple_mode",
        "helpers",
        "family_context",
        "voice_preference",
        "voice_speed",
        "checkin_style",
        "quiet_hours",
        "personal_goals",
        "device_tier",
        "data_saver",
        "theatre",
        "lifecycle_state",
        "rank_band",
        "language",
        "script",
        "accessibility",
        "remembers",
        "remembers_opt_in",
        "onboarding_done",
        "what_helps",
    }
)

# Language and similar profile fields are excluded from scoring (good).
# They must never appear as forecast features.
assert PERSONALISATION_FIELDS.isdisjoint(ADVERSE_FEATURES)
assert "language" in EXCLUDED_ATTRIBUTES

PROFILES: dict[str, dict[str, Any]] = {}

_DEFAULTS: dict[str, dict[str, Any]] = {
    "arjun": {
        "language": "hi",
        "simple_mode": True,
        "helpers": ["music", "talking to someone"],
        "family_context": "partner_and_child",
        "voice_preference": "female",
        "theatre": "central",
        "lifecycle_state": "inducted",
        "rank_band": "constable",
        "device_tier": "B",
        "shift_line": "Night duty ended at 06:00",
        "el_days": 18,
        "cl_days": 4,
        "consecutive_duty": 11,
        "night_within_24h": True,
        "sleep_nights_low": 3,
    },
    "meena": {
        "language": "hi",
        "simple_mode": False,
        "helpers": ["prayer or reflection", "talking to someone"],
        "family_context": "children_with_grandparents",
        "voice_preference": "female",
        "theatre": "east",
        "lifecycle_state": "de_induction",
        "rank_band": "hc",
        "device_tier": "A",
        "shift_line": "Leave window after de-induction",
        "el_days": 42,
        "cl_days": 8,
        "section_leader": True,
        "sunday_family_call": True,
    },
    "karthik": {
        "language": "ta",
        "simple_mode": False,
        "helpers": ["walking", "writing"],
        "family_context": "bereavement_return",
        "voice_preference": "female",
        "theatre": "east",
        "lifecycle_state": "return_from_leave",
        "rank_band": "constable",
        "device_tier": "B",
        "shift_line": "Settling back after leave",
        "el_days": 6,
        "cl_days": 2,
        "leave_days": 35,
    },
}


def _base(persona_id: str) -> dict[str, Any]:
    profile = {
        "language": PERSONAS[persona_id].language if persona_id in PERSONAS else "en",
        "simple_mode": False,
        "helpers": [],
        "family_context": "",
        "voice_preference": "female",
        "voice_speed": 1.0,
        "checkin_style": "tap",
        "quiet_hours": True,
        "personal_goals": [],
        "device_tier": "B",
        "data_saver": True,
        "theatre": "central",
        "lifecycle_state": "inducted",
        "rank_band": "constable",
        "script": "Deva",
        "accessibility": {"captions": True, "text_size": "md"},
        "remembers": [],
        "remembers_opt_in": False,
        "onboarding_done": False,
        "what_helps": [],
        "skipped_checkins": 0,
        "checkin_voice_streak": 0,
        "jitai_not_now_until": None,
        "jitai_day_count": 0,
        "jitai_week_count": 0,
        "el_days": 12,
        "cl_days": 3,
        "shift_line": "Duty",
        "section_leader": False,
        "sunday_family_call": False,
        "night_within_24h": False,
        "consecutive_duty": 0,
        "sleep_nights_low": 0,
        "leave_days": 0,
        "consents": {
            "hr_derived": True,
            "self_report": False,
            "wearable": False,
            "ai_conversation": False,
            "voice": False,
        },
        "exception_understood": False,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    profile.update(_DEFAULTS.get(persona_id, {}))
    if profile.get("helpers") and not profile.get("what_helps"):
        profile["what_helps"] = list(profile["helpers"])
    return profile


def persona_id_for_token(token: str | None) -> str | None:
    if not token:
        return None
    for persona in PERSONAS.values():
        if persona.token == token:
            return persona.id
    return None


def get_profile(token: str | None) -> dict[str, Any]:
    persona_id = persona_id_for_token(token) or "arjun"
    if token not in PROFILES:
        PROFILES[token or persona_id] = _base(persona_id)
    stored = PROFILES[token or persona_id]
    stored["persona_id"] = persona_id
    return stored


def update_profile(token: str | None, patch: dict[str, Any]) -> dict[str, Any]:
    current = get_profile(token)
    for key, value in patch.items():
        if key in {"persona_id", "token"}:
            continue
        current[key] = value
    current["updated_at"] = datetime.now(UTC).isoformat()
    return current


def public_profile(token: str | None) -> dict[str, Any]:
    return deepcopy(get_profile(token))


def assert_absent_from_payload(payload: object) -> None:
    blob = str(payload).lower()
    forbidden = (
        "simple_mode",
        "helpers",
        "family_context",
        "voice_preference",
        "personal_goals",
        "what_helps",
        "remembers",
        "sunday_family_call",
    )
    for field in forbidden:
        if field in blob:
            raise AssertionError(f"personalisation field {field} leaked")
