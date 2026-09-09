"""Publishing the audit chain head somewhere the database cannot reach.

The hash chain on ``audit_event`` makes an *edit* detectable, because changing
one row breaks the link to the next. It does not make a **rewrite** detectable.
An insider who can disable the trigger, edit a row, recompute every hash forward
and re-enable the trigger produces a chain that verifies perfectly — and the
suite's own ``test_recomputing_the_whole_chain_defeats_hashing_alone`` says so
in as many words.

The anchor is the answer, and only if it leaves. An anchor row sitting in the
same database as the log it commits to is rewritten in the same breath as
everything else. What defeats the rewrite is that somebody *outside* wrote down
what the head hash was on Tuesday: the attacker can produce a consistent chain,
but not one that also matches a value the WDEC recorded before the edit.

So the destination matters more than the mechanism. This module publishes to a
pluggable sink and records where it went, and an anchor whose publication failed
is left unpublished rather than marked as done — an anchor that claims to have
been externalised but was not is worse than no anchor at all, because it retires
the suspicion that would otherwise have prompted somebody to check.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from django.db import router, transaction
from django.utils import timezone

from .models import AuditAnchor, AuditEvent

logger = logging.getLogger(__name__)


class AnchorPublicationError(Exception):
    """The anchor could not be placed beyond the database's reach."""


@dataclass(frozen=True, slots=True)
class AnchorRecord:
    """What gets published. Carries no personal data — only counts and hashes."""

    anchored_at: datetime
    head_event_id: int
    head_hash: str
    event_count: int

    def as_payload(self) -> dict[str, object]:
        return {
            "anchored_at": self.anchored_at.isoformat(),
            "head_event_id": self.head_event_id,
            "head_hash": self.head_hash,
            "event_count": self.event_count,
        }

    def digest(self) -> str:
        encoded = json.dumps(self.as_payload(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode()).hexdigest()


class AnchorSink(Protocol):
    """Somewhere an anchor can be written that the analytics database cannot edit."""

    @property
    def name(self) -> str:
        """Recorded in ``AuditAnchor.published_to``."""

    def publish(self, record: AnchorRecord) -> None:
        """Write the anchor, or raise :class:`AnchorPublicationError`."""


class AppendOnlyFileSink:
    """Writes anchors to an append-only file, for development and small sites.

    A file on the same host is a weak sink — it is a placeholder for the
    WORM-backed store and the WDEC-held ledger that §7.3 and §11.3 call for, and
    the honest thing is to say so rather than let a local file stand in
    silently. It is still strictly better than nothing: it survives a database
    rewrite, which is the specific attack the anchor exists to catch.
    """

    def __init__(self, path: Path, name: str = "file:local-worm") -> None:
        self._path = path
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def publish(self, record: AnchorRecord) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            line = json.dumps(
                {**record.as_payload(), "digest": record.digest()},
                sort_keys=True,
                separators=(",", ":"),
            )
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
                handle.flush()
        except OSError as exc:
            raise AnchorPublicationError(
                f"Could not append the anchor to {self._path}: {exc}"
            ) from exc


def publish_anchor(sink: AnchorSink, *, now: datetime | None = None) -> AuditAnchor | None:
    """Anchor the current chain head and publish it. Returns ``None`` if empty.

    The row is written first and its ``published_to`` set only after the sink
    accepts it. If publication fails, the anchor remains in the table with an
    empty destination, which is exactly what the operator needs to see: a
    commitment that was made but never externalised, and therefore one that
    proves nothing yet.
    """
    using = router.db_for_write(AuditAnchor)

    with transaction.atomic(using=using):
        head = AuditEvent.objects.using(using).order_by("-id").first()
        if head is None:
            logger.info("no audit events to anchor")
            return None

        anchor = AuditAnchor.objects.using(using).create(
            anchored_at=now or timezone.now(),
            head_event_id=head.id,
            head_hash=head.row_hash,
            event_count=AuditEvent.objects.using(using).count(),
        )

    record = AnchorRecord(
        anchored_at=anchor.anchored_at,
        head_event_id=anchor.head_event_id,
        head_hash=anchor.head_hash,
        event_count=anchor.event_count,
    )

    sink.publish(record)

    # Only now, and deliberately outside the transaction above: an anchor is
    # marked published because a sink accepted it, never in the hope that one
    # will.
    AuditAnchor.objects.using(using).filter(pk=anchor.pk).update(published_to=sink.name)
    anchor.refresh_from_db(using=using)

    logger.info(
        "published audit anchor",
        extra={
            "event": "audit.anchor_published",
            "head_event_id": anchor.head_event_id,
            "event_count": anchor.event_count,
            "published_to": sink.name,
        },
    )
    return anchor


def unpublished_anchors() -> list[AuditAnchor]:
    """Anchors that were recorded but never made it out of the database.

    A non-empty result is an operational alarm, not a report: every one of these
    is a window during which a full chain rewrite would go unnoticed.
    """
    return list(AuditAnchor.objects.filter(published_to="").order_by("anchored_at"))
