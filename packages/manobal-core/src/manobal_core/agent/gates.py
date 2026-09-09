"""The five gates a turn must pass before a sentence reaches the person."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.utils import timezone

from manobal_core.alerting.acute import raise_acute
from manobal_core.apps.governance.enums import DataType
from manobal_core.apps.governance.models import ConsentEntry, Subject
from manobal_core.apps.psystore.models import AgentSession

CRISIS_PATTERNS = (
    r"\bkill myself\b",
    r"\bend my life\b",
    r"\bsuicid",
    r"\bwant to die\b",
    r"\bexplicit_sos\b",
)

_FORBIDDEN_IN_OUTPUT = (
    "T2",
    "T3",
    "T4",
    "tok_",
    "wsi",
    "phq-9",
    "phq9",
    "diagnosis",
    "officer-",
)

CRISIS_REPLY = (
    "If you are in immediate danger, please contact your unit welfare officer "
    "or local emergency services. Help is available, and asking for it is not "
    "a failure."
)


@dataclass(frozen=True, slots=True)
class GateDecision:
    allowed: bool
    reason: str
    session: AgentSession | None = None
    crisis: bool = False
    reply: str = ""


def gate_enabled() -> GateDecision:
    if not bool(settings.AGENT["ENABLED"]):
        return GateDecision(False, "disabled", reply="Structured forms are available instead.")
    return GateDecision(True, "enabled")


def gate_consent(subject_token: str) -> GateDecision:
    state = ConsentEntry.current_for(subject_token)
    if not state.get(DataType.SELF_REPORT) and not state.get(DataType.JOURNAL):
        return GateDecision(False, "not_consented", reply="This conversation needs your consent.")
    return GateDecision(True, "consented")


def gate_session(subject_token: str, session_id: str | None) -> GateDecision:
    limits = settings.RATE_LIMITS
    if not isinstance(limits, dict):
        raise TypeError("RATE_LIMITS must be a mapping")
    ttl = timedelta(minutes=_as_int(settings.AGENT["SESSION_TTL_MINUTES"]))
    now = timezone.now()
    session = None
    if session_id:
        session = AgentSession.objects.filter(pk=session_id, subject_token=subject_token).first()
        if session is not None and now - session.last_turn_at > ttl:
            session = None
    if session is None:
        session = AgentSession.objects.create(
            session_id=f"ags_{uuid4().hex}",
            subject_token=subject_token,
            started_at=now,
            last_turn_at=now,
        )
    day_start = now - timedelta(hours=24)
    day_turns = (
        AgentSession.objects.filter(subject_token=subject_token, last_turn_at__gte=day_start)
        .exclude(pk=session.session_id)
        .count()
        + session.turn_count
    )
    if session.turn_count >= _as_int(limits["agent_turns_per_session"]):
        return GateDecision(
            False, "session_budget", session=session, reply="Session limit reached."
        )
    if day_turns >= _as_int(limits["agent_turns_per_day"]):
        return GateDecision(False, "daily_budget", session=session, reply="Daily limit reached.")
    return GateDecision(True, "in_budget", session=session)


def gate_crisis(subject: Subject, message: str) -> GateDecision:
    text = message.lower()
    if any(re.search(pattern, text) for pattern in CRISIS_PATTERNS):
        raise_acute(
            subject,
            signal_code="crisis_language_detected",
            source="device_triage",
            self_initiated=False,
        )
        return GateDecision(False, "crisis", crisis=True, reply=CRISIS_REPLY)
    return GateDecision(True, "not_crisis")


def gate_output(reply: str) -> str:
    """Refuse anything that looks like a score, a token or a diagnosis."""
    lowered = reply.lower()
    if any(token.lower() in lowered for token in _FORBIDDEN_IN_OUTPUT):
        return (
            "I can listen and point you to support. I cannot discuss scores or "
            "clinical labels."
        )
    return reply


def _as_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return int(str(value))
    return value
