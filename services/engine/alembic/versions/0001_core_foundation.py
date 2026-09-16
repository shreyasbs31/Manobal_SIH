"""Create the token-only core schema.

Revision ID: 0001_core_foundation
Revises:
Create Date: 2026-09-16
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0001_core_foundation"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SCHEMA_SQL = r"""
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS ltree;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE unit (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    path ltree NOT NULL UNIQUE,
    name text NOT NULL,
    level text NOT NULL,
    theatre text,
    climate_class text,
    altitude_class text,
    parent_id uuid REFERENCES unit(id),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX ix_unit_path_gist ON unit USING gist (path);

CREATE TABLE subject (
    token varchar(19) PRIMARY KEY CHECK (token ~ '^st_[a-z2-7]{16}$'),
    unit_path ltree NOT NULL REFERENCES unit(path),
    rank_band text NOT NULL,
    tenure_band text NOT NULL,
    enrolled boolean NOT NULL DEFAULT false,
    device_tier text NOT NULL,
    lifecycle_state text NOT NULL,
    lifecycle_since timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX ix_subject_unit_path ON subject USING gist (unit_path);

CREATE TABLE subject_audit_attrs (
    token varchar(19) PRIMARY KEY REFERENCES subject(token) ON DELETE CASCADE,
    gender text NOT NULL,
    home_region text NOT NULL,
    language text NOT NULL,
    sector text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE officer (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    entra_oid text NOT NULL UNIQUE,
    display_label text NOT NULL,
    role text NOT NULL CHECK (
        role IN (
            'uwo', 'counsellor', 'mo', 'commander', 'hq', 'wdec',
            'dpo', 'hrms_integrator', 'admin', 'director'
        )
    ),
    unit_path ltree NOT NULL,
    valid_from timestamptz NOT NULL,
    valid_to timestamptz,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CHECK (valid_to IS NULL OR valid_to > valid_from)
);
CREATE INDEX ix_officer_unit_path ON officer USING gist (unit_path);
CREATE INDEX ix_officer_active_assignment ON officer (role, valid_from, valid_to);

CREATE TABLE buddy_pair (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    token_a varchar(19) NOT NULL REFERENCES subject(token) ON DELETE CASCADE,
    token_b varchar(19) NOT NULL REFERENCES subject(token) ON DELETE CASCADE,
    unit_path ltree NOT NULL,
    since timestamptz NOT NULL,
    active boolean NOT NULL DEFAULT true,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CHECK (token_a <> token_b),
    UNIQUE (token_a, token_b)
);

CREATE TABLE consent_ledger (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    token varchar(19) NOT NULL REFERENCES subject(token) ON DELETE CASCADE,
    data_type text NOT NULL CHECK (
        data_type IN (
            'hr_derived', 'self_report', 'wearable', 'voice_features',
            'ai_conversation', 'trend_share', 'buddy', 'family_line'
        )
    ),
    purpose text NOT NULL,
    action text NOT NULL CHECK (action IN ('grant', 'withdraw')),
    text_hash char(64) NOT NULL,
    lang text NOT NULL,
    app_version text NOT NULL,
    at timestamptz NOT NULL,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX ix_consent_ledger_token_at ON consent_ledger (token, at DESC);

CREATE TABLE consent_receipt (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    token varchar(19) NOT NULL REFERENCES subject(token) ON DELETE CASCADE,
    ledger_ids uuid[] NOT NULL,
    sha256 char(64) NOT NULL,
    signature bytea NOT NULL,
    at timestamptz NOT NULL,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE rights_request (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    token varchar(19) NOT NULL REFERENCES subject(token) ON DELETE CASCADE,
    kind text NOT NULL CHECK (
        kind IN ('access', 'correction', 'erasure', 'grievance', 'nomination')
    ),
    status text NOT NULL,
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    opened_at timestamptz NOT NULL,
    due_at timestamptz NOT NULL,
    closed_at timestamptz,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX ix_rights_request_status_due ON rights_request (status, due_at);

CREATE TABLE nominee (
    token varchar(19) PRIMARY KEY REFERENCES subject(token) ON DELETE CASCADE,
    nominee_name_enc bytea NOT NULL,
    relation text NOT NULL,
    contact_enc bytea NOT NULL,
    at timestamptz NOT NULL,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE erasure_receipt (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    token varchar(19) NOT NULL REFERENCES subject(token) ON DELETE CASCADE,
    data_type text NOT NULL,
    row_count bigint NOT NULL CHECK (row_count >= 0),
    sha256 char(64) NOT NULL,
    signature bytea NOT NULL,
    at timestamptz NOT NULL,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE breach_register (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    detected_at timestamptz NOT NULL,
    description text NOT NULL,
    affected_count bigint NOT NULL CHECK (affected_count >= 0),
    board_notified_at timestamptz,
    users_notified_at timestamptz,
    status text NOT NULL,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE notice_version (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    lang text NOT NULL,
    text_hash char(64) NOT NULL,
    published_at timestamptz NOT NULL,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (lang, text_hash)
);

CREATE TABLE duty_day (
    token varchar(19) NOT NULL REFERENCES subject(token) ON DELETE CASCADE,
    date date NOT NULL,
    hours numeric(5,2) NOT NULL CHECK (hours >= 0 AND hours <= 24),
    shift_start time,
    night boolean NOT NULL DEFAULT false,
    rest_day boolean NOT NULL DEFAULT false,
    rest_denied boolean NOT NULL DEFAULT false,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (token, date)
);

CREATE TABLE leave_balance (
    token varchar(19) NOT NULL REFERENCES subject(token) ON DELETE CASCADE,
    as_of date NOT NULL,
    el_days numeric(6,2) NOT NULL,
    cl_days numeric(6,2) NOT NULL,
    other jsonb NOT NULL DEFAULT '{}'::jsonb,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (token, as_of)
);

CREATE TABLE leave_event (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    token varchar(19) NOT NULL REFERENCES subject(token) ON DELETE CASCADE,
    type text NOT NULL CHECK (type IN ('EL', 'CL', 'HPL', 'emergency')),
    applied_at timestamptz NOT NULL,
    from_date date NOT NULL,
    to_date date NOT NULL,
    status text NOT NULL,
    reason_code text,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CHECK (to_date >= from_date)
);
CREATE INDEX ix_leave_event_token_applied ON leave_event (token, applied_at DESC);

CREATE TABLE org_event (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    token varchar(19) NOT NULL REFERENCES subject(token) ON DELETE CASCADE,
    type text NOT NULL CHECK (
        type IN (
            'transfer_request', 'duty_swap', 'training', 'grievance',
            'posting_change'
        )
    ),
    at timestamptz NOT NULL,
    meta jsonb NOT NULL DEFAULT '{}'::jsonb,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX ix_org_event_token_at ON org_event (token, at DESC);

CREATE TABLE deployment_event (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    unit_path ltree NOT NULL,
    type text NOT NULL CHECK (
        type IN ('induction', 'de_induction', 'operation_start', 'operation_end')
    ),
    at timestamptz NOT NULL,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX ix_deployment_event_unit_path ON deployment_event USING gist (unit_path);

CREATE TABLE incident (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    unit_path ltree NOT NULL,
    type text NOT NULL CHECK (
        type IN (
            'encounter', 'ied', 'casualty', 'colleague_death', 'accident',
            'disaster'
        )
    ),
    occurred_at timestamptz NOT NULL,
    severity smallint NOT NULL CHECK (severity BETWEEN 1 AND 5),
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX ix_incident_unit_path ON incident USING gist (unit_path);

CREATE TABLE ema (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    token varchar(19) NOT NULL REFERENCES subject(token) ON DELETE CASCADE,
    at timestamptz NOT NULL,
    mood smallint NOT NULL CHECK (mood BETWEEN 1 AND 5),
    energy smallint NOT NULL CHECK (energy BETWEEN 1 AND 5),
    sleep_quality smallint NOT NULL CHECK (sleep_quality BETWEEN 1 AND 5),
    sleep_hours numeric(4,2) CHECK (sleep_hours >= 0 AND sleep_hours <= 24),
    tags text[] NOT NULL DEFAULT '{}',
    source text NOT NULL CHECK (source IN ('app', 'voice', 'ivr')),
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX ix_ema_token_at ON ema (token, at DESC);

CREATE TABLE instrument (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    token varchar(19) NOT NULL REFERENCES subject(token) ON DELETE CASCADE,
    at timestamptz NOT NULL,
    kind text NOT NULL,
    items jsonb NOT NULL,
    total numeric,
    lang text NOT NULL,
    validated boolean NOT NULL DEFAULT false,
    visibility text NOT NULL CHECK (visibility IN ('shared', 'self_only')),
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX ix_instrument_token_at ON instrument (token, at DESC);

CREATE TABLE bio_day (
    token varchar(19) NOT NULL REFERENCES subject(token) ON DELETE CASCADE,
    date date NOT NULL,
    sleep_min integer CHECK (sleep_min >= 0),
    sleep_eff numeric(5,2),
    rhr numeric(6,2),
    hrv_rmssd numeric(8,2),
    steps integer CHECK (steps >= 0),
    spo2 numeric(5,2),
    wear_minutes integer CHECK (wear_minutes >= 0),
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (token, date)
);

CREATE TABLE voice_features (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    token varchar(19) NOT NULL REFERENCES subject(token) ON DELETE CASCADE,
    at timestamptz NOT NULL,
    egemaps real[] NOT NULL CHECK (array_length(egemaps, 1) = 88),
    duration_s numeric(8,3) NOT NULL CHECK (duration_s > 0),
    lang text NOT NULL,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX ix_voice_features_token_at ON voice_features (token, at DESC);

CREATE TABLE engagement_day (
    token varchar(19) NOT NULL REFERENCES subject(token) ON DELETE CASCADE,
    date date NOT NULL,
    expected integer NOT NULL CHECK (expected >= 0),
    completed integer NOT NULL CHECK (completed >= 0),
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (token, date)
);

CREATE TABLE climate_pulse (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    unit_path ltree NOT NULL,
    week date NOT NULL,
    question_id text NOT NULL,
    response_bucket text NOT NULL,
    n integer NOT NULL CHECK (n >= 0),
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (unit_path, week, question_id, response_bucket)
);
CREATE INDEX ix_climate_pulse_unit_path ON climate_pulse USING gist (unit_path);

CREATE TABLE grievance (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    token_hash char(64) NOT NULL,
    unit_path ltree NOT NULL,
    category text NOT NULL CHECK (
        category IN (
            'leave', 'pay', 'housing', 'transfer', 'family', 'land_property',
            'medical_admin', 'colleagues', 'other'
        )
    ),
    text_enc bytea,
    status text NOT NULL,
    sla_due timestamptz NOT NULL,
    opened_at timestamptz NOT NULL,
    closed_at timestamptz,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX ix_grievance_unit_path ON grievance USING gist (unit_path);
CREATE INDEX ix_grievance_status_sla ON grievance (status, sla_due);

CREATE TABLE indicator_day (
    token varchar(19) NOT NULL REFERENCES subject(token) ON DELETE CASCADE,
    date date NOT NULL,
    indicator text NOT NULL,
    value double precision,
    seasonal_adj_value double precision,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (token, date, indicator)
);

CREATE TABLE regime (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    token varchar(19) NOT NULL REFERENCES subject(token) ON DELETE CASCADE,
    started_at timestamptz NOT NULL,
    reason text NOT NULL CHECK (
        reason IN ('posting_change', 'induction', 'return_from_leave', 'initial')
    ),
    warmup_until timestamptz NOT NULL,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX ix_regime_token_started ON regime (token, started_at DESC);

CREATE TABLE baseline (
    token varchar(19) NOT NULL REFERENCES subject(token) ON DELETE CASCADE,
    indicator text NOT NULL,
    regime_id uuid NOT NULL REFERENCES regime(id) ON DELETE CASCADE,
    median double precision NOT NULL,
    mad double precision NOT NULL CHECK (mad >= 0),
    n integer NOT NULL CHECK (n >= 0),
    window_end date NOT NULL,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (token, indicator, regime_id)
);

CREATE TABLE domain_score (
    token varchar(19) NOT NULL REFERENCES subject(token) ON DELETE CASCADE,
    date date NOT NULL,
    domain text NOT NULL,
    z double precision NOT NULL,
    ewma double precision NOT NULL,
    cusum double precision NOT NULL,
    coverage double precision NOT NULL CHECK (coverage BETWEEN 0 AND 1),
    breached boolean NOT NULL,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (token, date, domain)
);

CREATE TABLE assessment (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    token varchar(19) NOT NULL REFERENCES subject(token) ON DELETE CASCADE,
    date date NOT NULL,
    wsi double precision NOT NULL,
    raw_tier text NOT NULL CHECK (raw_tier IN ('T0', 'T1', 'T2', 'T3', 'T4')),
    final_tier text NOT NULL CHECK (final_tier IN ('T0', 'T1', 'T2', 'T3', 'T4')),
    corroborating_domains text[] NOT NULL DEFAULT '{}',
    trajectory text NOT NULL CHECK (trajectory IN ('rising', 'stable', 'falling')),
    forecast_p double precision CHECK (forecast_p BETWEEN 0 AND 1),
    forecast_lo double precision CHECK (forecast_lo BETWEEN 0 AND 1),
    forecast_hi double precision CHECK (forecast_hi BETWEEN 0 AND 1),
    drivers jsonb NOT NULL DEFAULT '[]'::jsonb,
    onset_date date,
    limited_data boolean NOT NULL,
    ruleset_version text NOT NULL,
    model_version text NOT NULL,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (token, date, ruleset_version)
);
CREATE INDEX ix_assessment_token_date ON assessment (token, date DESC);
CREATE INDEX ix_assessment_final_tier_date ON assessment (final_tier, date DESC);

CREATE TABLE shadow_assessment (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    token varchar(19) NOT NULL REFERENCES subject(token) ON DELETE CASCADE,
    date date NOT NULL,
    wsi double precision NOT NULL,
    raw_tier text NOT NULL CHECK (raw_tier IN ('T0', 'T1', 'T2', 'T3', 'T4')),
    final_tier text NOT NULL CHECK (final_tier IN ('T0', 'T1', 'T2', 'T3', 'T4')),
    corroborating_domains text[] NOT NULL DEFAULT '{}',
    trajectory text NOT NULL CHECK (trajectory IN ('rising', 'stable', 'falling')),
    forecast_p double precision CHECK (forecast_p BETWEEN 0 AND 1),
    forecast_lo double precision CHECK (forecast_lo BETWEEN 0 AND 1),
    forecast_hi double precision CHECK (forecast_hi BETWEEN 0 AND 1),
    drivers jsonb NOT NULL DEFAULT '[]'::jsonb,
    onset_date date,
    limited_data boolean NOT NULL,
    ruleset_version text NOT NULL,
    model_version text NOT NULL,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (token, date, ruleset_version)
);

CREATE TABLE nudge (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    token varchar(19) NOT NULL REFERENCES subject(token) ON DELETE CASCADE,
    kind text NOT NULL,
    reason_codes text[] NOT NULL DEFAULT '{}',
    trigger text NOT NULL,
    shown_at timestamptz,
    dismissed_at timestamptz,
    feedback text,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE jitai_log (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    token varchar(19) NOT NULL REFERENCES subject(token) ON DELETE CASCADE,
    rule_id text NOT NULL,
    fired_at timestamptz NOT NULL,
    delivered boolean NOT NULL,
    suppressed_reason text,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE "case" (
    id varchar(7) PRIMARY KEY CHECK (id ~ '^MB-[0-9]{4}$'),
    token varchar(19) NOT NULL REFERENCES subject(token),
    unit_path ltree NOT NULL,
    tier text NOT NULL CHECK (tier IN ('T2', 'T3', 'T4')),
    status text NOT NULL,
    opened_at timestamptz NOT NULL,
    sla_due_at timestamptz NOT NULL,
    assigned_uwo uuid REFERENCES officer(id),
    dominant_domains text[] NOT NULL DEFAULT '{}',
    recommended jsonb NOT NULL DEFAULT '[]'::jsonb,
    source text NOT NULL CHECK (
        source IN ('engine', 'incident', 'self_referral', 'acute')
    ),
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX ix_case_unit_path ON "case" USING gist (unit_path);
CREATE INDEX ix_case_status_sla ON "case" (status, sla_due_at);

CREATE TABLE case_action (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id varchar(7) NOT NULL REFERENCES "case"(id) ON DELETE CASCADE,
    actor text NOT NULL,
    kind text NOT NULL CHECK (
        kind IN ('note', 'decision', 'contact', 'referral', 'followup', 'outcome')
    ),
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    at timestamptz NOT NULL,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX ix_case_action_case_at ON case_action (case_id, at DESC);

CREATE TABLE case_grant (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id varchar(7) NOT NULL REFERENCES "case"(id) ON DELETE CASCADE,
    actor text NOT NULL,
    purpose_code text NOT NULL,
    justification text NOT NULL,
    granted_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz,
    contact_note_due_at timestamptz NOT NULL,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CHECK (expires_at > granted_at)
);
CREATE INDEX ix_case_grant_actor_expiry ON case_grant (actor, expires_at);

CREATE TABLE breakglass (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    actor text NOT NULL,
    approver text NOT NULL,
    target_token varchar(19) NOT NULL REFERENCES subject(token),
    justification text NOT NULL,
    at timestamptz NOT NULL,
    wdec_review_status text NOT NULL,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CHECK (actor <> approver)
);

CREATE TABLE consent_request (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id varchar(7) NOT NULL REFERENCES "case"(id) ON DELETE CASCADE,
    token varchar(19) NOT NULL REFERENCES subject(token),
    kind text NOT NULL CHECK (kind = 'trend_share'),
    domain text NOT NULL,
    status text NOT NULL,
    at timestamptz NOT NULL,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE alert (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id varchar(7) NOT NULL REFERENCES "case"(id) ON DELETE CASCADE,
    tier text NOT NULL CHECK (tier IN ('T2', 'T3', 'T4')),
    recipient text NOT NULL,
    channel text NOT NULL CHECK (channel IN ('inapp', 'digest', 'push', 'sms', 'call')),
    status text NOT NULL,
    dedup_key text NOT NULL UNIQUE,
    at timestamptz NOT NULL,
    ack_at timestamptz,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX ix_alert_recipient_status ON alert (recipient, status, at DESC);

CREATE TABLE escalation_step (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id varchar(7) NOT NULL REFERENCES "case"(id) ON DELETE CASCADE,
    step smallint NOT NULL CHECK (step > 0),
    recipient text NOT NULL,
    due_at timestamptz NOT NULL,
    fired_at timestamptz,
    ack_at timestamptz,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (case_id, step)
);

CREATE TABLE self_referral (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    token varchar(19) NOT NULL REFERENCES subject(token) ON DELETE CASCADE,
    target text NOT NULL CHECK (
        target IN ('uwo', 'counsellor_anon', 'counsellor_named')
    ),
    note_enc bytea,
    status text NOT NULL,
    at timestamptz NOT NULL,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE counsel_session (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    counsellor_id uuid NOT NULL REFERENCES officer(id),
    token varchar(19) REFERENCES subject(token) ON DELETE SET NULL,
    anon_handle text,
    mode text NOT NULL CHECK (mode IN ('chat', 'voice', 'video')),
    scheduled_at timestamptz NOT NULL,
    started_at timestamptz,
    ended_at timestamptz,
    status text NOT NULL,
    notes_enc bytea,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CHECK (token IS NOT NULL OR anon_handle IS NOT NULL)
);
CREATE INDEX ix_counsel_session_counsellor_schedule
    ON counsel_session (counsellor_id, scheduled_at);

CREATE TABLE safety_plan (
    token varchar(19) PRIMARY KEY REFERENCES subject(token) ON DELETE CASCADE,
    content_enc bytea NOT NULL,
    updated_at timestamptz NOT NULL,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE access_ledger (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    token varchar(19) NOT NULL REFERENCES subject(token) ON DELETE CASCADE,
    actor_role text NOT NULL,
    actor_label text NOT NULL,
    action text NOT NULL,
    purpose_code text NOT NULL,
    at timestamptz NOT NULL,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX ix_access_ledger_token_at ON access_ledger (token, at DESC);

CREATE TABLE audit_log (
    seq bigserial PRIMARY KEY,
    at timestamptz NOT NULL,
    actor text NOT NULL,
    action text NOT NULL,
    object text NOT NULL,
    meta jsonb NOT NULL DEFAULT '{}'::jsonb,
    prev_hash char(64) NOT NULL,
    hash char(64) NOT NULL UNIQUE,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE agent_session (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    token varchar(19) NOT NULL REFERENCES subject(token) ON DELETE CASCADE,
    mode text NOT NULL,
    lang text NOT NULL,
    channel text NOT NULL CHECK (channel IN ('text', 'voice', 'ivr')),
    started_at timestamptz NOT NULL,
    ended_at timestamptz,
    crisis boolean NOT NULL DEFAULT false,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE agent_turn (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL REFERENCES agent_session(id) ON DELETE CASCADE,
    role text NOT NULL CHECK (role = 'assistant'),
    text text NOT NULL,
    mode text NOT NULL,
    guard_result text NOT NULL,
    provider text NOT NULL,
    latency_ms integer NOT NULL CHECK (latency_ms >= 0),
    at timestamptz NOT NULL,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE wo_outcome_label (
    case_id varchar(7) PRIMARY KEY REFERENCES "case"(id) ON DELETE CASCADE,
    label text NOT NULL CHECK (
        label IN ('helpful', 'not_needed', 'false_alarm', 'escalated')
    ),
    at timestamptz NOT NULL,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE ruleset (
    version text PRIMARY KEY,
    yaml text NOT NULL,
    signature bytea NOT NULL,
    signers text[] NOT NULL,
    status text NOT NULL CHECK (status IN ('active', 'shadow', 'draft')),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE UNIQUE INDEX ux_ruleset_single_active
    ON ruleset ((status)) WHERE status = 'active';

CREATE TABLE model_registry (
    version text PRIMARY KEY,
    kind text NOT NULL,
    metrics jsonb NOT NULL,
    card jsonb NOT NULL,
    artefact_uri text NOT NULL,
    status text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE killswitch (
    name text PRIMARY KEY CHECK (
        name IN (
            'agent', 'voice', 'copilot', 'briefs', 'alerts_t2_t3',
            'forecast', 'jitai'
        )
    ),
    enabled boolean NOT NULL,
    changed_by text NOT NULL,
    at timestamptz NOT NULL,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE feature_flag (
    name text PRIMARY KEY CHECK (name <> 'acute'),
    enabled boolean NOT NULL,
    audience jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE integration_job (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source text NOT NULL,
    kind text NOT NULL CHECK (kind IN ('csv', 'api', 'webhook')),
    started_at timestamptz NOT NULL,
    finished_at timestamptz,
    status text NOT NULL,
    rows_in bigint NOT NULL DEFAULT 0 CHECK (rows_in >= 0),
    rows_quarantined bigint NOT NULL DEFAULT 0 CHECK (rows_quarantined >= 0),
    report jsonb NOT NULL DEFAULT '{}'::jsonb,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE quarantine_row (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id uuid NOT NULL REFERENCES integration_job(id) ON DELETE CASCADE,
    reason text NOT NULL,
    redacted_payload jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE data_quality (
    date date NOT NULL,
    source text NOT NULL,
    missingness double precision NOT NULL CHECK (missingness BETWEEN 0 AND 1),
    staleness_hours double precision NOT NULL CHECK (staleness_hours >= 0),
    drift_score double precision NOT NULL CHECK (drift_score >= 0),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (date, source)
);

CREATE TABLE corpus_chunk (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id text NOT NULL,
    lang text NOT NULL,
    title text NOT NULL,
    text text NOT NULL,
    embedding vector(1024),
    version text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (doc_id, lang, version, id)
);
CREATE INDEX ix_corpus_chunk_embedding
    ON corpus_chunk USING hnsw (embedding vector_cosine_ops);

CREATE TABLE ground_truth (
    token varchar(19) NOT NULL REFERENCES subject(token) ON DELETE CASCADE,
    world text NOT NULL CHECK (world IN ('primary', 'shifted')),
    distress_onset date,
    acute_date date,
    cohort text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (token, world)
);

CREATE TABLE sim_clock (
    id smallint PRIMARY KEY CHECK (id = 1),
    sim_now timestamptz NOT NULL,
    speed double precision NOT NULL CHECK (speed >= 0),
    running boolean NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
INSERT INTO sim_clock (id, sim_now, speed, running)
VALUES (1, '2026-09-16T04:30:00Z', 1, false);

CREATE TABLE provider_call (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    capability text NOT NULL,
    provider text NOT NULL,
    latency_ms integer NOT NULL CHECK (latency_ms >= 0),
    ok boolean NOT NULL,
    cost_estimate numeric(14,6) NOT NULL DEFAULT 0 CHECK (cost_estimate >= 0),
    at timestamptz NOT NULL,
    sim_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX ix_provider_call_provider_at ON provider_call (provider, at DESC);

SELECT create_hypertable(
    'duty_day',
    'date',
    chunk_time_interval => INTERVAL '30 days',
    if_not_exists => true,
    migrate_data => true
);
SELECT create_hypertable(
    'bio_day',
    'date',
    chunk_time_interval => INTERVAL '30 days',
    if_not_exists => true,
    migrate_data => true
);
SELECT create_hypertable(
    'indicator_day',
    'date',
    chunk_time_interval => INTERVAL '30 days',
    if_not_exists => true,
    migrate_data => true
);

ALTER TABLE "case" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "case" FORCE ROW LEVEL SECURITY;
CREATE POLICY case_scope_policy ON "case"
    FOR ALL
    USING (
        current_setting('app.role', true) = 'engine'
        OR (
            current_setting('app.role', true) = 'personnel'
            AND token = current_setting('app.subject_token', true)
        )
        OR (
            current_setting('app.role', true) = 'uwo'
            AND unit_path <@ NULLIF(current_setting('app.scope_path', true), '')::ltree
        )
        OR (
            current_setting('app.role', true) = 'mo'
            AND tier = 'T4'
            AND unit_path <@ NULLIF(current_setting('app.scope_path', true), '')::ltree
        )
    )
    WITH CHECK (
        current_setting('app.role', true) = 'engine'
        OR (
            current_setting('app.role', true) = 'uwo'
            AND unit_path <@ NULLIF(current_setting('app.scope_path', true), '')::ltree
        )
        OR (
            current_setting('app.role', true) = 'mo'
            AND tier = 'T4'
            AND unit_path <@ NULLIF(current_setting('app.scope_path', true), '')::ltree
        )
    );

ALTER TABLE assessment ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessment FORCE ROW LEVEL SECURITY;
CREATE POLICY assessment_scope_policy ON assessment
    FOR SELECT
    USING (
        current_setting('app.role', true) IN ('engine', 'wdec')
        OR (
            current_setting('app.role', true) = 'personnel'
            AND token = current_setting('app.subject_token', true)
        )
    );
CREATE POLICY assessment_engine_write_policy ON assessment
    FOR INSERT
    WITH CHECK (current_setting('app.role', true) = 'engine');

ALTER TABLE counsel_session ENABLE ROW LEVEL SECURITY;
ALTER TABLE counsel_session FORCE ROW LEVEL SECURITY;
CREATE POLICY counsel_session_scope_policy ON counsel_session
    FOR ALL
    USING (
        current_setting('app.role', true) = 'engine'
        OR (
            current_setting('app.role', true) = 'counsellor'
            AND counsellor_id::text = current_setting('app.actor_id', true)
        )
        OR (
            current_setting('app.role', true) = 'personnel'
            AND token = current_setting('app.subject_token', true)
        )
    )
    WITH CHECK (
        current_setting('app.role', true) = 'engine'
        OR (
            current_setting('app.role', true) = 'counsellor'
            AND counsellor_id::text = current_setting('app.actor_id', true)
        )
    );

ALTER TABLE grievance ENABLE ROW LEVEL SECURITY;
ALTER TABLE grievance FORCE ROW LEVEL SECURITY;
CREATE POLICY grievance_scope_policy ON grievance
    FOR ALL
    USING (
        current_setting('app.role', true) = 'engine'
        OR current_setting('app.role', true) = 'dpo'
        OR (
            current_setting('app.role', true) = 'personnel'
            AND token_hash = encode(
                digest(current_setting('app.subject_token', true), 'sha256'),
                'hex'
            )
        )
        OR (
            current_setting('app.role', true) = 'uwo'
            AND unit_path <@ NULLIF(current_setting('app.scope_path', true), '')::ltree
        )
    )
    WITH CHECK (
        current_setting('app.role', true) = 'engine'
        OR (
            current_setting('app.role', true) = 'personnel'
            AND token_hash = encode(
                digest(current_setting('app.subject_token', true), 'sha256'),
                'hex'
            )
        )
        OR (
            current_setting('app.role', true) = 'uwo'
            AND unit_path <@ NULLIF(current_setting('app.scope_path', true), '')::ltree
        )
    );

CREATE OR REPLACE FUNCTION reject_immutable_change()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'immutable table % cannot be changed', TG_TABLE_NAME;
END;
$$;

CREATE TRIGGER assessment_immutable
BEFORE UPDATE OR DELETE ON assessment
FOR EACH ROW EXECUTE FUNCTION reject_immutable_change();

CREATE OR REPLACE FUNCTION append_audit(
    p_actor text,
    p_action text,
    p_object text,
    p_meta jsonb DEFAULT '{}'::jsonb,
    p_at timestamptz DEFAULT clock_timestamp(),
    p_sim_at timestamptz DEFAULT clock_timestamp()
)
RETURNS audit_log
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    previous_hash text;
    next_hash text;
    inserted audit_log;
    canonical_entry jsonb;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtext('manobal_audit_chain'));
    SELECT hash::text
      INTO previous_hash
      FROM audit_log
     ORDER BY seq DESC
     LIMIT 1;
    previous_hash := COALESCE(previous_hash, repeat('0', 64));
    canonical_entry := jsonb_build_object(
        'at', p_at,
        'actor', p_actor,
        'action', p_action,
        'object', p_object,
        'meta', COALESCE(p_meta, '{}'::jsonb),
        'sim_at', p_sim_at
    );
    next_hash := encode(
        digest(
            convert_to(previous_hash || canonical_entry::text, 'UTF8'),
            'sha256'
        ),
        'hex'
    );
    INSERT INTO audit_log (
        at, actor, action, object, meta, prev_hash, hash, sim_at
    )
    VALUES (
        p_at, p_actor, p_action, p_object, COALESCE(p_meta, '{}'::jsonb),
        previous_hash, next_hash, p_sim_at
    )
    RETURNING * INTO inserted;
    RETURN inserted;
END;
$$;

CREATE OR REPLACE FUNCTION verify_audit_chain()
RETURNS TABLE (
    valid boolean,
    checked bigint,
    broken_seq bigint,
    head_hash text
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    row_value audit_log%ROWTYPE;
    previous_hash text := repeat('0', 64);
    expected_hash text;
    canonical_entry jsonb;
    checked_count bigint := 0;
BEGIN
    FOR row_value IN SELECT * FROM audit_log ORDER BY seq LOOP
        canonical_entry := jsonb_build_object(
            'at', row_value.at,
            'actor', row_value.actor,
            'action', row_value.action,
            'object', row_value.object,
            'meta', row_value.meta,
            'sim_at', row_value.sim_at
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
            SELECT false, checked_count, row_value.seq, previous_hash;
            RETURN;
        END IF;
        previous_hash := row_value.hash::text;
    END LOOP;
    RETURN QUERY SELECT true, checked_count, NULL::bigint, previous_hash;
END;
$$;

CREATE TRIGGER audit_log_immutable
BEFORE UPDATE OR DELETE ON audit_log
FOR EACH ROW EXECUTE FUNCTION reject_immutable_change();

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'core_app') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public
            TO core_app;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO core_app;
        GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO core_app;
        REVOKE INSERT, UPDATE, DELETE ON audit_log FROM core_app;
        GRANT EXECUTE ON FUNCTION append_audit(
            text, text, text, jsonb, timestamptz, timestamptz
        ) TO core_app;
        GRANT EXECUTE ON FUNCTION verify_audit_chain() TO core_app;
    END IF;
END
$$;
"""


TABLES = (
    "provider_call",
    "sim_clock",
    "ground_truth",
    "corpus_chunk",
    "data_quality",
    "quarantine_row",
    "integration_job",
    "feature_flag",
    "killswitch",
    "model_registry",
    "ruleset",
    "wo_outcome_label",
    "agent_turn",
    "agent_session",
    "audit_log",
    "access_ledger",
    "safety_plan",
    "counsel_session",
    "self_referral",
    "escalation_step",
    "alert",
    "consent_request",
    "breakglass",
    "case_grant",
    "case_action",
    '"case"',
    "jitai_log",
    "nudge",
    "shadow_assessment",
    "assessment",
    "domain_score",
    "baseline",
    "regime",
    "indicator_day",
    "grievance",
    "climate_pulse",
    "engagement_day",
    "voice_features",
    "bio_day",
    "instrument",
    "ema",
    "incident",
    "deployment_event",
    "org_event",
    "leave_event",
    "leave_balance",
    "duty_day",
    "notice_version",
    "breach_register",
    "erasure_receipt",
    "nominee",
    "rights_request",
    "consent_receipt",
    "consent_ledger",
    "buddy_pair",
    "officer",
    "subject_audit_attrs",
    "subject",
    "unit",
)


def upgrade() -> None:
    op.execute(SCHEMA_SQL)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS verify_audit_chain()")
    op.execute(
        "DROP FUNCTION IF EXISTS append_audit(text, text, text, jsonb, timestamptz, timestamptz)"
    )
    op.execute("DROP FUNCTION IF EXISTS reject_immutable_change() CASCADE")
    for table in TABLES:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
