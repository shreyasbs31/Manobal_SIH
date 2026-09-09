-- MANOBAL Zone 3 — the identity enclave. SDD §4.9, §5.1.
--
-- This cluster holds the only mapping between a subject_token and a person. It
-- listens on its own port with its own pg_hba.conf, and the only role that can
-- authenticate to it is manobal_identity.
--
-- Note what is NOT in this file: manobal_core and manobal_risk. They do not
-- exist as roles here, so there is no password for them to leak and no grant for
-- an operator to widen by accident. SDD §7.1's fifth and sixth defence lines are
-- the reason the vault survives a compromise of the analytics plane.
--
-- Note also what is no longer in this file: the tables. Schema is owned by the
-- Django migrations in manobal_identity/apps/vault/migrations, so there is one
-- source of truth for the vault's shape rather than two that can drift. This
-- script sets up everything a migration cannot: the extension, the role, and
-- the database-level grants that must exist before the first `migrate` runs.

\set ON_ERROR_STOP on

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE ROLE manobal_identity LOGIN PASSWORD 'dev_only_not_a_secret';

COMMENT ON ROLE manobal_identity IS
  'The identity-resolver service account. The only role in the system with any '
  'grant in this database.';

REVOKE ALL ON DATABASE iam_vault FROM PUBLIC;
GRANT CONNECT ON DATABASE iam_vault TO manobal_identity;

-- The service owns its schema so that `manage.py migrate` can create and alter
-- its own tables. In production this is split: a separate migration role holds
-- DDL rights and the runtime role holds only DML, so a compromise of the
-- running service cannot reshape the vault or drop the audit triggers. That
-- split is deliberately not modelled locally, where one developer plays both
-- parts and the ceremony would only obscure the intent.
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO manobal_identity;
ALTER SCHEMA public OWNER TO manobal_identity;

-- Envelope encryption happens at the application layer before a value reaches
-- this database (NFR-SEC2), so a stolen dump of iam_vault is ciphertext without
-- the KMS key. The identifying columns are therefore bytea, not text: storing
-- them as text invites someone to "just check" a value in psql, and the type
-- system should make that awkward.
--
-- There is no foreign key from this database to any analytics store, and none
-- back. Per §5.1 the join is a deliberate, authorised, logged runtime operation
-- performed by exactly one service — never a database relationship. A DBA with
-- full access to the analytics cluster still cannot name a single person.
