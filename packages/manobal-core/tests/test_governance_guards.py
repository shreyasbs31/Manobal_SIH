"""The governance guarantees that were previously enforced only in Python.

Each test here does its damage through a path that bypasses the ORM's ``save()``
method — raw SQL, or ``QuerySet.update()``. That is the point. An
application-level check is a comment with a stack trace: it protects against a
mistake in the code above it and against nothing else. A migration, a management
shell, a data fix and anybody holding the database password all walk straight
past it, and those are precisely the circumstances in which these particular
records get quietly adjusted.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.db import IntegrityError, connections, router
from django.utils import timezone

from manobal_core.apps.governance.enums import (
    DataType,
    GrantScope,
    LegalBasis,
    Role,
)
from manobal_core.apps.governance.models import (
    AccessGrant,
    AuditAnchor,
    ConsentEntry,
    ConsentTextVersion,
    RulesetVersion,
)

pytestmark = pytest.mark.django_db


def gov_cursor():
    return connections[router.db_for_write(AccessGrant)].cursor()


@pytest.fixture
def grant() -> AccessGrant:
    now = timezone.now()
    return AccessGrant.objects.create(
        grantee_id="officer_221",
        grantee_role=Role.WELFARE_OFFICER,
        subject_token="st_abc",
        scope=GrantScope.FLAG,
        granted_at=now,
        expires_at=now + timedelta(days=7),
        subject_consented=True,
        legal_basis=LegalBasis.CONSENT,
        justification="Assigned welfare case review.",
    )


class TestTheAccessGrantCeilingIsEnforcedByTheDatabase:
    """FR-5.4: time-boxed and auto-revoked after 14 days.

    A standing grant is what turns welfare support into surveillance, so the
    ceiling has to hold on every write path rather than the polite one.
    """

    def test_a_raw_sql_extension_beyond_fourteen_days_is_refused(self, grant) -> None:
        with pytest.raises(IntegrityError), gov_cursor() as cursor:
            cursor.execute(
                "UPDATE access_grant SET expires_at = granted_at + INTERVAL '2 years'"
                " WHERE id = %s",
                [grant.id],
            )

    def test_a_queryset_update_beyond_fourteen_days_is_refused(self, grant) -> None:
        """``QuerySet.update()`` never calls ``save()``, so the Python clamp
        that used to be the only defence was not involved at all."""
        with pytest.raises(IntegrityError):
            AccessGrant.objects.filter(pk=grant.pk).update(
                expires_at=grant.granted_at + timedelta(days=365)
            )

    def test_an_insert_beyond_fourteen_days_is_refused(self) -> None:
        now = timezone.now()
        with pytest.raises(IntegrityError):
            AccessGrant.objects.bulk_create(
                [
                    AccessGrant(
                        grantee_id="officer_999",
                        grantee_role=Role.WELFARE_OFFICER,
                        subject_token="st_x",
                        scope=GrantScope.FLAG,
                        granted_at=now,
                        expires_at=now + timedelta(days=30),
                        subject_consented=True,
                        legal_basis=LegalBasis.CONSENT,
                        justification="Over the ceiling.",
                    )
                ]
            )

    def test_an_extension_within_the_ceiling_is_permitted(self, grant) -> None:
        """The guard must not obstruct legitimate case work."""
        AccessGrant.objects.filter(pk=grant.pk).update(
            expires_at=grant.granted_at + timedelta(days=13)
        )
        grant.refresh_from_db()
        assert grant.expires_at == grant.granted_at + timedelta(days=13)

    def test_exactly_fourteen_days_is_permitted(self, grant) -> None:
        AccessGrant.objects.filter(pk=grant.pk).update(
            expires_at=grant.granted_at + timedelta(days=14)
        )
        grant.refresh_from_db()
        assert grant.expires_at == grant.granted_at + timedelta(days=14)


class TestConsentWordingIsEvidence:
    """§7.7: what a person agreed to must be provable years later."""

    def test_the_body_of_a_consent_text_cannot_be_rewritten(self, consent_text) -> None:
        """Without this, one UPDATE retroactively changes what every person
        who ever signed that version is recorded as having agreed to."""
        with pytest.raises(IntegrityError), gov_cursor() as cursor:
            cursor.execute(
                "UPDATE consent_text_version SET body = 'something else' WHERE id = %s",
                [consent_text.id],
            )

    def test_the_checksum_cannot_be_rewritten(self, consent_text) -> None:
        with pytest.raises(IntegrityError), gov_cursor() as cursor:
            cursor.execute(
                "UPDATE consent_text_version SET checksum = %s WHERE id = %s",
                ["f" * 64, consent_text.id],
            )

    def test_a_consent_text_cannot_be_deleted(self, consent_text) -> None:
        with pytest.raises(IntegrityError), gov_cursor() as cursor:
            cursor.execute("DELETE FROM consent_text_version WHERE id = %s", [consent_text.id])

    def test_retiring_a_version_is_still_allowed(self, consent_text) -> None:
        """Retirement is forward-looking: it stops the wording being offered to
        anyone new without altering what anyone already agreed to."""
        ConsentTextVersion.objects.filter(pk=consent_text.pk).update(retired_at=timezone.now())
        consent_text.refresh_from_db()
        assert consent_text.retired_at is not None

    def test_an_entry_pins_the_hash_of_what_was_shown(self, consent_text) -> None:
        entry = ConsentEntry.objects.create(
            subject_token="st_abc",
            data_type=DataType.ORG,
            granted=True,
            consent_text=consent_text,
        )
        assert entry.consent_text_sha256 == consent_text.checksum
        assert entry.consent_text_is_unaltered


class TestRulesetProvenanceIsWriteOnce:
    """§10.5: who approved a ruleset, and what they approved, stay that way."""

    @pytest.fixture
    def ruleset(self) -> RulesetVersion:
        return RulesetVersion.objects.create(
            version="2026.03.1",
            digest="a" * 64,
            signature="sig",
            signing_key_id="ruleset-dev-1",
            approved_by_clinical="clinician-1",
            approved_by_wdec="wdec-1",
            approved_at=timezone.now(),
        )

    def test_the_digest_cannot_be_rewritten(self, ruleset) -> None:
        with pytest.raises(IntegrityError):
            RulesetVersion.objects.filter(pk=ruleset.pk).update(digest="b" * 64)

    def test_an_approval_cannot_be_reassigned(self, ruleset) -> None:
        with pytest.raises(IntegrityError):
            RulesetVersion.objects.filter(pk=ruleset.pk).update(approved_by_clinical="someone-else")

    def test_a_ruleset_cannot_be_deleted(self, ruleset) -> None:
        with pytest.raises(IntegrityError), gov_cursor() as cursor:
            cursor.execute("DELETE FROM ruleset_version WHERE id = %s", [ruleset.id])

    def test_a_ruleset_can_still_be_activated(self, ruleset) -> None:
        RulesetVersion.objects.filter(pk=ruleset.pk).update(activated_at=timezone.now())
        ruleset.refresh_from_db()
        assert ruleset.activated_at is not None


class TestAnAnchorDestinationIsWriteOnce:
    def test_a_published_destination_cannot_be_rewritten(self, audit_kwargs) -> None:
        from manobal_core.apps.governance.models import AuditEvent

        AuditEvent.record(**audit_kwargs)
        head = AuditEvent.objects.order_by("-id").first()
        assert head is not None
        anchor = AuditAnchor.objects.create(
            head_event_id=head.id,
            head_hash=head.row_hash,
            event_count=1,
            published_to="file:local-worm",
        )
        with pytest.raises(IntegrityError):
            AuditAnchor.objects.filter(pk=anchor.pk).update(published_to="somewhere-else")

    def test_an_empty_destination_can_be_completed(self, audit_kwargs) -> None:
        from manobal_core.apps.governance.models import AuditEvent

        AuditEvent.record(**audit_kwargs)
        head = AuditEvent.objects.order_by("-id").first()
        assert head is not None
        anchor = AuditAnchor.objects.create(
            head_event_id=head.id,
            head_hash=head.row_hash,
            event_count=1,
        )
        AuditAnchor.objects.filter(pk=anchor.pk).update(published_to="file:local-worm")
        anchor.refresh_from_db()
        assert anchor.published_to == "file:local-worm"
