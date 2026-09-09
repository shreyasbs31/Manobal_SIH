"""Physiological signal store — D4 (SDD §5.1).

Daily-grain wearable features, not raw PPG. The comparison the engine makes is
against a ninety-day personal baseline; a sample-per-second table would make
that query a production incident. ``observed_at`` is still a timestamp so a
Timescale hypertable can be attached later without rewriting the grain.

There is no service number here. The only handle is the token.
"""

from __future__ import annotations

from django.db import models
from django.utils import timezone


class PhysiologicalObservation(models.Model):
    """One daily metric for one person (resting HR, HRV, sleep, steps)."""

    id = models.BigAutoField(primary_key=True)
    subject_token = models.CharField(max_length=64, db_index=True)
    observed_on = models.DateField(db_index=True)
    observed_at = models.DateTimeField(default=timezone.now)
    metric_code = models.CharField(max_length=64, db_index=True)
    value = models.FloatField()
    source = models.CharField(max_length=32, default="wearable")

    class Meta:
        db_table = "physiological_observation"
        constraints = [
            models.UniqueConstraint(
                fields=["subject_token", "observed_on", "metric_code"],
                name="uniq_bio_metric_day",
            )
        ]
        indexes = [models.Index(fields=["subject_token", "-observed_on"])]

    def __str__(self) -> str:
        return f"{self.subject_token} {self.metric_code} {self.observed_on}"
