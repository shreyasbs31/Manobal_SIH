"""The audit log's tamper-evidence guarantees (SDD §7.3, §9.6).

These tests are the reason the hash chain exists. Any of them failing means the
system can no longer prove who looked at whom, which under §7.3 is a release
blocker rather than a bug to triage.
"""

from __future__ import annotations

import pytest
from django.db import connections
from django.db.utils import IntegrityError

from manobal_core.apps.governance.enums import AuditAction, LegalBasis, PurposeCode, Role
from manobal_core.apps.governance.models import GENESIS_HASH, AuditEvent

pytestmark = pytest.mark.django_db


def _chain_break() -> tuple[int, str, str] | None:
    """Ask PostgreSQL whether the chain is intact, using the shipped verifier."""
    with connections["default"].cursor() as cursor:
        cursor.execute("SELECT * FROM manobal_audit_chain_break()")
        return cursor.fetchone()


class TestChainConstruction:
    def test_the_first_event_links_to_the_genesis_hash(self, audit_kwargs: dict[str, str]) -> None:
        event = AuditEvent.record(**audit_kwargs)
        assert event.prev_hash == GENESIS_HASH

    def test_each_event_links_to_its_predecessor(self, audit_kwargs: dict[str, str]) -> None:
        first = AuditEvent.record(**audit_kwargs)
        second = AuditEvent.record(**audit_kwargs)
        assert second.prev_hash == first.row_hash

    def test_the_hash_commits_to_the_row_contents(self, audit_kwargs: dict[str, str]) -> None:
        event = AuditEvent.record(**audit_kwargs)
        assert event.row_hash == event.compute_hash()

    def test_identical_actions_still_produce_distinct_hashes(
        self, audit_kwargs: dict[str, str]
    ) -> None:
        """Two identical accesses must remain individually accountable.

        If an officer reads the same record twice, both reads have to appear.
        Chaining on ``prev_hash`` gives every row a distinct input even when its
        semantic content is byte-identical to the last one.
        """
        hashes = {AuditEvent.record(**audit_kwargs).row_hash for _ in range(5)}
        assert len(hashes) == 5

    def test_a_freshly_written_chain_verifies(self, audit_kwargs: dict[str, str]) -> None:
        for _ in range(20):
            AuditEvent.record(**audit_kwargs)
        assert _chain_break() is None


class TestTamperEvidence:
    """What an attacker with database write access can and cannot do."""

    def test_updates_are_rejected_by_the_database(self, audit_kwargs: dict[str, str]) -> None:
        """Raw SQL, deliberately: the ORM guard is bypassed here on purpose.

        ``IntegrityError`` rather than a generic database error because the
        trigger raises SQLSTATE 23001, which is what an append-only violation
        actually is — a constraint on the table, not an internal fault.
        """
        AuditEvent.record(**audit_kwargs)
        with (
            pytest.raises(IntegrityError, match="append-only"),
            connections["default"].cursor() as cursor,
        ):
            cursor.execute("UPDATE audit_event SET actor_id = 'someone-else'")

    def test_deletes_are_rejected_by_the_database(self, audit_kwargs: dict[str, str]) -> None:
        AuditEvent.record(**audit_kwargs)
        with (
            pytest.raises(IntegrityError, match="append-only"),
            connections["default"].cursor() as cursor,
        ):
            cursor.execute("DELETE FROM audit_event")

    def test_the_orm_refuses_to_rewrite_a_saved_event(self, audit_kwargs: dict[str, str]) -> None:
        event = AuditEvent.record(**audit_kwargs)
        event.actor_id = "someone-else"
        with pytest.raises(ValueError, match="append-only"):
            event.save()

    def test_the_orm_refuses_to_delete_an_event(self, audit_kwargs: dict[str, str]) -> None:
        event = AuditEvent.record(**audit_kwargs)
        with pytest.raises(ValueError, match="cannot be deleted"):
            event.delete()

    def test_a_removed_row_is_detected_even_with_the_trigger_disabled(
        self, audit_kwargs: dict[str, str]
    ) -> None:
        """The scenario the chain actually exists for.

        A privileged operator can disable the trigger — no application can stop
        that. What they cannot do is remove the evidence: excising a row leaves
        its successor pointing at a hash that no longer precedes it, and the
        verifier names the exact row where the break occurs.
        """
        events = [AuditEvent.record(**audit_kwargs) for _ in range(5)]
        victim = events[2]

        with connections["default"].cursor() as cursor:
            cursor.execute("ALTER TABLE audit_event DISABLE TRIGGER audit_event_append_only")
            cursor.execute("DELETE FROM audit_event WHERE id = %s", [victim.pk])
            cursor.execute("ALTER TABLE audit_event ENABLE TRIGGER audit_event_append_only")

        break_point = _chain_break()
        assert break_point is not None, "excising an audit row went undetected"
        assert break_point[0] == events[3].pk

    def test_an_edited_row_is_detected(self, audit_kwargs: dict[str, str]) -> None:
        """Editing a row without recomputing the chain is caught immediately."""
        events = [AuditEvent.record(**audit_kwargs) for _ in range(4)]

        with connections["default"].cursor() as cursor:
            cursor.execute("ALTER TABLE audit_event DISABLE TRIGGER audit_event_append_only")
            cursor.execute(
                "UPDATE audit_event SET row_hash = %s WHERE id = %s",
                ["f" * 64, events[1].pk],
            )
            cursor.execute("ALTER TABLE audit_event ENABLE TRIGGER audit_event_append_only")

        break_point = _chain_break()
        assert break_point is not None
        assert break_point[0] == events[2].pk

    def test_recomputing_the_whole_chain_defeats_hashing_alone(
        self, audit_kwargs: dict[str, str]
    ) -> None:
        """An honest statement of the chain's limit, kept as an executable note.

        An attacker who can disable triggers *and* rewrite every subsequent hash
        produces a chain that verifies. This is not a defect in the hash chain;
        it is why :class:`AuditAnchor` exists. Recording the limit as a passing
        test keeps a future reader from over-trusting the verifier.
        """
        first = AuditEvent.record(**audit_kwargs)
        second = AuditEvent.record(**audit_kwargs)

        with connections["default"].cursor() as cursor:
            cursor.execute("ALTER TABLE audit_event DISABLE TRIGGER audit_event_append_only")
            cursor.execute("UPDATE audit_event SET actor_id = 'ghost' WHERE id = %s", [first.pk])
            first.refresh_from_db()
            forged = first.compute_hash()
            cursor.execute("UPDATE audit_event SET row_hash = %s WHERE id = %s", [forged, first.pk])
            cursor.execute(
                "UPDATE audit_event SET prev_hash = %s WHERE id = %s", [forged, second.pk]
            )
            cursor.execute("ALTER TABLE audit_event ENABLE TRIGGER audit_event_append_only")

        assert _chain_break() is None, (
            "a full rewrite verifies — which is precisely what AuditAnchor is for"
        )


