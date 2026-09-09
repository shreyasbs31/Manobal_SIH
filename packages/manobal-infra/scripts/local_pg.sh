#!/usr/bin/env bash
#
# Project-local PostgreSQL clusters — the containerless equivalent of
# docker-compose.yml, for machines where Docker is unavailable.
#
# Two clusters, not two databases, because SDD §3.2 puts the identity vault in
# its own zone and the whole privacy argument rests on the analytics plane being
# *unable* to reach it rather than declining to. Docker gives that with an
# internal network; here it comes from three things acting together:
#
#   * separate clusters on separate ports with separate data directories,
#   * a role (manobal_identity) that exists only in the identity cluster, and
#   * a pg_hba.conf on the identity cluster that rejects every principal except
#     that one role.
#
# The result is that `psql -U manobal_core -d iam_vault` fails at authentication,
# not at authorisation, which is what the §9.6 gate
# test_analytics_plane_cannot_reach_identity_vault asserts.
#
# Both data directories live on the project volume. Nothing is written to the
# startup disk.
#
# Usage: local_pg.sh {up|down|status|reset|psql-analytics|psql-identity}

set -euo pipefail

readonly REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
readonly INFRA_DIR="${REPO_ROOT}/packages/manobal-infra"
readonly PG_BIN="${MANOBAL_PG_BIN:-/opt/homebrew/opt/postgresql@16/bin}"

readonly ANALYTICS_DATA="${REPO_ROOT}/.pgdata/analytics"
readonly IDENTITY_DATA="${REPO_ROOT}/.pgdata/identity"
readonly ANALYTICS_PORT="${MANOBAL_PG_ANALYTICS_PORT:-55432}"
readonly IDENTITY_PORT="${MANOBAL_PG_IDENTITY_PORT:-55433}"
readonly ANALYTICS_LOG="${REPO_ROOT}/.pgdata/analytics.log"
readonly IDENTITY_LOG="${REPO_ROOT}/.pgdata/identity.log"

readonly SUPERUSER="${MANOBAL_PG_SUPERUSER:-$(whoami)}"

log() { printf '\033[36m==>\033[0m %s\n' "$*"; }
die() { printf '\033[31merror:\033[0m %s\n' "$*" >&2; exit 1; }

require_binaries() {
  [[ -x "${PG_BIN}/initdb" ]] || die "PostgreSQL 16 binaries not found at ${PG_BIN}. Set MANOBAL_PG_BIN."
}

# --------------------------------------------------------------------- init --

init_analytics() {
  log "initdb: analytics cluster at ${ANALYTICS_DATA}"
  "${PG_BIN}/initdb" -D "${ANALYTICS_DATA}" -U "${SUPERUSER}" \
    --encoding=UTF8 --locale=C --auth-local=trust --auth-host=scram-sha-256 >/dev/null

  cat >>"${ANALYTICS_DATA}/postgresql.conf" <<EOF

# --- MANOBAL local development (Zone 2 analytics plane) ---
port = ${ANALYTICS_PORT}
listen_addresses = '127.0.0.1'
log_statement = 'ddl'
log_min_duration_statement = 500
EOF
}

init_identity() {
  log "initdb: identity cluster at ${IDENTITY_DATA}"
  "${PG_BIN}/initdb" -D "${IDENTITY_DATA}" -U "${SUPERUSER}" \
    --encoding=UTF8 --locale=C --auth-local=trust --auth-host=scram-sha-256 >/dev/null

  cat >>"${IDENTITY_DATA}/postgresql.conf" <<EOF

# --- MANOBAL local development (Zone 3 identity enclave) ---
port = ${IDENTITY_PORT}
listen_addresses = '127.0.0.1'
# Every connection is logged. Zone 3 keeps its own record precisely because the
# analytics-plane audit log is reachable by anyone who owns the analytics plane.
log_connections = on
log_disconnections = on
log_statement = 'all'
EOF

  # The enforcement, not a comment about it: over TCP only manobal_identity may
  # authenticate, and only to iam_vault. manobal_core and manobal_risk are
  # rejected before any password is even considered.
  cat >"${IDENTITY_DATA}/pg_hba.conf" <<EOF
# MANOBAL Zone 3 — SDD §4.9. Deny by default; one role, one database.
local   all             ${SUPERUSER}                            trust
local   all             manobal_identity                        trust
host    iam_vault       manobal_identity        127.0.0.1/32    scram-sha-256
host    iam_vault       manobal_identity        ::1/128         scram-sha-256
host    all             all                     0.0.0.0/0       reject
host    all             all                     ::0/0           reject
EOF
}

# ---------------------------------------------------------------- lifecycle --

