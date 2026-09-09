"""Persisted risk-engine output and personal baselines (SDD §5.2, §4.2-§4.5).

The single most important line in this module is the one that is not here: there
is no ``wsi`` column, and no ``deviation`` column. FR-3.7 requires that the
numeric Welfare Signal Index never leaves the risk engine, and the cheapest way
to keep a number out of an API response is to never write it down. What persists
is the tier, the *names* of the contributing categories, and enough provenance —
which ruleset, which inputs — to reproduce the number on demand inside the
engine if an assessment is ever contested.

The privacy gate suite asserts this by introspecting the model's fields, so
adding a numeric score here fails the build rather than quietly shipping.
"""

from __future__ import annotations

from typing import Any

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from ..enums import Tier


class BaselineRecord(models.Model):
    """A person's own normal for one indicator (SDD §4.2).

    Median and MAD rather than mean and standard deviation, because a single
    sleepless night before a court appearance should not permanently move
    someone's notion of normal. Both are stored per subject per indicator: the
    comparison is always against the person themselves and never against a unit
    or a cohort, which is what stops the system penalising anyone for being
    different from their peers.
    """

    id = models.BigAutoField(primary_key=True)
    subject_token = models.CharField(max_length=64, db_index=True)
    indicator_code = models.CharField(max_length=64)

    median = models.FloatField()
    mad = models.FloatField()
    observation_count = models.PositiveIntegerField()
    window_start = models.DateField()
    window_end = models.DateField()

    #: False while the trailing window is too sparse to be trusted. The engine
    #: refuses to score an indicator in this state rather than guessing.
    is_established = models.BooleanField(default=False)
    computed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "baseline_record"
        constraints = [
            models.UniqueConstraint(
                fields=["subject_token", "indicator_code"], name="uniq_subject_indicator_baseline"
            ),
            models.CheckConstraint(
                condition=models.Q(mad__gte=0), name="baseline_mad_non_negative"
            ),
        ]
        indexes = [models.Index(fields=["subject_token", "indicator_code"])]

    def __str__(self) -> str:
        return f"{self.subject_token}/{self.indicator_code}"


class RiskAssessmentRecord(models.Model):
    """One scoring run's conclusion about one person at one moment.

    Immutable by policy (FR-3.9): a superseded assessment is a new row, never an
    edit. The reason is procedural rather than technical — if an officer acted on
    a T3 that was later recomputed as T1, the record of what they were shown when
    they acted has to survive, or the review of their decision is meaningless.
    """

    id = models.BigAutoField(primary_key=True)
    subject_token = models.CharField(max_length=64, db_index=True)
    assessed_at = models.DateTimeField(default=timezone.now, db_index=True)

    tier = models.CharField(max_length=2, choices=Tier.choices, db_index=True)
    #: Category *names* only — "sleep and recovery", "duty load". Never scores,
    #: never raw values, never ranked by magnitude, because a ranking leaks the
    #: ordering of the underlying numbers.
    contributing_categories = models.JSONField(default=list, blank=True)

    #: Provenance sufficient to re-derive the number inside the engine.
    ruleset_version = models.CharField(max_length=32)
    ruleset_digest = models.CharField(max_length=64)
    #: Which domains actually had consented, fresh data. Explains why two people
    #: with identical readings can land on different tiers.
    domains_present = models.JSONField(default=list, blank=True)
    #: Fraction of total domain weight that was available, 0-1. This is a
    #: property of participation, not of the person's welfare, and is kept to
    #: explain coverage renormalisation rather than to describe anyone.
    coverage = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])

    #: True when a safety-critical indicator forced T4 (§4.5). Kept separate from
    #: the tier because the acute path has different consent rules, a different
    #: legal basis and a different response SLA.
    acute_override = models.BooleanField(default=False)
    #: Tier before the corroboration gate and hysteresis, for explaining to a
    #: reviewer why a raw signal did not become a case.
    pre_gate_tier = models.CharField(max_length=2, choices=Tier.choices)

    superseded_by = models.OneToOneField(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="supersedes"
    )

    class Meta:
        db_table = "risk_assessment"
        ordering = ("-assessed_at",)
        indexes = [
            models.Index(fields=["subject_token", "-assessed_at"]),
            models.Index(fields=["tier", "-assessed_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.subject_token} {self.tier} @ {self.assessed_at:%Y-%m-%d}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Permit only the ``superseded_by`` back-link to be set after insert.

        Everything else about a written assessment is frozen. The link is the one
        exception because it is metadata about a *later* assessment rather than a
        revision of this one's conclusion.
        """
        if not self._state.adding:
            allowed = {"superseded_by", "superseded_by_id"}
            updating = set(kwargs.get("update_fields") or [])
            if not updating or not updating <= allowed:
                msg = "risk assessments are immutable; write a new assessment (FR-3.9)"
                raise ValueError(msg)
        super().save(*args, **kwargs)

    @property
    def is_officer_visible(self) -> bool:
        """T0 tells nobody; T1 tells only the individual (§4.5)."""
        return self.tier in {Tier.T2, Tier.T3, Tier.T4}


class RulesetVersion(models.Model):
    """The registry of scoring rulesets that have been in force (§4.7).

    Rules are data, not code: changing a threshold is a signed artefact and a
    dual-approval workflow, not a deploy. Recording the digest and both approvers
    is what lets a WDEC auditor answer "which rules produced this flag, and who
    agreed to them?" months later.
    """

    id = models.BigAutoField(primary_key=True)
    version = models.CharField(max_length=32, unique=True)
    digest = models.CharField(max_length=64)
    signature = models.TextField()
    signing_key_id = models.CharField(max_length=64)

    approved_by_clinical = models.CharField(max_length=128)
    approved_by_wdec = models.CharField(max_length=128)
    approved_at = models.DateTimeField()

    activated_at = models.DateTimeField(null=True, blank=True)
    retired_at = models.DateTimeField(null=True, blank=True)
    #: Result of replaying the new ruleset over historical data before
    #: activation. §4.7 requires the change's effect on flag rates and on
    #: subgroup parity to be known *before* it reaches anyone.
    shadow_report = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "ruleset_version"
        ordering = ("-approved_at",)

    def __str__(self) -> str:
        return f"ruleset {self.version}"
