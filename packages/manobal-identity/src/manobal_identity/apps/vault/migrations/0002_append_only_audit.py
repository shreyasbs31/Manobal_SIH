"""Database-level enforcement that the Zone 3 audit stream is append-only.

The ORM already refuses to update or delete a :class:`ResolutionAudit`. That
guard protects against a mistake in application code and nothing else — it is
bypassed by ``QuerySet.update()``, by a management shell, by a migration and by
anybody holding the database password.

This migration moves the guarantee to where it survives all of those. The chain
hashes make tampering *detectable*; these triggers make it *fail*. Both matter:
detection alone means the evidence and the crime live in the same table, under
the same credentials.
"""

from __future__ import annotations

from django.db import migrations

FORWARD = """
CREATE OR REPLACE FUNCTION manobal_identity_reject_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        'Table % is append-only (SDD 4.9, 7.3). Attempted % rejected.',
        TG_TABLE_NAME, TG_OP
        USING ERRCODE = 'integrity_constraint_violation';
END;
$$;

COMMENT ON FUNCTION manobal_identity_reject_mutation() IS
    'Refuses any UPDATE or DELETE. Every crossing of the identity boundary is '
    'evidence, and evidence that can be edited is not evidence.';

CREATE TRIGGER resolution_audit_no_update
    BEFORE UPDATE ON resolution_audit
    FOR EACH ROW EXECUTE FUNCTION manobal_identity_reject_mutation();

CREATE TRIGGER resolution_audit_no_delete
    BEFORE DELETE ON resolution_audit
    FOR EACH ROW EXECUTE FUNCTION manobal_identity_reject_mutation();

-- Verification, for the WDEC and for the nightly integrity job. Returns the
-- first sequence number whose recorded predecessor does not match the actual
-- predecessor's hash, or NULL when the chain is intact.
CREATE OR REPLACE FUNCTION manobal_identity_audit_chain_break()
RETURNS bigint
LANGUAGE sql
STABLE
AS $$
    SELECT seq
    FROM (
        SELECT seq,
               prev_hash,
               LAG(entry_hash) OVER (ORDER BY seq) AS actual_prev
        FROM resolution_audit
    ) AS chain
    WHERE prev_hash IS DISTINCT FROM COALESCE(actual_prev, repeat('0', 64))
    ORDER BY seq
    LIMIT 1;
$$;

COMMENT ON FUNCTION manobal_identity_audit_chain_break() IS
    'NULL when the Zone 3 audit chain is intact; otherwise the first seq at '
    'which it forks or was truncated.';
"""

REVERSE = """
DROP TRIGGER IF EXISTS resolution_audit_no_update ON resolution_audit;
DROP TRIGGER IF EXISTS resolution_audit_no_delete ON resolution_audit;
DROP FUNCTION IF EXISTS manobal_identity_audit_chain_break();
DROP FUNCTION IF EXISTS manobal_identity_reject_mutation();
"""


class Migration(migrations.Migration):
    dependencies = [("vault", "0001_initial")]

    operations = [migrations.RunSQL(sql=FORWARD, reverse_sql=REVERSE)]
