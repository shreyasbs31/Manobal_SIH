"""The append-only, hash-chained audit log (SDD §5.2 AUDIT_EVENT, §7.3).

The design goal is narrow and worth stating precisely: an administrator with
database credentials must not be able to remove the record of an access without
that removal being *detectable*. Nothing here prevents a superuser from deleting
a row — no application can prevent that — but every row commits to its
predecessor, so a deletion or edit breaks the chain at a known point, and the
daily anchor bounds how far back a rewrite could reach unnoticed.

Three mechanisms, each covering the previous one's gap:

1. ``row_hash = SHA256(prev_hash || canonical(row))`` links rows, so editing row
   *n* invalidates every hash after it.
2. A database trigger rejects ``UPDATE`` and ``DELETE`` on the table, so breaking
   the chain requires deliberately disabling a trigger rather than a stray query.
3. :class:`AuditAnchor` publishes the head hash on a schedule. Rewriting history
   that predates an anchor requires forging the anchor too.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any, Final

from django.db import DEFAULT_DB_ALIAS, models, transaction
from django.db import router as db_router
from django.utils import timezone

from ..enums import AuditAction, LegalBasis, PurposeCode, Role

if TYPE_CHECKING:
    from collections.abc import Mapping

#: The hash of the row before the first one. A fixed, well-known value so that a
#: verifier can check the chain from its true origin rather than trusting
#: whatever the first row claims its predecessor was.
GENESIS_HASH: Final = "0" * 64

#: Serialising the hashed payload deterministically matters more than it looks.
#: If two verifiers disagree about key order or float formatting they will
#: compute different hashes for the same row and report false tampering.
_JSON_ARGS: Final[dict[str, Any]] = {
    "sort_keys": True,
    "separators": (",", ":"),
    "ensure_ascii": False,
    "default": str,
}


def canonicalise(payload: Mapping[str, Any]) -> str:
    """Return the one agreed byte-level representation of ``payload``."""
    return json.dumps(payload, **_JSON_ARGS)


class AuditEvent(models.Model):
    """One immutable record of something that happened.

    Note what is *absent*: there is no ``service_number`` and no name. The audit
    log lives in the analytics plane and records the pseudonymous token, so the
    log of who-looked-at-whom does not itself become a register of identities
    (SDD §3.2 rule 3). Where an event concerns identity resolution, the
    corresponding identifying detail stays in the Zone 3 resolution audit.
    """

    id = models.BigAutoField(primary_key=True)

    #: Server receipt time. Deliberately not client-supplied: a caller must not
    #: be able to backdate its own audit row.
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)

    actor_id = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Stable subject claim of the authenticated principal.",
    )
    actor_role = models.CharField(max_length=32, choices=Role.choices)
    action = models.CharField(max_length=48, choices=AuditAction.choices, db_index=True)

    #: The pseudonymous token of the person the action concerned, if any.
    #: Null for actions with no individual subject, such as a ruleset change.
    subject_token = models.CharField(max_length=64, null=True, blank=True, db_index=True)

    #: SDD §7.3 requires both of these on every entry, so both are NOT NULL.
    #: A read path that cannot say why it is reading cannot write its audit row,
    #: and a read that cannot be audited must not happen.
    purpose_code = models.CharField(max_length=32, choices=PurposeCode.choices)
    legal_basis = models.CharField(max_length=32, choices=LegalBasis.choices)

    outcome = models.CharField(
        max_length=16,
        choices=[("success", "Success"), ("denied", "Denied"), ("error", "Error")],
        default="success",
    )
    source_ip = models.GenericIPAddressField(null=True, blank=True)
    request_id = models.CharField(max_length=64, null=True, blank=True, db_index=True)

    #: Action-specific detail. Must never contain free-text clinical content or
    #: any direct identifier; :meth:`record` is the only supported writer and
    #: callers are expected to pass structured, minimal values.
    detail = models.JSONField(default=dict, blank=True)

    prev_hash = models.CharField(max_length=64)
    row_hash = models.CharField(max_length=64, unique=True)

    class Meta:
        db_table = "audit_event"
        ordering = ("id",)
        indexes = [
            models.Index(fields=["subject_token", "occurred_at"]),
            models.Index(fields=["actor_id", "occurred_at"]),
            models.Index(fields=["action", "occurred_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.occurred_at:%Y-%m-%dT%H:%M:%SZ} {self.action} by {self.actor_role}"

    # ------------------------------------------------------------------ hash --

    def canonical_payload(self) -> dict[str, Any]:
        """The semantic content that the hash commits to.

        Excludes ``row_hash`` (it is the output) but includes ``prev_hash``,
        which is what actually chains the rows together.
        """
        return {
            "occurred_at": self.occurred_at.isoformat(),
            "actor_id": self.actor_id,
            "actor_role": self.actor_role,
            "action": self.action,
            "subject_token": self.subject_token,
            "purpose_code": self.purpose_code,
            "legal_basis": self.legal_basis,
            "outcome": self.outcome,
            "source_ip": self.source_ip,
            "request_id": self.request_id,
            "detail": self.detail,
            "prev_hash": self.prev_hash,
        }

    def compute_hash(self) -> str:
        return hashlib.sha256(canonicalise(self.canonical_payload()).encode()).hexdigest()

    # --------------------------------------------------------------- writing --

    @classmethod
    def record(cls, **fields: Any) -> AuditEvent:
        """Append one event, linking it to the current chain head.

        Serialisation is via a transaction-scoped advisory lock rather than
        ``SELECT ... FOR UPDATE`` on the tail row. Locking the tail row would let
        two concurrent writers read the same head before either commits and
        produce a fork; the advisory lock makes append a genuine critical
        section. It is held only for the duration of the insert.

        The target database is resolved through the router rather than named
        here. Hardcoding an alias duplicates routing knowledge that already
        lives in :class:`~manobal_core.db.routers.StoreRouter`, and the two
        copies drift.
        """
        using = fields.pop("using", None) or db_router.db_for_write(cls) or DEFAULT_DB_ALIAS
        with transaction.atomic(using=using):
            with transaction.get_connection(using).cursor() as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(%s)", [_AUDIT_LOCK_KEY])
            head = cls.objects.using(using).order_by("-id").values("row_hash").first()
            event = cls(prev_hash=head["row_hash"] if head else GENESIS_HASH, **fields)
            event.row_hash = event.compute_hash()
            event.save(using=using, force_insert=True)
        return event

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Reject rewrites in Python as well as in the database.

        The trigger is the real guarantee. This check exists so that a mistake
        surfaces as a clear application error during development rather than as
        an opaque database exception in production.
        """
        if not self._state.adding and not kwargs.get("force_insert"):
            msg = "audit_event rows are append-only; use AuditEvent.record()"
            raise ValueError(msg)
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> Any:
        msg = "audit_event rows cannot be deleted"
        raise ValueError(msg)


#: Arbitrary but fixed 64-bit key identifying the audit-append critical section.
_AUDIT_LOCK_KEY: Final = 0x4D414E4F42414C01


class AuditAnchor(models.Model):
    """A periodically published commitment to the chain head (SDD §7.3).

    Without an anchor, an attacker who can write to the table could recompute
    every hash after the row they edited and present a chain that verifies. The
    anchor defeats that by pinning the head at a known time; a rewrite of
    anything older would also have to alter an already-published anchor value.

    Publishing the anchor somewhere outside this database — a WDEC-held record,
    a signed transparency feed — is what makes it worth anything, so
    :attr:`published_to` records where it went.
    """

    id = models.BigAutoField(primary_key=True)
    anchored_at = models.DateTimeField(default=timezone.now, db_index=True)
    head_event_id = models.BigIntegerField()
    head_hash = models.CharField(max_length=64)
    event_count = models.BigIntegerField()
    published_to = models.CharField(max_length=128, blank=True, default="")

    class Meta:
        db_table = "audit_anchor"
        ordering = ("-anchored_at",)
