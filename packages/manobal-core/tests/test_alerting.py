"""Alerting is a lock-screen, not a case file (FR-6.1-FR-6.5, §4.8).

The body is a fixed sentence. If a test ever has to look inside an alert for a
tier, a token or a category name, the implementation has already failed: a
barracks lock screen is a public surface, and the only thing it may say is that
one item needs review.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.conf import settings
from django.utils import timezone

from manobal_core.alerting.bodies import lock_screen_body
from manobal_core.alerting.dispatch import acknowledge_case_alerts
from manobal_core.alerting.escalate import escalate_unacknowledged
from manobal_core.apps.governance.enums import AlertChannel, DeliveryStatus, Role, Tier
from manobal_core.apps.governance.models import AlertDispatch, OfficerProfile
from manobal_core.scoring.orchestrator import persist_assessment
from manobal_risk.types import Tier as EngineTier

from .scoring_helpers import engine_assessment

pytestmark = pytest.mark.django_db

PUSH = settings.ALERTING["PUSH_BODY"]
URGENT = settings.ALERTING["URGENT_PUSH_BODY"]


class TestLockScreen:
    def test_routine_and_urgent_bodies_are_the_published_sentences(self) -> None:
        assert lock_screen_body(Tier.T2) == PUSH
        assert lock_screen_body(Tier.T3) == PUSH
        assert lock_screen_body(Tier.T4) == URGENT

    def test_neither_body_carries_a_tier_token_or_category(self) -> None:
        for body in (PUSH, URGENT):
            assert "T2" not in body
            assert "T3" not in body
            assert "T4" not in body
            assert "tok_" not in body
            assert "wsi" not in body
            assert "sleep" not in body.lower()


class TestRoutingAndDedupe:
    def test_t2_goes_to_the_assigned_officer_as_a_digest(
        self, subject, officer
    ) -> None:
        del officer
        result = persist_assessment(
            engine_assessment(subject.subject_token, tier=EngineTier.T2),
            subject,
        )
        assert result.case is not None
        rows = list(AlertDispatch.objects.filter(case=result.case))
        assert len(rows) == 1
        assert rows[0].recipient_id == "officer-001"
        assert rows[0].channel == AlertChannel.DIGEST
        assert rows[0].body == PUSH
        assert rows[0].tier == Tier.T2

    def test_t3_is_an_immediate_push_to_one_officer(self, subject, officer) -> None:
        del officer
        result = persist_assessment(
            engine_assessment(subject.subject_token, tier=EngineTier.T3),
            subject,
        )
        rows = list(AlertDispatch.objects.filter(case=result.case))
        assert [row.channel for row in rows] == [AlertChannel.PUSH]
        assert rows[0].body == PUSH

    def test_a_persisting_tier_does_not_re_alert_in_the_same_week(
        self, subject, officer
    ) -> None:
        del officer
        persist_assessment(
            engine_assessment(subject.subject_token, tier=EngineTier.T2),
            subject,
        )
        later = timezone.now() + timedelta(hours=2)
        persist_assessment(
            engine_assessment(subject.subject_token, tier=EngineTier.T2, assessed_at=later),
            subject,
        )
        assert AlertDispatch.objects.count() == 1

    def test_t4_uses_push_and_sms_and_the_urgent_sentence(
        self, subject, officer
    ) -> None:
        del officer
        result = persist_assessment(
            engine_assessment(subject.subject_token, tier=EngineTier.T4, acute=True),
            subject,
        )
        channels = set(
            AlertDispatch.objects.filter(case=result.case).values_list("channel", flat=True)
        )
        assert AlertChannel.PUSH in channels
        assert AlertChannel.SMS in channels
        assert all(row.body == URGENT for row in AlertDispatch.objects.all())
        assert "T4" not in "".join(row.body for row in AlertDispatch.objects.all())

    def test_t4_notifies_a_medical_officer_individually(
        self, subject, officer, unit_tree
    ) -> None:
        del officer
        OfficerProfile.objects.create(
            actor_id="medical-001",
            role=Role.MEDICAL_OFFICER,
            unit=unit_tree["battalion"],
            force_code="CAPF",
            training_valid_until=timezone.localdate() + timedelta(days=180),
        )
        result = persist_assessment(
            engine_assessment(subject.subject_token, tier=EngineTier.T4, acute=True),
            subject,
        )
        recipients = set(
            AlertDispatch.objects.filter(case=result.case).values_list("recipient_id", flat=True)
        )
        assert "officer-001" in recipients
        assert "medical-001" in recipients
        assert AlertDispatch.objects.filter(recipient_id="medical-001").count() == 1


class TestAcknowledgementAndEscalation:
    def test_contacting_the_case_acknowledges_the_officer_s_alerts(
        self, subject, officer
    ) -> None:
        del officer
        result = persist_assessment(
            engine_assessment(subject.subject_token, tier=EngineTier.T3),
            subject,
        )
        assert result.case is not None
        acknowledge_case_alerts(result.case, actor_id="officer-001")
        row = AlertDispatch.objects.get()
        assert row.status == DeliveryStatus.ACKNOWLEDGED
        assert row.acknowledged_at is not None

    def test_an_unacked_t4_escalates_to_the_next_officer_after_the_sla(
        self, subject, officer, unit_tree
    ) -> None:
        del officer
        OfficerProfile.objects.create(
            actor_id="officer-002",
            role=Role.WELFARE_OFFICER,
            unit=unit_tree["force"],
            force_code="CAPF",
            training_valid_until=timezone.localdate() + timedelta(days=180),
        )
        result = persist_assessment(
            engine_assessment(subject.subject_token, tier=EngineTier.T4, acute=True),
            subject,
        )
        AlertDispatch.objects.filter(case=result.case, recipient_id="officer-001").update(
            sent_at=timezone.now() - timedelta(minutes=20),
            status=DeliveryStatus.SENT,
        )
        created = escalate_unacknowledged(now=timezone.now())
        assert created
        follow = AlertDispatch.objects.get(recipient_id="officer-002")
        assert follow.channel == AlertChannel.VOICE
        assert follow.body == URGENT
        assert follow.escalated_to_id is None
        original = AlertDispatch.objects.filter(
            recipient_id="officer-001", channel=AlertChannel.PUSH
        ).get()
        assert original.escalated_to_id == follow.pk
