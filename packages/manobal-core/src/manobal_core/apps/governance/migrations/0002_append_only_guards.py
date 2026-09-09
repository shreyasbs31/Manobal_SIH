"""Database-level enforcement of the append-only tables (SDD §5.2, §7.3).

The Python ``save()`` overrides on these models catch honest mistakes. They do
nothing about a management command using ``queryset.update()``, an ORM-bypassing
raw query, or a well-meaning data migration — all of which reach the table
without ever calling ``save()``. These triggers close that gap: the guarantee
belongs to the database, where every write path necessarily passes.

What this does not claim: a superuser can ``ALTER TABLE ... DISABLE TRIGGER``.
That is unavoidable and is why the audit chain is hashed and anchored as well as
trigger-protected. The trigger makes tampering deliberate; the hash chain makes
it detectable.
"""

from __future__ import annotations

from django.db import migrations

APPEND_ONLY_FN = """
CREATE OR REPLACE FUNCTION manobal_reject_mutation() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        'MANOBAL: % is append-only; % is not permitted (SDD 5.2)',
        TG_TABLE_NAME, TG_OP
        USING ERRCODE = 'restrict_violation';
END;
$$ LANGUAGE plpgsql;
"""

# An assessment is frozen except for the back-link that a *later* assessment
# writes to mark it superseded. Comparing the two rows column by column would be
# brittle; blanking the one mutable column and comparing the remainder is exact
# and stays correct as columns are added.
ASSESSMENT_FN = """
CREATE OR REPLACE FUNCTION manobal_reject_assessment_edit() RETURNS TRIGGER AS $$
DECLARE
    before_row risk_assessment;
    after_row  risk_assessment;
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION
            'MANOBAL: risk assessments are immutable and cannot be deleted (FR-3.9)'
            USING ERRCODE = 'restrict_violation';
    END IF;

    before_row := OLD;
    after_row  := NEW;
    before_row.superseded_by_id := NULL;
    after_row.superseded_by_id  := NULL;

    IF before_row IS DISTINCT FROM after_row THEN
        RAISE EXCEPTION
            'MANOBAL: risk assessments are immutable; write a new assessment (FR-3.9)'
            USING ERRCODE = 'restrict_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

TRIGGERS = """
CREATE TRIGGER audit_event_append_only
    BEFORE UPDATE OR DELETE ON audit_event
    FOR EACH ROW EXECUTE FUNCTION manobal_reject_mutation();

CREATE TRIGGER consent_entry_append_only
    BEFORE UPDATE OR DELETE ON consent_entry
    FOR EACH ROW EXECUTE FUNCTION manobal_reject_mutation();

CREATE TRIGGER audit_anchor_append_only
    BEFORE UPDATE OR DELETE ON audit_anchor
    FOR EACH ROW EXECUTE FUNCTION manobal_reject_mutation();

CREATE TRIGGER risk_assessment_immutable
    BEFORE UPDATE OR DELETE ON risk_assessment
    FOR EACH ROW EXECUTE FUNCTION manobal_reject_assessment_edit();
"""

DROP = """
DROP TRIGGER IF EXISTS audit_event_append_only ON audit_event;
DROP TRIGGER IF EXISTS consent_entry_append_only ON consent_entry;
DROP TRIGGER IF EXISTS audit_anchor_append_only ON audit_anchor;
DROP TRIGGER IF EXISTS risk_assessment_immutable ON risk_assessment;
DROP FUNCTION IF EXISTS manobal_reject_mutation();
DROP FUNCTION IF EXISTS manobal_reject_assessment_edit();
"""

# The chain is only worth something if somebody checks it. This runs the whole
# verification in one pass inside the database rather than streaming every audit
# row to the application, which matters once the table holds years of history
# under the seven-year retention rule.
VERIFY_FN = """
CREATE OR REPLACE FUNCTION manobal_audit_chain_break()
RETURNS TABLE (broken_at BIGINT, expected TEXT, found TEXT) AS $$
    SELECT id, expected_prev, prev_hash
    FROM (
        SELECT
            id,
            prev_hash,
            COALESCE(
                LAG(row_hash) OVER (ORDER BY id),
                repeat('0', 64)
            ) AS expected_prev
        FROM audit_event
    ) AS chain
    WHERE prev_hash IS DISTINCT FROM expected_prev
    ORDER BY id
    LIMIT 1;
$$ LANGUAGE sql STABLE;
"""

DROP_VERIFY = "DROP FUNCTION IF EXISTS manobal_audit_chain_break();"


class Migration(migrations.Migration):
    dependencies = [("governance", "0001_initial")]

    operations = [
        migrations.RunSQL(sql=APPEND_ONLY_FN, reverse_sql=migrations.RunSQL.noop),
        migrations.RunSQL(sql=ASSESSMENT_FN, reverse_sql=migrations.RunSQL.noop),
        migrations.RunSQL(sql=TRIGGERS, reverse_sql=DROP),
        migrations.RunSQL(sql=VERIFY_FN, reverse_sql=DROP_VERIFY),
    ]
