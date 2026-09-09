"""Database-level guards for the three governance records that had none.

Migration 0002 protected the audit log, the consent ledger, the anchors and the
assessments. Three tables that carry equally load-bearing governance facts were
left to application-level checks alone, and an application-level check is a
comment with a stack trace: it is bypassed by ``QuerySet.update()``, by a
management shell, by a data migration, and by anybody holding the database
password.

``access_grant``
    FR-5.4 gives a statutory 14-day ceiling on any grant of access to an
    individual's record. It was clamped in ``AccessGrant.save()``, which
    ``AccessGrant.objects.filter(...).update(expires_at=...)`` never calls. A
    standing grant is precisely what turns welfare into surveillance, so the
    ceiling belongs where every write path meets.

``consent_text_version``
    §7.7 promises that what a person agreed to is provable years later. An
    ``UPDATE`` here rewrites the wording that every linked consent entry points
    at, retroactively and silently, without touching the append-only
    ``consent_entry`` table at all.

``ruleset_version``
    §10.5 requires a WDEC auditor to be able to answer "which rules produced
    this flag, and who agreed to them?" months later. The approval and
    signature columns were editable, so the answer to the second half was
    whatever the last writer said it was.
"""

from __future__ import annotations

from django.db import migrations

FORWARD = """
-- FR-5.4: no grant may outlive its case, and none may exceed 14 days.
-- Expressed as a trigger rather than a CHECK because the ceiling is relative
-- to granted_at, and a CHECK cannot reference an interval of another column
-- in a way that survives an UPDATE to either one.
CREATE OR REPLACE FUNCTION manobal_enforce_grant_ceiling()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.expires_at > NEW.granted_at + INTERVAL '14 days' THEN
        RAISE EXCEPTION
            'MANOBAL: an access grant may not exceed 14 days (FR-5.4). '
            'Requested % from %, which is % beyond the ceiling.',
            NEW.expires_at, NEW.granted_at,
            NEW.expires_at - (NEW.granted_at + INTERVAL '14 days')
            USING ERRCODE = 'restrict_violation';
    END IF;
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION manobal_enforce_grant_ceiling() IS
    'FR-5.4 statutory ceiling on access grants, enforced for every write path '
    'rather than only the ones that go through the ORM save() method.';

CREATE TRIGGER access_grant_ceiling
    BEFORE INSERT OR UPDATE ON access_grant
    FOR EACH ROW EXECUTE FUNCTION manobal_enforce_grant_ceiling();

-- 7.7: the wording a person was shown is evidence, and evidence does not
-- change after the fact. Retiring a version is still allowed, because that is
-- a forward-looking act: it stops the text being offered to anyone new without
-- altering what anyone already agreed to.
CREATE OR REPLACE FUNCTION manobal_freeze_consent_text()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION
            'MANOBAL: consent_text_version is immutable (SDD 7.7); a wording '
            'that somebody agreed to may never be deleted.'
            USING ERRCODE = 'restrict_violation';
    END IF;

    IF NEW.version         IS DISTINCT FROM OLD.version
       OR NEW.language_code IS DISTINCT FROM OLD.language_code
       OR NEW.device_tier   IS DISTINCT FROM OLD.device_tier
       OR NEW.body          IS DISTINCT FROM OLD.body
       OR NEW.checksum      IS DISTINCT FROM OLD.checksum
       OR NEW.effective_from IS DISTINCT FROM OLD.effective_from
    THEN
        RAISE EXCEPTION
            'MANOBAL: consent_text_version is immutable (SDD 7.7). Only '
            'retired_at may change; publish a new version instead.'
            USING ERRCODE = 'restrict_violation';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER consent_text_version_frozen
    BEFORE UPDATE OR DELETE ON consent_text_version
    FOR EACH ROW EXECUTE FUNCTION manobal_freeze_consent_text();

-- 10.5: who approved a ruleset, and what they approved, are both fixed at the
-- moment of approval. The shadow report and the activation window are not, so
-- that a ruleset can be promoted and retired without reopening its provenance.
CREATE OR REPLACE FUNCTION manobal_freeze_ruleset_provenance()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION
            'MANOBAL: ruleset_version is a provenance record (SDD 10.5) and '
            'may not be deleted; assessments reference it by version.'
            USING ERRCODE = 'restrict_violation';
    END IF;

    IF NEW.digest    IS DISTINCT FROM OLD.digest
       OR NEW.signature IS DISTINCT FROM OLD.signature
       OR NEW.version   IS DISTINCT FROM OLD.version
    THEN
        RAISE EXCEPTION
            'MANOBAL: the identity of a ruleset (version, digest, signature) '
            'is fixed at publication (SDD 10.5).'
            USING ERRCODE = 'restrict_violation';
    END IF;

    -- Approvals are write-once rather than immutable: they start empty and are
    -- filled in when each approver signs off. What must not happen is an
    -- approval being changed to name somebody else, or quietly withdrawn after
    -- a ruleset has been used to flag people.
    IF (OLD.approved_by_clinical <> ''
        AND NEW.approved_by_clinical IS DISTINCT FROM OLD.approved_by_clinical)
       OR (OLD.approved_by_wdec <> ''
        AND NEW.approved_by_wdec IS DISTINCT FROM OLD.approved_by_wdec)
       OR (OLD.approved_at IS NOT NULL
        AND NEW.approved_at IS DISTINCT FROM OLD.approved_at)
    THEN
        RAISE EXCEPTION
            'MANOBAL: a recorded ruleset approval may not be reassigned or '
            'withdrawn (SDD 10.5). Supersede the ruleset instead.'
            USING ERRCODE = 'restrict_violation';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER ruleset_version_provenance
    BEFORE UPDATE OR DELETE ON ruleset_version
    FOR EACH ROW EXECUTE FUNCTION manobal_freeze_ruleset_provenance();

-- 7.3: an anchor's commitment is immutable, but where it was published is a
-- write-once completion of that record.
--
-- Migration 0002 made audit_anchor wholly append-only, which had an unintended
-- consequence: `published_to` could never be filled in, so the field that
-- records whether an anchor ever left the database was permanently empty and
-- the anchor mechanism was decorative. The fix is not to relax the table but to
-- name the one transition that must be possible — empty to non-empty, once.
CREATE OR REPLACE FUNCTION manobal_reject_anchor_edit()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION
            'MANOBAL: audit_anchor is append-only; DELETE is not permitted '
            '(SDD 7.3).'
            USING ERRCODE = 'restrict_violation';
    END IF;

    IF NEW.anchored_at    IS DISTINCT FROM OLD.anchored_at
       OR NEW.head_event_id IS DISTINCT FROM OLD.head_event_id
       OR NEW.head_hash     IS DISTINCT FROM OLD.head_hash
       OR NEW.event_count   IS DISTINCT FROM OLD.event_count
    THEN
        RAISE EXCEPTION
            'MANOBAL: an anchor commitment is immutable (SDD 7.3); only '
            'published_to may be completed after insert.'
            USING ERRCODE = 'restrict_violation';
    END IF;

    IF OLD.published_to <> '' AND NEW.published_to IS DISTINCT FROM OLD.published_to
    THEN
        RAISE EXCEPTION
            'MANOBAL: an anchor has already been published to %; the record of '
            'where it went may not be rewritten (SDD 7.3).', OLD.published_to
            USING ERRCODE = 'restrict_violation';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS audit_anchor_append_only ON audit_anchor;

CREATE TRIGGER audit_anchor_publish_once
    BEFORE UPDATE OR DELETE ON audit_anchor
    FOR EACH ROW EXECUTE FUNCTION manobal_reject_anchor_edit();
"""

REVERSE = """
DROP TRIGGER IF EXISTS access_grant_ceiling ON access_grant;
DROP TRIGGER IF EXISTS consent_text_version_frozen ON consent_text_version;
DROP TRIGGER IF EXISTS ruleset_version_provenance ON ruleset_version;
DROP TRIGGER IF EXISTS audit_anchor_publish_once ON audit_anchor;

CREATE TRIGGER audit_anchor_append_only
    BEFORE UPDATE OR DELETE ON audit_anchor
    FOR EACH ROW EXECUTE FUNCTION manobal_reject_mutation();

DROP FUNCTION IF EXISTS manobal_enforce_grant_ceiling();
DROP FUNCTION IF EXISTS manobal_freeze_consent_text();
DROP FUNCTION IF EXISTS manobal_freeze_ruleset_provenance();
DROP FUNCTION IF EXISTS manobal_reject_anchor_edit();
"""


class Migration(migrations.Migration):
    dependencies = [("governance", "0003_consent_text_hash")]

    operations = [migrations.RunSQL(sql=FORWARD, reverse_sql=REVERSE)]
