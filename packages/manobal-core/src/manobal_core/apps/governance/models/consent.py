"""The consent ledger and the erasure saga (SDD §5.2, §5.4, §6.4.1, §7.9).

Consent is modelled as an append-only ledger rather than a mutable row per
person per data type. The difference is not academic. A mutable row can answer
"may we use their heart-rate data today?" but cannot answer "were we permitted to
use it on 14 March, and under which version of the consent text?" — and the
second question is the one asked during a grievance or an audit. Withdrawal
therefore appends a revocation; it never updates a grant in place.
"""

from __future__ import annotations

from typing import Any

from django.db import DEFAULT_DB_ALIAS, models
from django.db import router as db_router
from django.utils import timezone

from ..enums import DataType, DeviceTier, ErasureStatus


class ConsentTextVersion(models.Model):
    """A specific wording of the consent notice, in a specific language.

    Storing the text — not just a version number — is what makes it possible to
    show a person exactly what they agreed to, in the language they read it in.
    A checksum is kept so an altered record is detectable.
    """

    id = models.BigAutoField(primary_key=True)
    version = models.CharField(max_length=32)
    language_code = models.CharField(max_length=8)
    device_tier = models.CharField(max_length=1, choices=DeviceTier.choices)
    body = models.TextField()
    checksum = models.CharField(max_length=64)
    effective_from = models.DateTimeField()
    retired_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "consent_text_version"
        constraints = [
            models.UniqueConstraint(
                fields=["version", "language_code", "device_tier"],
                name="uniq_consent_text",
            )
        ]

    def __str__(self) -> str:
        return f"{self.version}/{self.language_code}/tier{self.device_tier}"


class ConsentEntry(models.Model):
    """One immutable grant or revocation.

    The current state for a (subject, data_type) pair is the latest row by
    ``recorded_at``. :meth:`current_for` performs that resolution; nothing else
    should reimplement it, because a subtly different tie-break in a second
    implementation is how a withdrawal quietly stops taking effect.
    """

    id = models.BigAutoField(primary_key=True)
    subject_token = models.CharField(max_length=64, db_index=True)
    data_type = models.CharField(max_length=32, choices=DataType.choices)

    granted = models.BooleanField(help_text="True for a grant, False for a withdrawal.")
    recorded_at = models.DateTimeField(default=timezone.now, db_index=True)

    consent_text = models.ForeignKey(
        ConsentTextVersion, on_delete=models.PROTECT, related_name="entries"
    )
    #: How the person expressed this: in-app, or on paper witnessed by an officer
    #: for personnel without a suitable device (FR-1.1 accessibility).
    method = models.CharField(
        max_length=24,
        choices=[("app", "In-app"), ("assisted", "Assisted"), ("paper", "Paper form")],
        default="app",
    )
    #: Present only for assisted or paper capture, and holds the *token* of the
    #: assisting officer, never a name.
    witnessed_by = models.CharField(max_length=128, blank=True, default="")

    class Meta:
        db_table = "consent_entry"
        ordering = ("subject_token", "data_type", "-recorded_at")
        indexes = [models.Index(fields=["subject_token", "data_type", "-recorded_at"])]

    def __str__(self) -> str:
        verb = "granted" if self.granted else "withdrew"
        return f"{self.subject_token} {verb} {self.data_type}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        # ``_state.adding`` rather than a primary-key check: it is Django's own
        # notion of "this row is not in the database yet", and it stays correct
        # for a model whose key was assigned explicitly before the first save.
        if not self._state.adding:
            msg = "consent entries are append-only; append a new entry instead"
            raise ValueError(msg)
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> Any:
        msg = "consent entries cannot be deleted"
        raise ValueError(msg)

    @classmethod
    def current_for(cls, subject_token: str, *, using: str | None = None) -> dict[str, bool]:
        """Return the effective consent state for every data type.

        Types the person has never answered for are reported as ``False``. There
        is no implicit grant: silence is not consent, and a data type that was
        added to the system after someone enrolled must be asked about, not
        assumed.
        """
        alias = using or db_router.db_for_read(cls) or DEFAULT_DB_ALIAS
        state = dict.fromkeys(DataType.values, False)
        rows = (
            cls.objects.using(alias)
            .filter(subject_token=subject_token)
            .order_by("data_type", "-recorded_at", "-id")
            .values("data_type", "granted")
        )
        seen: set[str] = set()
        for row in rows:
            if row["data_type"] not in seen:
                seen.add(row["data_type"])
                state[row["data_type"]] = row["granted"]
        return state


