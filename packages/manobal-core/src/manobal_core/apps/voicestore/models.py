"""Vocal-acoustic feature store — D6 (SDD §5.1, §7.4 V13).

This table holds derived scalars and an optional embedding. It does not hold
audio, and it does not hold a transcript. Speaker-identifying raw features are
out of the retained set; what remains is the six ruleset indicators plus a
vector used only for on-device quality checks and Phase-1 similarity work.

The embedding is JSON on purpose: tests and a cluster without pgvector still
run. Production attaches an HNSW index when the ``vector`` extension is present.
"""

from __future__ import annotations

from django.db import models
from django.utils import timezone


class VoiceObservation(models.Model):
    """One voice check-in: scalar features, never the recording."""

    id = models.BigAutoField(primary_key=True)
    subject_token = models.CharField(max_length=64, db_index=True)
    captured_on = models.DateField(db_index=True)
    captured_at = models.DateTimeField(default=timezone.now)
    #: Keys are ruleset indicator codes (``voice_f0_variability``, …).
    features = models.JSONField(default=dict, blank=True)
    #: Fixed-length eGeMAPS vector. No audio. No transcript.
    embedding = models.JSONField(default=list, blank=True)
    language_code = models.CharField(max_length=8, default="en")

    class Meta:
        db_table = "voice_observation"
        constraints = [
            models.UniqueConstraint(
                fields=["subject_token", "captured_on"],
                name="uniq_voice_checkin_day",
            )
        ]
        indexes = [models.Index(fields=["subject_token", "-captured_on"])]

    def __str__(self) -> str:
        return f"{self.subject_token} voice {self.captured_on}"
