"""Create the isolated identity vault schema.

Revision ID: 0001_vault_foundation
Revises:
Create Date: 2026-09-16
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0001_vault_foundation"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SCHEMA_SQL = r"""
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE identity (
    token varchar(19) PRIMARY KEY CHECK (token ~ '^st_[a-z2-7]{16}$'),
    service_no_enc bytea NOT NULL,
    name_enc bytea NOT NULL,
    phone_enc bytea,
    posting_enc bytea,
    dek_wrapped bytea NOT NULL,
    kek_version text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE resolve_log (
    id bigserial PRIMARY KEY,
    token varchar(19) NOT NULL REFERENCES identity(token),
    requester text NOT NULL,
    case_id varchar(7) NOT NULL CHECK (case_id ~ '^MB-[0-9]{4}$'),
    purpose_code text NOT NULL,
    at timestamptz NOT NULL,
    hash char(64) NOT NULL UNIQUE,
    prev_hash char(64) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX ix_resolve_log_requester_at ON resolve_log (requester, at DESC);
CREATE INDEX ix_resolve_log_token_at ON resolve_log (token, at DESC);

CREATE TABLE nominee_store (
    token varchar(19) PRIMARY KEY REFERENCES identity(token) ON DELETE CASCADE,
    payload_enc bytea NOT NULL,
    dek_wrapped bytea NOT NULL,
    kek_version text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE OR REPLACE FUNCTION reject_vault_log_change()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'resolve log is append only';
END;
$$;

CREATE OR REPLACE FUNCTION append_resolve_log(
    p_token varchar,
    p_requester text,
    p_case_id varchar,
    p_purpose_code text,
    p_at timestamptz DEFAULT clock_timestamp()
)
RETURNS resolve_log
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    previous_hash text;
    next_hash text;
    canonical_entry jsonb;
    inserted resolve_log;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtext('manobal_resolve_chain'));
    SELECT hash::text
      INTO previous_hash
      FROM resolve_log
     ORDER BY id DESC
     LIMIT 1;
    previous_hash := COALESCE(previous_hash, repeat('0', 64));
    canonical_entry := jsonb_build_object(
        'token', p_token,
        'requester', p_requester,
        'case_id', p_case_id,
        'purpose_code', p_purpose_code,
        'at', p_at
    );
    next_hash := encode(
        digest(
            convert_to(previous_hash || canonical_entry::text, 'UTF8'),
            'sha256'
        ),
        'hex'
    );
    INSERT INTO resolve_log (
        token, requester, case_id, purpose_code, at, hash, prev_hash
    )
    VALUES (
        p_token, p_requester, p_case_id, p_purpose_code, p_at,
        next_hash, previous_hash
    )
    RETURNING * INTO inserted;
    RETURN inserted;
END;
$$;

CREATE OR REPLACE FUNCTION verify_resolve_chain()
RETURNS TABLE (
    valid boolean,
    checked bigint,
    broken_id bigint,
    head_hash text
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    row_value resolve_log%ROWTYPE;
    previous_hash text := repeat('0', 64);
    expected_hash text;
    canonical_entry jsonb;
    checked_count bigint := 0;
BEGIN
    FOR row_value IN SELECT * FROM resolve_log ORDER BY id LOOP
        canonical_entry := jsonb_build_object(
            'token', row_value.token,
            'requester', row_value.requester,
            'case_id', row_value.case_id,
            'purpose_code', row_value.purpose_code,
            'at', row_value.at
        );
        expected_hash := encode(
            digest(
                convert_to(previous_hash || canonical_entry::text, 'UTF8'),
                'sha256'
            ),
            'hex'
        );
        checked_count := checked_count + 1;
        IF row_value.prev_hash::text <> previous_hash
           OR row_value.hash::text <> expected_hash THEN
            RETURN QUERY
            SELECT false, checked_count, row_value.id, previous_hash;
            RETURN;
        END IF;
        previous_hash := row_value.hash::text;
    END LOOP;
    RETURN QUERY SELECT true, checked_count, NULL::bigint, previous_hash;
END;
$$;

CREATE TRIGGER resolve_log_immutable
BEFORE UPDATE OR DELETE ON resolve_log
FOR EACH ROW EXECUTE FUNCTION reject_vault_log_change();

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vault_app') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public
            TO vault_app;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO vault_app;
        GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO vault_app;
        REVOKE INSERT, UPDATE, DELETE ON resolve_log FROM vault_app;
        GRANT EXECUTE ON FUNCTION append_resolve_log(
            varchar, text, varchar, text, timestamptz
        ) TO vault_app;
        GRANT EXECUTE ON FUNCTION verify_resolve_chain() TO vault_app;
    END IF;
END
$$;
"""


def upgrade() -> None:
    op.execute(SCHEMA_SQL)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS verify_resolve_chain()")
    op.execute(
        "DROP FUNCTION IF EXISTS append_resolve_log(varchar, text, varchar, text, timestamptz)"
    )
    op.execute("DROP FUNCTION IF EXISTS reject_vault_log_change() CASCADE")
    op.execute("DROP TABLE IF EXISTS nominee_store")
    op.execute("DROP TABLE IF EXISTS resolve_log")
    op.execute("DROP TABLE IF EXISTS identity")
