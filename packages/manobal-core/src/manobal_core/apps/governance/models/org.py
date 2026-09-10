"""Units and pseudonymous subjects (SDD §5.2 SUBJECT, UNIT).

Read the :class:`Subject` field list and notice what is missing: no service
number, no name, no rank, no date of birth. This table is the analytics plane's
entire notion of a person, and it is deliberately unable to say who anyone is.
Turning ``subject_token`` into a person requires the Zone 3 identity resolver,
which lives in a different database, on a different network, behind a scope the
risk engine does not hold (SDD §3.2 rule 2).
"""

from __future__ import annotations

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from ..enums import DeviceTier, SubjectStatus


class Unit(models.Model):
    """A formation in the org hierarchy.

    Hierarchy matters for two opposed reasons at once: it decides which officer
    may see a case (SDD §6.2 scope predicate) and it decides whether an aggregate
    has enough people in it to be publishable at all (§4.6 k-anonymity).
    """

    code = models.CharField(max_length=32, primary_key=True)
    name = models.CharField(max_length=128)
    force_code = models.CharField(max_length=16, db_index=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )
    #: Denormalised depth, maintained on write. Officer scope checks run on
    #: every request and walking a recursive FK chain per check is the kind of
    #: cost that quietly turns into a per-request N+1.
    depth = models.PositiveSmallIntegerField(default=0)
    #: Materialised ancestor path ("CENTRAL/WESTERN/12BN") so a subtree query is
    #: one indexed prefix match.
    path = models.CharField(max_length=512, db_index=True, default="")
    posted_strength = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "unit"
        ordering = ("path",)

    def __str__(self) -> str:
        return f"{self.code} ({self.name})"

    def descendant_filter(self) -> models.Q:
        """Match this unit and everything under it."""
        return models.Q(code=self.code) | models.Q(path__startswith=f"{self.path}/")


class Subject(models.Model):
    """A pseudonymous participant.

    ``enrolled_at`` and :attr:`is_enrolled` are the sharp edge here. SDD §7.7
    forbids exposing participation status to the chain of command, because a
    commander who can see who declined can punish declining, and a consent that
    can be punished is not consent. The field exists because the system must know
    it; the API layer must never surface it to a commander, and the privacy gate
    suite tests exactly that.
    """

    subject_token = models.CharField(max_length=64, primary_key=True)
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="subjects")
    force_code = models.CharField(max_length=16, db_index=True)

    #: Banded rather than exact, because exact tenure plus unit plus rank is
    #: frequently a unique fingerprint in a small formation (SDD §7.2).
    rank_band = models.CharField(max_length=32)
    service_years_bucket = models.CharField(max_length=16)
    posting_type = models.CharField(max_length=32, blank=True, default="")

    status = models.CharField(
        max_length=16, choices=SubjectStatus.choices, default=SubjectStatus.ACTIVE
    )
    device_tier = models.CharField(max_length=1, choices=DeviceTier.choices, default=DeviceTier.A)
    language_code = models.CharField(max_length=8, default="en")

    enrolled_at = models.DateTimeField(null=True, blank=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    #: FR-7.4 clock. The purge beat reads this, not ``updated_at``.
    separated_at = models.DateTimeField(null=True, blank=True)

    #: Set once the trailing window holds enough observations for a personal
    #: baseline. Until then the person is scored at T0 regardless of their
    #: readings, because deviation from an unknown norm is not a signal (§4.2).
    baseline_established_on = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "subject"
        indexes = [
            models.Index(fields=["unit", "status"]),
            models.Index(fields=["force_code", "status"]),
        ]

    def __str__(self) -> str:
        return self.subject_token

    @property
    def is_enrolled(self) -> bool:
        return self.enrolled_at is not None and self.withdrawn_at is None

    @property
    def has_baseline(self) -> bool:
        return self.baseline_established_on is not None


class UnitAggregate(models.Model):
    """A k-anonymised unit-level rollup for the commander view (SDD §4.6).

    ``suppressed`` is a stored outcome rather than something computed at render
    time. That is intentional: a suppression is itself a governance event worth
    auditing and counting, and a commander repeatedly querying a small unit until
    it crosses *k* is a pattern the WDEC should be able to see.
    """

    id = models.BigAutoField(primary_key=True)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="aggregates")
    period_start = models.DateField()
    period_end = models.DateField()

    headcount = models.PositiveIntegerField()
    #: Rounded to a band before storage. An exact count in a small unit combined
    #: with a second query a week later can isolate an individual.
    elevated_band = models.CharField(max_length=16, blank=True, default="")
    dominant_category = models.CharField(max_length=64, blank=True, default="")
    trend_direction = models.CharField(max_length=16, blank=True, default="")

    suppressed = models.BooleanField(default=False)
    suppression_reason = models.CharField(max_length=64, blank=True, default="")
    k_threshold = models.PositiveSmallIntegerField(
        default=15, validators=[MinValueValidator(1), MaxValueValidator(1000)]
    )
    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "unit_aggregate"
        constraints = [
            models.UniqueConstraint(
                fields=["unit", "period_start", "period_end"], name="uniq_unit_period"
            ),
            models.CheckConstraint(
                condition=models.Q(period_end__gte=models.F("period_start")),
                name="aggregate_period_ordered",
            ),
        ]
        indexes = [models.Index(fields=["unit", "-period_end"])]
