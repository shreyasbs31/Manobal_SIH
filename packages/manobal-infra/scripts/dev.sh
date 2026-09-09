#!/usr/bin/env bash
#
# Bring the local (non-Docker) stack up: databases, migrations, seed, then
# print the commands that keep the four processes running.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "${REPO_ROOT}"

PY="${REPO_ROOT}/.venv/bin/python"
CORE="${REPO_ROOT}/packages/manobal-core/manage.py"
IDENTITY="${REPO_ROOT}/packages/manobal-identity/manage.py"

log() { printf '\033[36m==>\033[0m %s\n' "$*"; }

if [[ ! -x "${PY}" ]]; then
  log "creating workspace venv"
  make install
fi

make db-up

log "migrate Zone 2"
"${PY}" "${CORE}" migrate --noinput

log "migrate Zone 3"
"${PY}" "${IDENTITY}" migrate --noinput

log "seed identity vault"
"${PY}" "${IDENTITY}" seed_vault

log "seed analytics plane"
"${PY}" "${CORE}" seed_local

cat <<EOF

MANOBAL local stack is provisioned.

  Zone 2 API:     ${PY} ${CORE} runserver 127.0.0.1:8000
  Zone 3 enclave: ${PY} ${IDENTITY} runserver 127.0.0.1:8001
  Zone 1 edge:    MANOBAL_CORE_URL=http://127.0.0.1:8000 ${PY} -m manobal_edge
  Consoles:       (cd packages/manobal-web && npm run dev)

Personnel / officer tokens are minted from the consoles at http://127.0.0.1:5173
EOF
