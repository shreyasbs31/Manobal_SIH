"""Sweep raw observations older than the statutory retention window (FR-7.3)."""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from manobal_core.apps.biostore.models import PhysiologicalObservation
from manobal_core.apps.psystore.models import CheckinResponse, InstrumentResponse, JournalEntry
from manobal_core.apps.voicestore.models import VoiceObservation


def purge_raw_observations(*, now=None) -> int:
    """Delete raw rows older than ``PRIVACY.RAW_RETENTION_DAYS``. Aggregates stay."""
    privacy = settings.PRIVACY
    days = int(privacy["RAW_RETENTION_DAYS"])
    moment = now or timezone.now()
    cutoff_dt = moment - timedelta(days=days)
    cutoff_date = cutoff_dt.date()
    deleted = 0
    deleted += CheckinResponse.objects.filter(observed_on__lt=cutoff_date).delete()[0]
    deleted += InstrumentResponse.objects.filter(completed_at__lt=cutoff_dt).delete()[0]
    deleted += PhysiologicalObservation.objects.filter(observed_on__lt=cutoff_date).delete()[0]
    deleted += VoiceObservation.objects.filter(captured_on__lt=cutoff_date).delete()[0]
    expired = JournalEntry.objects.filter(expires_at__isnull=False, expires_at__lte=moment)
    deleted += expired.delete()[0]
    return deleted
