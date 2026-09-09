-- MANOBAL Zone 2 — the analytics plane. SDD §5.1 store separation.
--
-- Five databases, not five schemas. The distinction matters: PostgreSQL cannot
-- join across databases, so "no cross-store join" stops being a rule people have
-- to remember and becomes a thing the engine will not do. SDD §5.1 puts it
-- plainly — a DBA with full access to this cluster still cannot name a single
-- person, because the names are on a different cluster on a different network.
--
-- Roles are least-privilege by construction:
--
--   manobal_core   owns the schemas, runs migrations, serves the API
--   manobal_risk   reads the four signal stores, writes only assessments
--   manobal_wdec   reads audit and aggregate tables, and nothing else
--
-- None of them exists on the identity cluster. That is not an omission.

\set ON_ERROR_STOP on

-- ---------------------------------------------------------------- roles ----
CREATE ROLE manobal_core  LOGIN PASSWORD 'dev_only_not_a_secret';
CREATE ROLE manobal_risk  LOGIN PASSWORD 'dev_only_not_a_secret';
CREATE ROLE manobal_wdec  LOGIN PASSWORD 'dev_only_not_a_secret';

COMMENT ON ROLE manobal_core IS
  'Zone 2 API and workers. Owns every analytics schema. Holds no credential for iam_vault.';
COMMENT ON ROLE manobal_risk IS
  'Zone 2 risk engine. Reads signal stores, writes assessments. SDD §9.6 asserts it '
  'holds no grant on iam_vault and no identity:resolve scope.';
COMMENT ON ROLE manobal_wdec IS
  'Independent oversight. Audit trails and aggregate metrics only, never personnel content.';

-- ------------------------------------------------------------ databases ----
CREATE DATABASE org_store   OWNER manobal_core;
CREATE DATABASE psy_store   OWNER manobal_core;
CREATE DATABASE bio_store   OWNER manobal_core;
CREATE DATABASE voice_store OWNER manobal_core;
CREATE DATABASE gov_store   OWNER manobal_core;

COMMENT ON DATABASE org_store   IS 'Derived organisational indicators, keyed by subject_token. Never raw HR records.';
COMMENT ON DATABASE psy_store   IS 'Instrument scores, EMA, opt-in journal. Item-level responses are column-encrypted.';
COMMENT ON DATABASE bio_store   IS 'Wearable time series. TimescaleDB hypertables, 7-day chunks.';
COMMENT ON DATABASE voice_store IS 'eGeMAPS feature vectors and derived tags. No audio. No transcript. Ever.';
COMMENT ON DATABASE gov_store   IS 'Consent ledger, hash-chained audit, access grants, cases, alerts, assessments.';

-- Deny by default, then grant. The four signal stores are readable by the risk
-- engine; gov_store is where it writes its output.
REVOKE ALL ON DATABASE org_store, psy_store, bio_store, voice_store, gov_store FROM PUBLIC;

GRANT CONNECT ON DATABASE org_store, psy_store, bio_store, voice_store, gov_store TO manobal_core;
GRANT CONNECT ON DATABASE org_store, psy_store, bio_store, voice_store, gov_store TO manobal_risk;
GRANT CONNECT ON DATABASE gov_store TO manobal_wdec;

-- ---------------------------------------------- per-database bootstrap ----
-- Applied identically to the four read-only-for-risk signal stores.

\connect org_store
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT ALL   ON SCHEMA public TO manobal_core;
GRANT USAGE ON SCHEMA public TO manobal_risk;
ALTER DEFAULT PRIVILEGES FOR ROLE manobal_core IN SCHEMA public
  GRANT SELECT ON TABLES TO manobal_risk;
ALTER DEFAULT PRIVILEGES FOR ROLE manobal_core IN SCHEMA public
  GRANT SELECT ON SEQUENCES TO manobal_risk;

\connect psy_store
CREATE EXTENSION IF NOT EXISTS pgcrypto;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT ALL   ON SCHEMA public TO manobal_core;
GRANT USAGE ON SCHEMA public TO manobal_risk;
ALTER DEFAULT PRIVILEGES FOR ROLE manobal_core IN SCHEMA public
  GRANT SELECT ON TABLES TO manobal_risk;

-- bio_store and voice_store are created here so that the store topology is
-- complete and the grants are in place, but they carry no tables yet: bio_store
-- needs TimescaleDB for its hypertables (NFR-S3) and voice_store needs pgvector
-- for the 88-dimensional eGeMAPS functionals. Both extensions are applied by
-- analytics-extensions.sql where they are available. Until then the D4
-- physiological and D6 vocal-acoustic domains simply have no data, and coverage
-- renormalisation (FR-3.3) handles their absence exactly as it handles a subject
-- who declined to wear a device.

\connect bio_store
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT ALL   ON SCHEMA public TO manobal_core;
GRANT USAGE ON SCHEMA public TO manobal_risk;
ALTER DEFAULT PRIVILEGES FOR ROLE manobal_core IN SCHEMA public
  GRANT SELECT ON TABLES TO manobal_risk;

\connect voice_store
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT ALL   ON SCHEMA public TO manobal_core;
GRANT USAGE ON SCHEMA public TO manobal_risk;
ALTER DEFAULT PRIVILEGES FOR ROLE manobal_core IN SCHEMA public
  GRANT SELECT ON TABLES TO manobal_risk;

\connect gov_store
CREATE EXTENSION IF NOT EXISTS pgcrypto;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT ALL   ON SCHEMA public TO manobal_core;
GRANT USAGE ON SCHEMA public TO manobal_risk;
GRANT USAGE ON SCHEMA public TO manobal_wdec;

-- The risk engine reads consent and baselines and writes assessments. It gets no
-- UPDATE and no DELETE anywhere: an assessment is an immutable record of a
-- decision (FR-3.9), and a component that cannot rewrite history is easier to
-- trust than one that promises not to.
ALTER DEFAULT PRIVILEGES FOR ROLE manobal_core IN SCHEMA public
  GRANT SELECT, INSERT ON TABLES TO manobal_risk;
ALTER DEFAULT PRIVILEGES FOR ROLE manobal_core IN SCHEMA public
  GRANT SELECT ON TABLES TO manobal_wdec;
