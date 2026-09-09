"""The agent never sees a crisis, and never emits a score (SDD §7.8)."""

from __future__ import annotations

import pytest

from manobal_core.agent.harness import run_turn
from manobal_core.apps.governance.enums import DataType
from manobal_core.apps.governance.models import (
    ConsentEntry,
    ConsentTextVersion,
    Subject,
)
from manobal_core.apps.psystore.models import AcuteSignal

pytestmark = pytest.mark.django_db(databases=["default", "psy"])


def _consent(subject: Subject, text: ConsentTextVersion) -> None:
    ConsentEntry.objects.create(
        subject_token=subject.subject_token,
        data_type=DataType.SELF_REPORT,
        granted=True,
        consent_text=text,
    )


class TestAgentHarness:
    def test_a_normal_turn_returns_a_non_clinical_reply(
        self, subject: Subject, consent_text: ConsentTextVersion
    ) -> None:
        _consent(subject, consent_text)
        turn = run_turn(subject, "I have not been sleeping well")
        assert turn.accepted is True
        assert turn.crisis is False
        assert "T2" not in turn.reply
        assert "wsi" not in turn.reply.lower()
        assert turn.session_id.startswith("ags_")

    def test_crisis_language_pages_t4_and_never_reaches_the_model(
        self, subject: Subject, officer, consent_text: ConsentTextVersion
    ) -> None:
        del officer
        _consent(subject, consent_text)

        class Forbidden:
            def complete(self, message: str) -> str:
                raise AssertionError(f"model must not see: {message}")

        turn = run_turn(subject, "I want to die", backend=Forbidden())
        assert turn.crisis is True
        assert "emergency" in turn.reply.lower()
        assert AcuteSignal.objects.filter(
            subject_token=subject.subject_token, signal_code="crisis_language_detected"
        ).exists()

    def test_without_consent_the_agent_refuses(
        self, subject: Subject
    ) -> None:
        turn = run_turn(subject, "hello")
        assert turn.accepted is False
        assert "consent" in turn.reply.lower()
