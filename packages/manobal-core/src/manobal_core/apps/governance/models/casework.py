"""Officer casework, time-boxed access and alert dispatch (SDD §5.2, §4.5, §6.2).

The governing idea across this module is that access is an event with an expiry,
not a property of a role. An officer does not "have access to their unit"; they
hold a grant, for one person, for one scope, until a stated time, recorded in a
row someone can later read back. Broad standing access is what turns a welfare
system into a surveillance system, and the schema is arranged so that the broad
version is the awkward one to write.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db import models
from django.utils import timezone

from ..enums import (
    AlertChannel,
    CaseStatus,
    DeliveryStatus,
    GrantScope,
    LegalBasis,
    Role,
    Tier,
)

#: FR-2.7 caps an access grant at fourteen days. Renewal is deliberate friction:
#: an officer who still needs access must say so again, which creates a second
#: auditable decision rather than an access that quietly persists for a year.
MAX_GRANT_DAYS = 14


class OfficerProfile(models.Model):
    """A welfare officer's authorisation envelope.

    ``training_valid_until`` gates casework rather than merely recording a fact.
    FR-4.6 requires an officer to be currently certified to receive a flag, so an
    expired certification removes them from assignment: an untrained officer
    receiving a T3 is a worse outcome than a slightly slower response.
    """

    actor_id = models.CharField(max_length=128, primary_key=True)
    role = models.CharField(max_length=32, choices=Role.choices)
    unit = models.ForeignKey("governance.Unit", on_delete=models.PROTECT, related_name="officers")
    force_code = models.CharField(max_length=16, db_index=True)

    training_valid_until = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    #: Caseload ceiling. Beyond it, assignment moves to the next officer in the
    #: escalation ladder rather than deepening a queue nobody can work through.
    max_open_cases = models.PositiveSmallIntegerField(default=25)
    #: Duty phone for T4 SMS. Never a subject's number. Empty until the officer
    #: registers it; the transport then no-ops rather than guessing.
    duty_phone_e164 = models.CharField(max_length=16, blank=True, default="")
    #: FCM registration token for this officer's device. ``recipient_id`` on a
    #: dispatch is the actor id, not a push token.
    push_token = models.CharField(max_length=4096, blank=True, default="")

    class Meta:
        db_table = "officer_profile"

    def __str__(self) -> str:
        return f"{self.actor_id} ({self.role})"

    @property
    def is_certified(self) -> bool:
        return (
            self.training_valid_until is not None
            and self.training_valid_until >= timezone.localdate()
        )

    @property
    def may_receive_cases(self) -> bool:
        return self.is_active and self.is_certified


class Case(models.Model):
    """A welfare case opened when an assessment becomes officer-visible.

    ``officer_rationale`` is mandatory on close. Requiring a sentence of reasoning
    is not bureaucracy for its own sake: FR-4.2 makes the officer the decision
    maker and the system the decision aid, and an outcome recorded without a
    reason is indistinguishable from an outcome that was never considered. It is
    also the raw material for the WDEC's review of decision quality.
    """

    id = models.BigAutoField(primary_key=True)
    subject_token = models.CharField(max_length=64, db_index=True)
    assessment = models.ForeignKey(
        "governance.RiskAssessmentRecord", on_delete=models.PROTECT, related_name="cases"
    )
    unit = models.ForeignKey("governance.Unit", on_delete=models.PROTECT, related_name="cases")

    tier_at_open = models.CharField(max_length=2, choices=Tier.choices)
    contributing_categories = models.JSONField(default=list, blank=True)

    assigned_officer = models.ForeignKey(
        OfficerProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cases",
    )
    status = models.CharField(
        max_length=16, choices=CaseStatus.choices, default=CaseStatus.OPEN, db_index=True
    )

    opened_at = models.DateTimeField(default=timezone.now, db_index=True)
    #: Derived from the tier's response SLA (§4.5): hours for T4, days for T2.
    sla_due_at = models.DateTimeField(db_index=True)
    first_contact_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    outcome_code = models.CharField(max_length=48, blank=True, default="")
    officer_rationale = models.TextField(blank=True, default="")

    #: FR-4.5. A person may contest a flag, and the contest travels with the case
    #: so that a reviewer sees the disagreement next to the decision.
    contested_at = models.DateTimeField(null=True, blank=True)
    contest_note = models.TextField(blank=True, default="")

    class Meta:
        db_table = "case"
        ordering = ("-opened_at",)
        indexes = [
            models.Index(fields=["status", "sla_due_at"]),
            models.Index(fields=["assigned_officer", "status"]),
            models.Index(fields=["unit", "status"]),
        ]

    def __str__(self) -> str:
        return f"case {self.pk} [{self.status}] {self.tier_at_open}"

    @property
    def is_open(self) -> bool:
        return self.status in {CaseStatus.OPEN, CaseStatus.CONTACTED, CaseStatus.CONTESTED}

    @property
    def is_breaching_sla(self) -> bool:
        return self.is_open and timezone.now() > self.sla_due_at


class AccessGrant(models.Model):
    """Permission for one actor to see one thing about one person until a time.

    ``break_glass`` is the emergency path and is priced accordingly: it is
    reviewed by the WDEC without exception, and §6.3 requires the individual to
    be notified that it happened. Making the override available but expensive is
    the point — a system that cannot be overridden in a genuine emergency will be
    worked around, and a system that can be overridden silently will be.
    """

    id = models.BigAutoField(primary_key=True)
    subject_token = models.CharField(max_length=64, db_index=True)
    grantee_id = models.CharField(max_length=128, db_index=True)
    grantee_role = models.CharField(max_length=32, choices=Role.choices)
    scope = models.CharField(max_length=32, choices=GrantScope.choices)

    case = models.ForeignKey(
        Case, null=True, blank=True, on_delete=models.CASCADE, related_name="grants"
    )

    granted_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(db_index=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    #: Whether this grant rests on the individual's explicit agreement. False
    #: only where another basis applies, which in practice means the acute path.
    subject_consented = models.BooleanField(default=False)
    legal_basis = models.CharField(max_length=32, choices=LegalBasis.choices)
    justification = models.TextField()

    break_glass = models.BooleanField(default=False)
    wdec_reviewed_at = models.DateTimeField(null=True, blank=True)
    subject_notified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "access_grant"
        ordering = ("-granted_at",)
        indexes = [
            models.Index(fields=["grantee_id", "subject_token", "expires_at"]),
            models.Index(fields=["break_glass", "wdec_reviewed_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(expires_at__gt=models.F("granted_at")),
                name="grant_expires_after_grant",
            )
        ]

    def __str__(self) -> str:
        return f"{self.grantee_id} -> {self.subject_token} [{self.scope}]"

    @property
    def is_live(self) -> bool:
        return self.revoked_at is None and self.expires_at > timezone.now()

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Clamp the expiry to the statutory maximum rather than trusting callers.

        A caller passing a two-year expiry is a bug, and the safe failure mode is
        a shorter grant, not a longer one. Enforcing it here means every write
        path is covered, including admin actions and data migrations.
        """
        ceiling = self.granted_at + timedelta(days=MAX_GRANT_DAYS)
        if self.expires_at > ceiling:
            self.expires_at = ceiling
        super().save(*args, **kwargs)


