"""Anchors only defend anything once they have left the database (§7.3).

The hash chain catches an *edit*: change one row and its successor no longer
links to it. It does not catch a **rewrite**. Somebody who can drop the trigger,
edit a row, recompute every hash forward and put the trigger back produces a
chain that verifies perfectly — ``test_audit_chain.py`` says so in as many
words.

What defeats that is a value written down somewhere the attacker's database
credentials do not reach. These tests are about the publishing, not the hashing,
because the publishing is the part that was missing.
"""

from __future__ import annotations

import json

import pytest

from manobal_core.apps.governance.anchoring import (
    AnchorPublicationError,
    AnchorRecord,
    AppendOnlyFileSink,
    publish_anchor,
    unpublished_anchors,
)
from manobal_core.apps.governance.models import AuditAnchor, AuditEvent

pytestmark = pytest.mark.django_db


class RefusingSink:
    """A sink that is unavailable, which is the interesting failure case."""

    name = "test:unavailable"

    def publish(self, record: AnchorRecord) -> None:
        raise AnchorPublicationError("the WORM store is unreachable")


@pytest.fixture
def sink(tmp_path) -> AppendOnlyFileSink:
    return AppendOnlyFileSink(tmp_path / "anchors.jsonl", name="test:file")


@pytest.fixture
def some_events(audit_kwargs) -> None:
    for _ in range(3):
        AuditEvent.record(**audit_kwargs)


class TestPublishing:
    def test_an_anchor_commits_to_the_current_chain_head(self, some_events, sink) -> None:
        anchor = publish_anchor(sink)
        head = AuditEvent.objects.order_by("-id").first()
        assert anchor is not None
        assert anchor.head_hash == head.row_hash
        assert anchor.head_event_id == head.id
        assert anchor.event_count == 3

    def test_the_anchor_records_where_it_was_published(self, some_events, sink) -> None:
        """``published_to`` was the field that nothing ever wrote, which is what
        made the whole mechanism decorative."""
        anchor = publish_anchor(sink)
        assert anchor.published_to == "test:file"

    def test_the_anchor_actually_reaches_the_sink(self, some_events, sink, tmp_path) -> None:
        publish_anchor(sink)
        written = json.loads((tmp_path / "anchors.jsonl").read_text().strip())
        head = AuditEvent.objects.order_by("-id").first()
        assert written["head_hash"] == head.row_hash

    def test_publishing_twice_appends_rather_than_replaces(
        self, some_events, sink, tmp_path
    ) -> None:
        """A sink that overwrites keeps only the most recent commitment, which
        is the one an attacker would rewrite to."""
        publish_anchor(sink)
        AuditEvent.record(**_kwargs())
        publish_anchor(sink)
        assert len((tmp_path / "anchors.jsonl").read_text().strip().splitlines()) == 2

    def test_an_empty_log_produces_no_anchor(self, sink) -> None:
        assert publish_anchor(sink) is None


class TestFailureIsVisible:
    def test_a_failed_publication_leaves_the_anchor_unpublished(self, some_events) -> None:
        """Rather than marking it done and moving on. An anchor that claims to
        have been externalised but was not is worse than none at all, because it
        retires the suspicion that would have prompted somebody to check."""
        with pytest.raises(AnchorPublicationError):
            publish_anchor(RefusingSink())
        assert AuditAnchor.objects.get().published_to == ""

    def test_stranded_anchors_are_reportable(self, some_events) -> None:
        with pytest.raises(AnchorPublicationError):
            publish_anchor(RefusingSink())
        assert len(unpublished_anchors()) == 1

    def test_a_successful_publication_leaves_nothing_stranded(self, some_events, sink) -> None:
        publish_anchor(sink)
        assert unpublished_anchors() == []

    def test_an_unwritable_destination_raises_rather_than_passing(
        self, some_events, tmp_path
    ) -> None:
        unwritable = tmp_path / "anchors.jsonl"
        unwritable.mkdir()  # a directory where a file should be
        with pytest.raises(AnchorPublicationError):
            publish_anchor(AppendOnlyFileSink(unwritable))


class TestTheAnchorCarriesNoPersonalData:
    def test_an_anchor_is_only_hashes_and_counts(self, some_events, sink) -> None:
        """It is published outside the system's access controls by design, so
        anything personal in it would be published too."""
        anchor = publish_anchor(sink)
        payload = AnchorRecord(
            anchored_at=anchor.anchored_at,
            head_event_id=anchor.head_event_id,
            head_hash=anchor.head_hash,
            event_count=anchor.event_count,
        ).as_payload()
        assert set(payload) == {
            "anchored_at",
            "head_event_id",
            "head_hash",
            "event_count",
        }

    def test_the_published_record_is_self_verifying(self, some_events, sink) -> None:
        anchor = publish_anchor(sink)
        record = AnchorRecord(
            anchored_at=anchor.anchored_at,
            head_event_id=anchor.head_event_id,
            head_hash=anchor.head_hash,
            event_count=anchor.event_count,
        )
        assert record.digest() == record.digest()
        assert len(record.digest()) == 64


class TestTheManagementCommand:
    def test_the_command_publishes_and_reports(self, some_events, tmp_path) -> None:
        from io import StringIO

        from django.core.management import call_command

        out = StringIO()
        call_command("publish_audit_anchor", "--path", str(tmp_path / "a.jsonl"), stdout=out)
        assert "Anchored event" in out.getvalue()
        assert AuditAnchor.objects.get().published_to.startswith("file:")

    def test_the_command_says_so_when_the_log_is_empty(self, tmp_path) -> None:
        from io import StringIO

        from django.core.management import call_command

        out = StringIO()
        call_command("publish_audit_anchor", "--path", str(tmp_path / "a.jsonl"), stdout=out)
        assert "No audit events" in out.getvalue()

    def test_the_command_warns_about_stranded_anchors(self, some_events, tmp_path) -> None:
        from io import StringIO

        from django.core.management import call_command

        with pytest.raises(AnchorPublicationError):
            publish_anchor(RefusingSink())
        err = StringIO()
        call_command(
            "publish_audit_anchor",
            "--path",
            str(tmp_path / "a.jsonl"),
            "--warn-unpublished",
            stdout=StringIO(),
            stderr=err,
        )
        assert "never externalised" in err.getvalue()

    def test_a_failed_publication_exits_nonzero(self, some_events, tmp_path) -> None:
        from django.core.management import CommandError, call_command

        blocked = tmp_path / "not-a-file"
        blocked.mkdir()
        with pytest.raises(CommandError, match="MB-7301"):
            call_command("publish_audit_anchor", "--path", str(blocked))


def _kwargs() -> dict[str, str]:
    return {
        "action": "authn_success",
        "actor_id": "officer_221",
        "actor_role": "welfare_officer",
        "purpose_code": "case_review",
        "outcome": "allow",
    }