class ErasureRequest(models.Model):
    """The durable state machine behind "withdraw and delete" (SDD §5.4).

    Purging one person's data touches five databases and an object store, and
    those cannot be enrolled in a single transaction. The saga is the honest
    alternative: record the intent first, then purge store by store, marking each
    as it completes. A crash mid-way leaves a row that is visibly incomplete and
    a resumable list of what remains, rather than a person who believes they were
    deleted and was not.

    Note ``retain_aggregates``: previously published unit-level statistics are
    not retracted, because they are irreversibly anonymised and un-publishing
    them could itself single a person out. §7.9 says this must be stated in the
    consent text, so the flag exists to make the promise explicit and auditable.
    """

    id = models.BigAutoField(primary_key=True)
    subject_token = models.CharField(max_length=64, db_index=True)
    requested_at = models.DateTimeField(default=timezone.now)
    #: Erasure of one data type, or of everything when null.
    data_type = models.CharField(max_length=32, choices=DataType.choices, null=True, blank=True)

    status = models.CharField(
        max_length=24, choices=ErasureStatus.choices, default=ErasureStatus.INTENT_RECORDED
    )
    #: ``{"psy_store": "completed", "bio_store": "pending", ...}`` — the resume
    #: point after a crash.
    store_progress = models.JSONField(default=dict, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(blank=True, default="")

    completed_at = models.DateTimeField(null=True, blank=True)
    #: Handed to the individual as proof. Signed so that it means something
    #: outside this system.
    receipt_id = models.CharField(max_length=64, blank=True, default="")
    receipt_signature = models.TextField(blank=True, default="")

    retain_aggregates = models.BooleanField(
        default=True,
        help_text="Anonymised aggregates already published are not retracted (§7.9).",
    )

    class Meta:
        db_table = "erasure_request"
        ordering = ("-requested_at",)
        indexes = [models.Index(fields=["status", "requested_at"])]

    def __str__(self) -> str:
        scope = self.data_type or "all data"
        return f"erasure of {scope} for {self.subject_token} [{self.status}]"


class DisclosureRequest(models.Model):
    """An officer asking to see a trend, and the individual's answer (FR-4.4).

    This is the mechanism that keeps "the officer sees a category name, not a
    chart" true in practice. The default answer is no answer: an unanswered
    request expires and grants nothing. Declining is recorded as a legitimate
    outcome and is explicitly not an adverse signal — the SDD is unambiguous
    that a refusal must not feed back into the person's assessment, so this model
    has no path into the risk pipeline at all.
    """

    id = models.BigAutoField(primary_key=True)
    case = models.ForeignKey(
        "governance.Case", on_delete=models.CASCADE, related_name="disclosure_requests"
    )
    subject_token = models.CharField(max_length=64, db_index=True)
    requested_by = models.CharField(max_length=128)
    category = models.CharField(max_length=64)
    rationale = models.TextField()

    requested_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    responded_at = models.DateTimeField(null=True, blank=True)
    granted = models.BooleanField(null=True, blank=True)

    class Meta:
        db_table = "disclosure_request"
        ordering = ("-requested_at",)

    @property
    def is_actionable(self) -> bool:
        """True only on an explicit, unexpired grant."""
        return self.granted is True and self.expires_at > timezone.now()
