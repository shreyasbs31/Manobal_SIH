"""Hysteresis is live: the gated tier is persisted and consecutive nights count."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from manobal_core.apps.governance.enums import Tier
from manobal_core.apps.governance.models import Subject
from manobal_core.scoring.features import assemble_history
from manobal_core.scoring.orchestrator import persist_assessment
from manobal_risk.types import Tier as EngineTier

from .scoring_helpers import engine_assessment

pytestmark = pytest.mark.django_db(databases=["default", "org", "psy", "bio", "voice"])


def test_pre_gate_tier_is_the_gated_tier_not_the_held_tier(subject: Subject, officer) -> None:
    del officer
    result = persist_assessment(
        engine_assessment(
            subject.subject_token,
            tier=EngineTier.T3,
            tier_before_hysteresis=EngineTier.T1,
        ),
        subject,
    )
    assert result.assessment.tier == Tier.T3
    assert result.assessment.pre_gate_tier == Tier.T1


def test_consecutive_lower_cycles_count_trailing_gated_nights(subject: Subject, officer) -> None:
    del officer
    persist_assessment(
        engine_assessment(subject.subject_token, tier=EngineTier.T3),
        subject,
    )
    later = timezone.now() + timedelta(hours=1)
    persist_assessment(
        engine_assessment(
            subject.subject_token,
            tier=EngineTier.T3,
            tier_before_hysteresis=EngineTier.T1,
            assessed_at=later,
        ),
        subject,
    )
    history = assemble_history(subject.subject_token)
    assert history.previous_tier is EngineTier.T3
    assert history.consecutive_lower_cycles == 1

    persist_assessment(
        engine_assessment(
            subject.subject_token,
            tier=EngineTier.T3,
            tier_before_hysteresis=EngineTier.T1,
            assessed_at=later + timedelta(hours=1),
        ),
        subject,
    )
    history = assemble_history(subject.subject_token)
    assert history.consecutive_lower_cycles == 2
