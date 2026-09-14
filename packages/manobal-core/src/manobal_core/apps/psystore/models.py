"""Psychometric and self-report store — D3, D5 and journalling (SDD §5.1).

The most sensitive store in the analytics plane, and the one where the
distinction between a *feature* and a *disclosure* is sharpest. An instrument
score is a feature and may be scored. What someone wrote in their journal is a
disclosure, is never scored, and is never shown to an officer — the risk engine
has no read path to :class:`JournalEntry` at all, enforced by the database grant
rather than by convention.
"""

from __future__ import annotations

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class InstrumentResponse(models.Model):
    """A completed validated instrument (D3).

    Item-level answers are deliberately not stored. Retaining every response to
    every question would make this a clinical record, subject to a different
    legal regime and a far more attractive target; the total and subscales are
    what the engine needs and are all that is kept.

    ``is_acute_flagged`` exists because some instruments contain a
    safety-critical item — PHQ-9 item 9 is the canonical case. That item's
    presence triggers the acute path immediately and out of band, without waiting
    for the nightly scoring run.
    """

    id = models.BigAutoField(primary_key=True)
    subject_token = models.CharField(max_length=64, db_index=True)
    instrument_code = models.CharField(max_length=32, db_index=True)
    instrument_version = models.CharField(max_length=16)
    language_code = models.CharField(max_length=8, default="en")

    completed_at = models.DateTimeField(default=timezone.now, db_index=True)
    total_score = models.FloatField()
    subscales = models.JSONField(default=dict, blank=True)

    #: Seconds to complete. Implausibly fast completion suggests straight-lining,
    #: which makes the score unreliable rather than reassuring — a low score
    #: completed in nine seconds is not evidence of wellbeing.
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    straight_lined = models.BooleanField(default=False)

    is_acute_flagged = models.BooleanField(default=False, db_index=True)
    acute_item_code = models.CharField(max_length=32, blank=True, default="")

    class Meta:
        db_table = "instrument_response"
        ordering = ("-completed_at",)
        indexes = [
            models.Index(fields=["subject_token", "instrument_code", "-completed_at"]),
            models.Index(fields=["is_acute_flagged", "-completed_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.subject_token} {self.instrument_code} @ {self.completed_at:%Y-%m-%d}"


class CheckinResponse(models.Model):
    """A short daily self-report (D5).

    Kept to a handful of ordinal items answerable in under a minute. Compliance
    with a daily instrument collapses if it takes longer, and a check-in nobody
    completes produces a coverage gap rather than a signal.
    """

    id = models.BigAutoField(primary_key=True)
    subject_token = models.CharField(max_length=64, db_index=True)
    observed_on = models.DateField(db_index=True)
    submitted_at = models.DateTimeField(default=timezone.now)

    _SCALE = (MinValueValidator(1), MaxValueValidator(5))
    mood = models.PositiveSmallIntegerField(null=True, blank=True, validators=list(_SCALE))
    sleep_quality = models.PositiveSmallIntegerField(null=True, blank=True, validators=list(_SCALE))
    stress = models.PositiveSmallIntegerField(null=True, blank=True, validators=list(_SCALE))
    #: SDD D5 names mood, fatigue and sleep. ``stress`` remains as the older
    #: label; when ``fatigue`` is present the engine reads it instead.
    fatigue = models.PositiveSmallIntegerField(null=True, blank=True, validators=list(_SCALE))
    #: Perceived social connection. Isolation is among the more actionable
    #: contributors, and one an officer can respond to without clinical training.
    connection = models.PositiveSmallIntegerField(null=True, blank=True, validators=list(_SCALE))

    #: Only ever a coarse category chosen from a fixed list, never free text.
    #: Free text here would become an unreviewed clinical note in a store an
    #: officer can reach.
    concern_tag = models.CharField(max_length=32, blank=True, default="")

    class Meta:
        db_table = "checkin_response"
        constraints = [
            models.UniqueConstraint(
                fields=["subject_token", "observed_on"], name="uniq_checkin_day"
            )
        ]
        indexes = [models.Index(fields=["subject_token", "-observed_on"])]

    def __str__(self) -> str:
        return f"{self.subject_token} checkin {self.observed_on}"


class JournalEntry(models.Model):
    """A private reflective entry (FR-1.2 ``journal``).

    Read the field list carefully: there is no derived score, no sentiment, no
    extracted topic. This content exists for the individual and is not an input
    to anything. The risk engine's database role holds no privilege on this
    table, so "the journal is not scored" is a fact about the deployment rather
    than a promise in a document.

    ``crisis_referred_at`` is the one exception and is narrowly drawn: on-device
    crisis triage may prompt the person with help resources, and if they accept,
    that acceptance is recorded. The entry text still does not move.
    """

    id = models.BigAutoField(primary_key=True)
    subject_token = models.CharField(max_length=64, db_index=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    #: Encrypted at rest with a per-subject key. Erasure destroys the key as well
    #: as the row, so a restored backup cannot resurrect readable text.
    ciphertext = models.BinaryField()
    key_id = models.CharField(max_length=64)
    nonce = models.BinaryField()

    crisis_referred_at = models.DateTimeField(null=True, blank=True)
    #: UC-19. A session the person chose not to keep expires and is swept.
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "journal_entry"
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["subject_token", "-created_at"])]

    def __str__(self) -> str:
        return f"journal {self.pk} for {self.subject_token}"


class AcuteSignal(models.Model):
    """A safety-critical indicator, on its own out-of-band path (§4.5 T4).

    Separate from :class:`InstrumentResponse` because the acute path must not
    queue behind nightly scoring, and because it operates under a different legal
    basis: §7(c)/(d) vital interest rather than consent. A person who has
    withdrawn consent for scoring can still trigger this path, and the SDD is
    explicit that they must — which is precisely why every instance is recorded
    here for WDEC review rather than handled silently.
    """

    id = models.BigAutoField(primary_key=True)
    subject_token = models.CharField(max_length=64, db_index=True)
    detected_at = models.DateTimeField(default=timezone.now, db_index=True)

    signal_code = models.CharField(max_length=48)
    source = models.CharField(
        max_length=24,
        choices=[
            ("instrument", "Instrument item"),
            ("device_triage", "On-device crisis triage"),
            ("self_report", "Direct request for help"),
            ("officer", "Officer-raised concern"),
        ],
    )
    #: Set when the person asked for help themselves. Consent is unambiguous in
    #: that case, and the response should not be wrapped in override paperwork.
    self_initiated = models.BooleanField(default=False)

    dispatched_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    wdec_reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "acute_signal"
        ordering = ("-detected_at",)
        indexes = [models.Index(fields=["acknowledged_at", "detected_at"])]

    def __str__(self) -> str:
        return f"acute {self.signal_code} for {self.subject_token}"


class AgentSession(models.Model):
    """A time-boxed conversation with the on-device/server agent (§7.8).

    The transcript is not stored. Turns are counted so the rate limit is a
    fact about the session, not a guess, and so a crash mid-conversation does
    not reset the budget.
    """

    session_id = models.CharField(max_length=64, primary_key=True)
    subject_token = models.CharField(max_length=64, db_index=True)
    started_at = models.DateTimeField(default=timezone.now)
    last_turn_at = models.DateTimeField(default=timezone.now)
    turn_count = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "agent_session"
        indexes = [models.Index(fields=["subject_token", "-last_turn_at"])]
