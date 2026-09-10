"""Synthetic observations land in the five stores without identifiers."""

from __future__ import annotations

from datetime import date

import pytest

from manobal_core.apps.biostore.models import PhysiologicalObservation
from manobal_core.apps.governance.models import Subject, Unit
from manobal_core.apps.orgstore.models import DutyObservation
from manobal_core.apps.psystore.models import CheckinResponse, InstrumentResponse
from manobal_core.apps.voicestore.models import VoiceObservation
from manobal_core.synth.load import load_observation_rows
from manobal_synth.records import ObservationRow

pytestmark = pytest.mark.django_db(databases=["default", "org", "psy", "bio", "voice"])


def test_observation_rows_load_without_identifiers(
    unit_tree: dict[str, Unit], consent_text
) -> None:
    token = "tok_synth_0001"
    day = date(2026, 9, 1)
    rows = [
        ObservationRow(token, "duty_hours_7d", day, 42.0),
        ObservationRow(token, "phq9_total", day, 6.0),
        ObservationRow(token, "ema_mood", day, 3.0),
        ObservationRow(token, "resting_hr_nightly", day, 58.0),
        ObservationRow(token, "voice_f0_variability", day, 1.1),
    ]
    receipt = load_observation_rows(rows, unit=unit_tree["company"], consent_text=consent_text)
    assert receipt.subjects == 1
    assert receipt.observations == 5
    subject = Subject.objects.get(pk=token)
    assert subject.unit_id == unit_tree["company"].code
    assert DutyObservation.objects.get(subject_token=token).duty_hours_7d == 42.0
    instrument = InstrumentResponse.objects.get(subject_token=token)
    assert instrument.instrument_code == "phq9"
    assert instrument.total_score == 6.0
    assert instrument.subscales == {}
    assert CheckinResponse.objects.get(subject_token=token).mood == 3
    assert PhysiologicalObservation.objects.get(subject_token=token).value == 58.0
    assert VoiceObservation.objects.get(subject_token=token).features["voice_f0_variability"] == 1.1
    dumped = " ".join(
        str(row.__dict__)
        for row in (
            subject,
            DutyObservation.objects.get(),
            instrument,
            CheckinResponse.objects.get(),
            PhysiologicalObservation.objects.get(),
            VoiceObservation.objects.get(),
        )
    )
    assert "CRPF" not in dumped
    assert "service_no" not in dumped
    assert "full_name" not in dumped