class TestMandatoryFields:
    """§7.3: an access that cannot state its purpose must not be recorded as if
    it had one."""

    def test_purpose_and_legal_basis_are_not_nullable(self) -> None:
        purpose = AuditEvent._meta.get_field("purpose_code")
        basis = AuditEvent._meta.get_field("legal_basis")
        assert not purpose.null
        assert not basis.null

    def test_every_audited_action_has_an_enumerated_code(self) -> None:
        assert AuditAction.INDIVIDUAL_READ in AuditAction
        assert AuditAction.BREAK_GLASS in AuditAction
        assert AuditAction.IDENTITY_RESOLVE in AuditAction


class TestNoIdentifiersInTheAuditLog:
    """§3.2 rule 3: the record of who-looked-at-whom must not itself become a
    register of identities."""

    def test_the_model_has_no_direct_identifier_columns(self) -> None:
        forbidden = {"service_number", "name", "full_name", "mobile", "email", "aadhaar"}
        present = {field.name for field in AuditEvent._meta.get_fields()}
        assert not (forbidden & present)

    def test_a_recorded_event_references_a_token_not_a_person(
        self, audit_kwargs: dict[str, str]
    ) -> None:
        event = AuditEvent.record(**audit_kwargs, subject_token="tok_abc123")
        assert event.subject_token == "tok_abc123"
        assert not hasattr(event, "service_number")


class TestPurposeIsRecorded:
    def test_a_denial_is_audited_with_its_reason(self, audit_kwargs: dict[str, str]) -> None:
        """A refused access is as much a governance event as a granted one."""
        event = AuditEvent.record(
            **{**audit_kwargs, "action": AuditAction.ACCESS_DENIED},
            outcome="denied",
            detail={"reason": "tier_not_officer_visible"},
        )
        assert event.outcome == "denied"
        assert event.detail["reason"] == "tier_not_officer_visible"

    def test_break_glass_is_recorded_under_vital_interest(self) -> None:
        event = AuditEvent.record(
            actor_id="officer-001",
            actor_role=Role.WELFARE_OFFICER,
            action=AuditAction.BREAK_GLASS,
            purpose_code=PurposeCode.BREAK_GLASS,
            legal_basis=LegalBasis.VITAL_INTEREST,
            subject_token="tok_abc123",
        )
        assert event.legal_basis == LegalBasis.VITAL_INTEREST
