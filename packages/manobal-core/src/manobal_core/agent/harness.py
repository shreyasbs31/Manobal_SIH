"""Run one agent turn through the five gates, in order."""

from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from manobal_core.agent.backends import InferenceBackend, backend_for_settings
from manobal_core.agent.gates import (
    gate_consent,
    gate_crisis,
    gate_enabled,
    gate_output,
    gate_session,
)
from manobal_core.apps.governance.models import Subject
from manobal_core.apps.psystore.models import AgentSession


@dataclass(frozen=True, slots=True)
class AgentTurn:
    session_id: str
    reply: str
    crisis: bool
    accepted: bool


def run_turn(
    subject: Subject,
    message: str,
    *,
    session_id: str | None = None,
    backend: InferenceBackend | None = None,
) -> AgentTurn:
    """Apply gates 1-5. Crisis never reaches the model."""
    enabled = gate_enabled()
    if not enabled.allowed:
        return AgentTurn(
            session_id=session_id or "", reply=enabled.reply, crisis=False, accepted=False
        )

    consent = gate_consent(subject.subject_token)
    if not consent.allowed:
        return AgentTurn(
            session_id=session_id or "", reply=consent.reply, crisis=False, accepted=False
        )

    budget = gate_session(subject.subject_token, session_id)
    if budget.session is None or not budget.allowed:
        return AgentTurn(
            session_id=budget.session.session_id if budget.session else "",
            reply=budget.reply,
            crisis=False,
            accepted=False,
        )

    crisis = gate_crisis(subject, message)
    if crisis.crisis:
        _touch(budget.session)
        return AgentTurn(
            session_id=budget.session.session_id,
            reply=crisis.reply,
            crisis=True,
            accepted=True,
        )

    raw = (backend or backend_for_settings()).complete(message)
    reply = gate_output(raw)
    _touch(budget.session)
    return AgentTurn(
        session_id=budget.session.session_id,
        reply=reply,
        crisis=False,
        accepted=True,
    )


def _touch(session: AgentSession) -> None:
    session.turn_count += 1
    session.last_turn_at = timezone.now()
    session.save(update_fields=["turn_count", "last_turn_at"])