class AlertDispatch(models.Model):
    """A notification sent about a case, and what became of it (§4.5, M8/M9).

    Delivery is tracked because an unacknowledged T4 alert must escalate. The
    difference between "sent" and "acknowledged" is the difference between the
    system having done its part and a human actually being on the way, and only
    the second one helps the person at risk.
    """

    id = models.BigAutoField(primary_key=True)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="alerts")
    recipient_id = models.CharField(max_length=128, db_index=True)
    recipient_role = models.CharField(max_length=32, choices=Role.choices)
    channel = models.CharField(max_length=16, choices=AlertChannel.choices)

    tier = models.CharField(max_length=2, choices=Tier.choices)
    #: Rendered notification text. Carries the tier and category names only; the
    #: acute path adds no clinical detail, because an SMS is not a confidential
    #: channel and a phone screen is read by whoever is holding the phone.
    body = models.TextField()

    queued_at = models.DateTimeField(default=timezone.now)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=16, choices=DeliveryStatus.choices, default=DeliveryStatus.QUEUED
    )
    failure_reason = models.CharField(max_length=256, blank=True, default="")

    escalated_to = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="escalated_from"
    )
    #: Idempotency key. The acute path retries aggressively across channels, and
    #: without this a network blip becomes four SMS messages to a duty officer.
    dedupe_key = models.CharField(max_length=128, unique=True)

    class Meta:
        db_table = "alert_dispatch"
        ordering = ("-queued_at",)
        indexes = [models.Index(fields=["status", "queued_at"])]

    def __str__(self) -> str:
        return f"alert {self.pk} {self.channel} [{self.status}]"


class InterventionRecommendation(models.Model):
    """A suggested next step, and whether the officer took it (§4.5).

    ``accepted`` being nullable is load-bearing. The system proposes; the officer
    disposes. Recording overrides — and, over time, noticing that officers
    consistently reject a particular recommendation — is how the ruleset learns
    it is wrong, which is a far better feedback loop than assuming the model was
    right and the humans were lazy.
    """

    id = models.BigAutoField(primary_key=True)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="recommendations")
    code = models.CharField(max_length=48)
    rationale = models.TextField()
    priority = models.PositiveSmallIntegerField(default=0)

    accepted = models.BooleanField(null=True, blank=True)
    officer_note = models.TextField(blank=True, default="")
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "intervention_recommendation"
        ordering = ("case", "priority")
