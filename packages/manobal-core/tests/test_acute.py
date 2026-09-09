"""The T4 path overrides consent, corroboration and the nightly window (SDD §4.7).

A person who has withdrawn scoring can still ask for help. The response is a
case, a vital-interest grant, and a page — never a counselling message, and
never the officer's name on the caller's screen.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from manobal_core.alerting.acute import raise_acute
from manobal_core.apps.authz.principal import Principal
from manobal_core.apps.governance.enums import (
    AlertChannel,
    DataType,
    GrantScope,
    LegalBasis,
    Role,
    Tier,
)
from manobal_core.apps.governance.models import (
    AccessGrant,
    AlertDispatch,
    Case,
    ConsentEntry,
    ConsentTextVersion,
    OfficerProfile,
    Subject,
)
from manobal_core.apps.psystore.models import AcuteSignal

pytestmark = pytest.mark.django_db(databases=["default", "psy"])


def _personnel(subject: Subject) -> Principal:
    return Principal(
        actor_id=subject.subject_token,
        role=Role.PERSONNEL,
        force_code=subject.force_code,
        unit_code=subject.unit_id,
        subject_token=subject.subject_token,
    )


class TestRaiseAcute:
    def test_sos_opens_a_t4_case_and_pages_the_officer(
        self, subject: Subject, officer: OfficerProfile
    ) -> None:
        result = raise_acute(
            subject,
            signal_code="explicit_sos",
            source="self_report",
            self_initiated=True,
        )
        assert result.case is not None
        assert result.case.assigned_officer_id == officer.actor_id
        assert result.case.tier_at_open == Tier.T4
        assert result.signal.dispatched_at is not None
        assert result.signal.self_initiated is True
        assert AcuteSignal.objects.filter(subject_token=subject.subject_token).count() == 1

        channels = set(
            AlertDispatch.objects.filter(case=result.case).values_list("channel", flat=True)
        )
        assert AlertChannel.PUSH in channels
        assert AlertChannel.SMS in channels

    def test_t4_authorises_identity_resolution_under_vital_interest(
        self, subject: Subject, officer: OfficerProfile
    ) -> None:
        result = raise_acute(
            subject, signal_code="explicit_sos", source="self_report", self_initiated=True
        )
        assert result.case is not None
        grant = AccessGrant.objects.get(
            case=result.case,
            grantee_id=officer.actor_id,
            scope=GrantScope.IDENTITY,
        )
        assert grant.legal_basis == LegalBasis.VITAL_INTEREST
        assert grant.subject_consented is False
        assert grant.is_live

    def test_withdrawal_does_not_block_an_sos(
        self,
        subject: Subject,
        officer: OfficerProfile,
        consent_text: ConsentTextVersion,
    ) -> None:
        del officer
        ConsentEntry.objects.create(
            subject_token=subject.subject_token,
            data_type=DataType.BIOMETRIC,
            granted=False,
            consent_text=consent_text,
        )
        result = raise_acute(
            subject, signal_code="explicit_sos", source="self_report", self_initiated=True
        )
        assert result.case is not None
        assert result.case.tier_at_open == Tier.T4
        assert Case.objects.filter(subject_token=subject.subject_token).count() == 1


class TestSosHttp:
    def test_personnel_receive_acceptance_and_never_an_officer_identity(
        self, subject: Subject, officer: OfficerProfile
    ) -> None:
        del officer
        client = APIClient()
        client.force_authenticate(user=_personnel(subject))
        response = client.post("/v1/me/sos", {}, format="json")
        assert response.status_code == 202
        assert response.json() == {"accepted": True}
        body = response.content.decode()
        assert "officer-001" not in body
        assert "officer" not in body.lower()
        assert subject.subject_token not in body
        opened = Case.objects.filter(
            subject_token=subject.subject_token, tier_at_open=Tier.T4
        )
        assert opened.exists()

    def test_the_wrong_role_cannot_raise_an_sos(
        self, subject: Subject, officer_principal: Principal
    ) -> None:
        del subject
        client = APIClient()
        client.force_authenticate(user=officer_principal)
        response = client.post("/v1/me/sos", {}, format="json")
        assert response.status_code == 403

    def test_an_unacked_t4_from_sos_escalates_after_the_sla(
        self, subject: Subject, officer: OfficerProfile, unit_tree: dict
    ) -> None:
        del officer
        OfficerProfile.objects.create(
            actor_id="officer-002",
            role=Role.WELFARE_OFFICER,
            unit=unit_tree["force"],
            force_code="CAPF",
            training_valid_until=timezone.localdate() + timedelta(days=180),
        )
        result = raise_acute(
            subject, signal_code="explicit_sos", source="self_report", self_initiated=True
        )
        AlertDispatch.objects.filter(case=result.case, recipient_id="officer-001").update(
            sent_at=timezone.now() - timedelta(minutes=20),
            status="sent",
        )
        from manobal_core.alerting.escalate import escalate_unacknowledged

        created = escalate_unacknowledged(now=timezone.now())
        assert created
        follow = AlertDispatch.objects.get(recipient_id="officer-002")
        assert follow.channel == AlertChannel.VOICE
        assert "T4" not in follow.body
        assert "tok_" not in follow.body
