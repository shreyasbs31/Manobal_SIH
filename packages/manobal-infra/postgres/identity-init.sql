-- MANOBAL Zone 3 — the identity enclave. SDD §4.9, §5.1.
--
-- This cluster holds the only mapping between a subject_token and a person. It
-- runs on its own container, on an `internal` Docker network with no route to
-- anywhere, and publishes no host port. The only process that can reach it is
-- identity-resolver, which is the single container attached to both networks.
--
-- Note what is NOT in this file: manobal_core and manobal_risk. They do not
-- exist as roles here, so there is no password for them to leak and no grant for
-- an operator to widen by accident. SDD §7.1's fifth and sixth defence lines are
-- the reason the vault survives a compromise of the analytics plane.

\set ON_ERROR_STOP on

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE ROLE manobal_identity LOGIN PASSWORD 'dev_only_not_a_secret';

COMMENT ON ROLE manobal_identity IS
  'The identity-resolver service account. The only role in the system with any '
  'grant in this database.';

REVOKE ALL ON DATABASE iam_vault FROM PUBLIC;
GRANT CONNECT ON DATABASE iam_vault TO manobal_identity;

REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO manobal_identity;

-- Envelope encryption happens at the application layer before a value reaches
-- this database (NFR-SEC2), so a stolen dump of iam_vault is ciphertext without
-- the HSM key. The columns below are therefore bytea, not text: storing them as
-- text invites someone to "just check" a value in psql, and the type system
-- should make that awkward.
CREATE TABLE subject_identity (
    subject_token       text PRIMARY KEY,
    service_no_hmac     bytea NOT NULL UNIQUE,
    service_no_enc      bytea NOT NULL,
    full_name_enc       bytea NOT NULL,
    rank_code_enc       bytea NOT NULL,
    mobile_e164_enc     bytea NOT NULL,
    current_unit_id     uuid  NOT NULL,
    force_code          text  NOT NULL,
    enrolled_on         date  NOT NULL,
    separated_on        date,
    key_version         integer NOT NULL DEFAULT 1,
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE subject_identity IS
  'SDD §5.2 SUBJECT_IDENTITY. There is no foreign key from here to any analytics '
  'store, and none to here: the join is an authorised, logged runtime operation '
  'performed by exactly one service, never a database relationship.';
COMMENT ON COLUMN subject_identity.service_no_hmac IS
  'Blind index over the service number, so the ingest boundary can look up a '
  'token without the database ever seeing the plaintext. Keyed HMAC, not a bare '
  'hash — a bare hash of a service number is trivially rainbow-tabled.';
COMMENT ON COLUMN subject_identity.key_version IS
  'Envelope key generation, so a 90-day KMS rotation can proceed row by row.';

-- Both directions are indexed. SDD §5.3 is explicit that it is the *scope*, not
-- the index, that restricts direction: the ingest worker holds
-- manobal.identity.tokenise and the case path holds manobal.identity.resolve,
-- and they are different scopes with different rate limits and different audit
-- categories.
CREATE INDEX subject_identity_unit_idx ON subject_identity (current_unit_id);
CREATE INDEX subject_identity_separated_idx ON subject_identity (separated_on)
    WHERE separated_on IS NOT NULL;

-- Zone 3 keeps its own audit stream. If the analytics-plane audit log were the
-- only record of resolutions, an attacker who owned Zone 2 could resolve
-- identities and erase the evidence from the same position.
CREATE TABLE resolution_audit (
    id             bigserial PRIMARY KEY,
    occurred_at    timestamptz NOT NULL DEFAULT now(),
    direction      text NOT NULL CHECK (direction IN ('tokenise', 'resolve')),
    actor_id       text NOT NULL,
    actor_role     text NOT NULL,
    workload_id    text NOT NULL,
    subject_token  text,
    case_id        uuid,
    purpose_code   text NOT NULL,
    legal_basis    text NOT NULL,
    justification  text,
    break_glass    boolean NOT NULL DEFAULT false,
    granted        boolean NOT NULL,
    denial_reason  text,
    source_ip      inet
);

COMMENT ON TABLE resolution_audit IS
  'Every tokenise and every resolve, granted or denied. Written before the read '
  'it describes (SDD §5.4), so a crash cannot lose the audit record while '
  'completing the lookup.';

CREATE INDEX resolution_audit_actor_idx ON resolution_audit (actor_id, occurred_at DESC);
CREATE INDEX resolution_audit_time_idx  ON resolution_audit (occurred_at DESC);
-- The anomaly detector's hot path: SDD §6.5 caps resolve at 5/officer/hour and
-- treats a breach as a security incident, not a usage problem.
CREATE INDEX resolution_audit_resolve_idx ON resolution_audit (actor_id, occurred_at DESC)
    WHERE direction = 'resolve';

CREATE RULE resolution_audit_no_update AS ON UPDATE TO resolution_audit DO INSTEAD NOTHING;
CREATE RULE resolution_audit_no_delete AS ON DELETE TO resolution_audit DO INSTEAD NOTHING;

GRANT SELECT, INSERT, UPDATE, DELETE ON subject_identity TO manobal_identity;
GRANT SELECT, INSERT ON resolution_audit TO manobal_identity;
GRANT USAGE, SELECT ON SEQUENCE resolution_audit_id_seq TO manobal_identity;