start_cluster() {
  local data="$1" logfile="$2" name="$3"
  if "${PG_BIN}/pg_ctl" -D "${data}" status >/dev/null 2>&1; then
    log "${name} cluster already running"
    return
  fi
  log "starting ${name} cluster"
  "${PG_BIN}/pg_ctl" -D "${data}" -l "${logfile}" -w start >/dev/null
}

stop_cluster() {
  local data="$1" name="$2"
  if "${PG_BIN}/pg_ctl" -D "${data}" status >/dev/null 2>&1; then
    log "stopping ${name} cluster"
    "${PG_BIN}/pg_ctl" -D "${data}" -m fast -w stop >/dev/null
  fi
}

bootstrap_analytics() {
  log "applying analytics-init.sql (5 databases, 3 roles, least-privilege grants)"
  "${PG_BIN}/psql" -q -p "${ANALYTICS_PORT}" -U "${SUPERUSER}" -d postgres \
    -v ON_ERROR_STOP=1 -f "${INFRA_DIR}/postgres/analytics-init.sql"

  # Dev-only. pytest-django builds and drops a test_* copy of each store per
  # run, which needs CREATEDB. This grant lives here rather than in
  # analytics-init.sql on purpose: that file is the production-shaped artefact
  # and is applied verbatim by docker-compose, where the application role
  # creating databases at will would be a genuine privilege-escalation step.
  log "granting CREATEDB to manobal_core (local test databases only)"
  "${PG_BIN}/psql" -q -p "${ANALYTICS_PORT}" -U "${SUPERUSER}" -d postgres \
    -v ON_ERROR_STOP=1 -c "ALTER ROLE manobal_core CREATEDB;"
}

bootstrap_identity() {
  log "creating iam_vault and applying identity-init.sql"
  "${PG_BIN}/createdb" -p "${IDENTITY_PORT}" -U "${SUPERUSER}" iam_vault
  "${PG_BIN}/psql" -q -p "${IDENTITY_PORT}" -U "${SUPERUSER}" -d iam_vault \
    -v ON_ERROR_STOP=1 -f "${INFRA_DIR}/postgres/identity-init.sql"
}

cmd_up() {
  require_binaries
  mkdir -p "${REPO_ROOT}/.pgdata"

  local fresh_analytics=false fresh_identity=false
  [[ -d "${ANALYTICS_DATA}" ]] || { init_analytics; fresh_analytics=true; }
  [[ -d "${IDENTITY_DATA}"  ]] || { init_identity;  fresh_identity=true; }

  start_cluster "${ANALYTICS_DATA}" "${ANALYTICS_LOG}" "analytics"
  start_cluster "${IDENTITY_DATA}"  "${IDENTITY_LOG}"  "identity"

  "${fresh_analytics}" && bootstrap_analytics
  "${fresh_identity}"  && bootstrap_identity

  cmd_status
}

cmd_down() {
  require_binaries
  stop_cluster "${ANALYTICS_DATA}" "analytics"
  stop_cluster "${IDENTITY_DATA}"  "identity"
}

cmd_reset() {
  cmd_down
  log "removing both data directories"
  rm -rf "${REPO_ROOT}/.pgdata"
  cmd_up
}

cmd_status() {
  require_binaries
  printf '\n  %-12s %-8s %-9s %s\n' "CLUSTER" "PORT" "STATE" "ZONE"
  printf '  %-12s %-8s %-9s %s\n' "analytics" "${ANALYTICS_PORT}" \
    "$("${PG_BIN}/pg_isready" -q -h 127.0.0.1 -p "${ANALYTICS_PORT}" && echo up || echo down)" \
    "2 — org, psy, bio, voice, gov"
  printf '  %-12s %-8s %-9s %s\n\n' "identity" "${IDENTITY_PORT}" \
    "$("${PG_BIN}/pg_isready" -q -h 127.0.0.1 -p "${IDENTITY_PORT}" && echo up || echo down)" \
    "3 — iam_vault (manobal_identity only)"
}

cmd_psql_analytics() { exec "${PG_BIN}/psql" -p "${ANALYTICS_PORT}" -U "${SUPERUSER}" "${@:-gov_store}"; }
cmd_psql_identity()  { exec "${PG_BIN}/psql" -p "${IDENTITY_PORT}"  -U "${SUPERUSER}" iam_vault; }

case "${1:-}" in
  up)              cmd_up ;;
  down)            cmd_down ;;
  reset)           cmd_reset ;;
  status)          cmd_status ;;
  psql-analytics)  shift; cmd_psql_analytics "$@" ;;
  psql-identity)   cmd_psql_identity ;;
  *) die "usage: $(basename "$0") {up|down|status|reset|psql-analytics|psql-identity}" ;;
esac
