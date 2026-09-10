"""The identity vault and its own audit stream (SDD §4.9, §5.1, §5.2).

Three tables, and the reason for each is worth stating.

:class:`SubjectIdentity`
    The mapping. Every identifying column is ciphertext produced in the
    application before the driver sees it, so a dump of this database is
    ciphertext (NFR-SEC2). There is no foreign key to any analytics store and
    none back — §5.1: "the join is a deliberate, authorised, logged runtime
    operation performed by exactly one service, never a database relationship."

:class:`ResolutionAudit`
    Zone 3's own record of every tokenise and every resolve. The analytics-plane
    audit log is not sufficient on its own: an attacker who owned Zone 2 could
    resolve identities and erase the evidence from the same position. This
    stream is hash-chained so that an attacker who owns *Zone 3* cannot quietly
    edit it either.

:class:`SpentAssertion`
    Single-use enforcement for grant assertions, in the database rather than in
    memory because the resolver runs two replicas and both must agree that a
    capability has been spent.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Final

from django.db import IntegrityError, models, transaction

CHAIN_GENESIS: Final = "0" * 64
"""The predecessor hash of the first entry."""

_AUDIT_LOCK_ID: Final = 0x4D414E4F  # "MANO"
"""Advisory lock so two replicas cannot interleave and fork the chain."""


class Direction(models.TextChoices):
    """§4.9's directional scopes, recorded separately because they are
    separately authorised, separately rate-limited and separately alarming."""

    TOKENISE = "tokenise", "Tokenise (ingest boundary, write direction)"
    RESOLVE = "resolve", "Resolve (case path, read direction)"
    BREAK_GLASS = "break_glass", "Break-glass resolve (emergency)"


class SubjectIdentity(models.Model):
    """The only mapping between a token and a person.

    **Deviation from the §5.2 ERD, recorded deliberately.** The ERD models the
    posting as ``uuid current_unit_id``. The running system's ``Unit`` is keyed
    by its code, not a UUID, so a UUID here would reference nothing and could
    not be compared against the unit code an officer's grant assertion carries.
    The vault stores the unit code and the materialised ancestor path instead,
    which is what the out-of-unit anomaly check in §4.9 actually needs.

    The unit path is stored in the clear. It is organisational, not identifying:
    the analytics plane already knows every subject's unit, so encrypting it
    here would protect nothing while making the anomaly check impossible.
    """

    subject_token = models.CharField(max_length=64, primary_key=True)

    #: Keyed MAC of the normalised service number. Lets the ingest boundary find
    #: a row without the database ever holding the plaintext. Never leaves
    #: Zone 3 — its determinism is exactly what would make it a correlation key.
    service_no_index = models.CharField(max_length=64, unique=True, db_index=True)
    #: Blind index of the mobile. Enrolment OTP looks up a token without
    #: decrypting a name. Nullable so rows enrolled before this column existed
    #: remain valid.
    mobile_e164_index = models.CharField(
        max_length=64, unique=True, null=True, blank=True, db_index=True
    )

    #: The row's data key, encrypted under the KMS key-encryption key.
    wrapped_key = models.BinaryField()
    key_version = models.PositiveSmallIntegerField()

    service_no_enc = models.BinaryField()
    full_name_enc = models.BinaryField()
    rank_code_enc = models.BinaryField()
    mobile_e164_enc = models.BinaryField()

    current_unit_code = models.CharField(max_length=32, db_index=True)
    current_unit_path = models.CharField(max_length=512)
    force_code = models.CharField(max_length=16, db_index=True)

    enrolled_on = models.DateField()
    separated_on = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "subject_identity"
        verbose_name_plural = "subject identities"
        indexes = [
            models.Index(
                fields=["separated_on"], name="subj_ident_separated_idx"
            ),
        ]

    def __str__(self) -> str:
        """Renders the token, never a name. This object appears in tracebacks."""
        return self.subject_token


class ResolutionAudit(models.Model):
    """Append-only, hash-chained record of every crossing of this boundary.

    Written *before* the read it describes (§5.4), so a crash between the audit
    and the lookup leaves an over-recorded audit rather than an unrecorded
    resolution. Erring towards claiming a resolution that did not happen is
    recoverable; the opposite is not.
    """

    seq = models.BigAutoField(primary_key=True)
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)

    direction = models.CharField(max_length=16, choices=Direction.choices)
    granted = models.BooleanField()
    denial_reason = models.CharField(max_length=32, blank=True, default="")

    actor_id = models.CharField(max_length=64, db_index=True)
    actor_role = models.CharField(max_length=32)
    actor_unit_code = models.CharField(max_length=32, blank=True, default="")
    workload_id = models.CharField(max_length=128)

    subject_token = models.CharField(max_length=64, blank=True, default="")
    case_id = models.CharField(max_length=64, blank=True, default="")
    grant_id = models.CharField(max_length=64, blank=True, default="")
    assertion_id = models.CharField(max_length=64, blank=True, default="")

    purpose_code = models.CharField(max_length=64, blank=True, default="")
    justification = models.TextField(blank=True, default="")

    #: Batch size for the tokenise direction, so a bulk boundary call is one
    #: audit entry rather than eighty thousand.
    record_count = models.PositiveIntegerField(default=1)

    anomalies = models.JSONField(default=list)
    source_ip = models.GenericIPAddressField(null=True, blank=True)

    prev_hash = models.CharField(max_length=64)
    entry_hash = models.CharField(max_length=64, unique=True)

    class Meta:
        db_table = "resolution_audit"
        indexes = [
            models.Index(fields=["actor_id", "-occurred_at"], name="res_audit_actor_idx"),
            models.Index(fields=["direction", "-occurred_at"], name="res_audit_dir_idx"),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            raise IntegrityError(
                "resolution_audit is append-only; an entry may never be edited. "
                "The database enforces this too — this check exists so the "
                "mistake surfaces in review rather than as a trigger violation."
            )
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise IntegrityError(
            "resolution_audit is append-only; entries are never deleted."
        )

    @classmethod
    @transaction.atomic
    def record(cls, **fields: Any) -> ResolutionAudit:
        """Append one entry, chained to its predecessor.

        The advisory lock is held for the remainder of the transaction. Two
        resolver replicas appending concurrently would otherwise both read the
        same tail and write two entries claiming the same predecessor, forking
        the chain and making later verification ambiguous.
        """
        with transaction.get_connection().cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [_AUDIT_LOCK_ID])

        previous = cls.objects.order_by("-seq").values_list("entry_hash", flat=True).first()
        prev_hash = previous or CHAIN_GENESIS

        entry = cls(**fields, prev_hash=prev_hash)
        entry.entry_hash = entry.compute_hash()
        entry.save(force_insert=True)
        return entry

    def compute_hash(self) -> str:
        """Hash over the fields that carry meaning, plus the predecessor.

        ``occurred_at`` is excluded because it is assigned by the database on
        insert and is not yet known here. The chain's job is to make *edits*
        detectable, and an edited row is detected through its content and its
        position regardless.
        """
        material = {
            "prev": self.prev_hash,
            "direction": self.direction,
            "granted": self.granted,
            "denial_reason": self.denial_reason,
            "actor_id": self.actor_id,
            "actor_role": self.actor_role,
            "workload_id": self.workload_id,
            "subject_token": self.subject_token,
            "case_id": self.case_id,
            "grant_id": self.grant_id,
            "assertion_id": self.assertion_id,
            "purpose_code": self.purpose_code,
            "justification": self.justification,
            "record_count": self.record_count,
            "anomalies": self.anomalies,
        }
        encoded = json.dumps(material, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode()).hexdigest()

    def __str__(self) -> str:
        verdict = "granted" if self.granted else f"denied({self.denial_reason})"
        return f"#{self.seq} {self.direction} {verdict} by {self.actor_id}"


class SpentAssertion(models.Model):
    """One row per grant assertion that has been honoured.

    The uniqueness of the primary key *is* the replay guard: two replicas
    racing on the same assertion both attempt the insert, and exactly one
    succeeds. A read-then-write check would let both through.
    """

    assertion_id = models.CharField(max_length=64, primary_key=True)
    expires_at = models.DateTimeField(db_index=True)
    spent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "spent_assertion"

    def __str__(self) -> str:
        return self.assertion_id


class DatabaseReplayGuard:
    """A :class:`~manobal_identity.grants.replay.ReplayGuard` backed by Postgres."""

    def consume(self, assertion_id: str, expires_at: datetime, now: datetime) -> bool:
        try:
            with transaction.atomic():
                SpentAssertion.objects.create(
                    assertion_id=assertion_id, expires_at=expires_at
                )
        except IntegrityError:
            return False
        return True

    @staticmethod
    def purge(now: datetime) -> int:
        """Drop records that could no longer be replayed anyway.

        An expired assertion is refused on its expiry, so keeping it proves
        nothing and the table would grow without bound.
        """
        deleted, _ = SpentAssertion.objects.filter(expires_at__lt=now).delete()
        return deleted


class EnrolmentChallenge(models.Model):
    """A hashed OTP bound to a mobile index. The plaintext code is never stored."""

    id = models.BigAutoField(primary_key=True)
    mobile_index = models.CharField(max_length=64, db_index=True)
    code_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "enrolment_challenge"
        indexes = [
            models.Index(
                fields=["mobile_index", "-created_at"],
                name="enrolment_c_mobile__idx",
            )
        ]

    def __str__(self) -> str:
        return f"otp {self.pk}"
