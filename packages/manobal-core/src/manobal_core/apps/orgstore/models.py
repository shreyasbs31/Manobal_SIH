"""Organisational signal store — D1 duty load and D2 leave/rest (SDD §5.1).

These are derived features, not source records. The distinction matters: MANOBAL
does not become the system of record for anyone's leave, and it deliberately
cannot answer "did this person take Tuesday off?". It stores the shape of a
person's duty rhythm — hours worked in a trailing window, nights disrupted, leave
deferred — which is what a personal baseline is computed from.

There is no ``service_number`` column here, and there cannot be one: this store
sits in the analytics plane, where the only handle on a person is their token.
"""

from __future__ import annotations

from django.db import models


class DutyObservation(models.Model):
    """One day's duty-load features for one person (D1).

    A daily grain rather than a per-shift grain because the baseline compares
    like with like across a 90-day window, and shift boundaries vary too much
    between forces and postings to be a stable unit of comparison.
    """

    id = models.BigAutoField(primary_key=True)
    subject_token = models.CharField(max_length=64, db_index=True)
    observed_on = models.DateField(db_index=True)

    duty_hours = models.FloatField(null=True, blank=True)
    #: Rolling seven-day total, precomputed. Consecutive load is the signal;
    #: one long day is not, and recomputing a window per scoring run over
    #: hundreds of thousands of rows is the kind of query that turns a nightly
    #: batch into a four-hour job.
    duty_hours_7d = models.FloatField(null=True, blank=True)
    night_duty = models.BooleanField(default=False)
    consecutive_duty_days = models.PositiveSmallIntegerField(default=0)
    high_alert_posting = models.BooleanField(default=False)
    #: Distinct locations in the trailing window. Frequent relocation
    #: disrupts routine and social contact independently of hours worked.
    location_changes_30d = models.PositiveSmallIntegerField(default=0)

    source_batch_id = models.BigIntegerField(null=True, blank=True)
    ingested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "duty_observation"
        constraints = [
            models.UniqueConstraint(
                fields=["subject_token", "observed_on"], name="uniq_duty_observation_day"
            )
        ]
        indexes = [models.Index(fields=["subject_token", "-observed_on"])]

    def __str__(self) -> str:
        return f"{self.subject_token} duty {self.observed_on}"


class LeaveObservation(models.Model):
    """Leave and rest-opportunity features for one person on one day (D2).

    ``leave_denied_count`` and ``leave_deferred_days`` carry most of the weight.
    Leave *taken* says relatively little; leave repeatedly applied for and not
    granted, especially around a family event, is one of the more legible
    organisational contributors to strain — and unlike most signals here, it
    points at something a commander can actually fix.
    """

    id = models.BigAutoField(primary_key=True)
    subject_token = models.CharField(max_length=64, db_index=True)
    observed_on = models.DateField(db_index=True)

    days_since_last_leave = models.PositiveSmallIntegerField(null=True, blank=True)
    leave_denied_count_90d = models.PositiveSmallIntegerField(default=0)
    leave_deferred_days = models.PositiveSmallIntegerField(default=0)
    pending_leave_application = models.BooleanField(default=False)
    #: Distance from home station, banded. Bands rather than kilometres because
    #: an exact distance plus a unit is close to a home address.
    home_distance_band = models.CharField(max_length=16, blank=True, default="")

    source_batch_id = models.BigIntegerField(null=True, blank=True)
    ingested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_observation"
        constraints = [
            models.UniqueConstraint(
                fields=["subject_token", "observed_on"], name="uniq_leave_observation_day"
            )
        ]
        indexes = [models.Index(fields=["subject_token", "-observed_on"])]

    def __str__(self) -> str:
        return f"{self.subject_token} leave {self.observed_on}"


class EngagementObservation(models.Model):
    """Interaction rhythm with the platform itself (D7).

    The weakest domain in the ruleset, and weighted accordingly. Disengagement
    is genuinely ambiguous — withdrawal can mean distress, or a dead battery, or
    a week of field exercise. It corroborates other domains; it should never
    carry a tier on its own, which the corroboration gate guarantees structurally.

    A person who has withdrawn consent for engagement data produces no rows here
    at all, and the engine treats the domain as absent rather than as silent.
    """

    id = models.BigAutoField(primary_key=True)
    subject_token = models.CharField(max_length=64, db_index=True)
    observed_on = models.DateField(db_index=True)

    checkin_completed = models.BooleanField(default=False)
    app_sessions = models.PositiveSmallIntegerField(default=0)
    #: Median seconds to complete a check-in. Slower completion over time can
    #: indicate reduced concentration, but it is a soft signal at best.
    median_response_seconds = models.FloatField(null=True, blank=True)
    days_since_last_interaction = models.PositiveSmallIntegerField(null=True, blank=True)
    resource_views = models.PositiveSmallIntegerField(default=0)

    ingested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "engagement_observation"
        constraints = [
            models.UniqueConstraint(
                fields=["subject_token", "observed_on"], name="uniq_engagement_observation_day"
            )
        ]
        indexes = [models.Index(fields=["subject_token", "-observed_on"])]

    def __str__(self) -> str:
        return f"{self.subject_token} engagement {self.observed_on}"
