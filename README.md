# MANOBAL

[![gates](https://github.com/shreyasbs31/Manobal_SIH/actions/workflows/gates.yml/badge.svg)](https://github.com/shreyasbs31/Manobal_SIH/actions/workflows/gates.yml)

AI-based predictive personnel stress and welfare monitoring for uniformed forces.
The analytics plane never holds a name, service number, or rank. The identity
enclave never sees a risk score. Those two planes have no route to each other
except a grant-gated, audited resolve.

This repository is the SIH implementation: six packages, local PostgreSQL
clusters for Zone 2 and Zone 3, and role-separated consoles.

## Zones

| Zone | What lives here | Process |
| --- | --- | --- |
| 0 | Device protocol (no identifying payload on the wire) | `packages/manobal-mobile` |
| 1 | Edge ingest | `python -m manobal_edge` |
| 2 | Analytics, casework, consoles | `127.0.0.1:8000` + Vite `:5173` |
| 3 | Identity vault | `127.0.0.1:8001` |
| 4 | Source systems (HRMS / ingest contracts) | HTTP ingest only |

Zone 2 APIs return tier and category names. They do not persist or serialise
WSI or item-level instrument answers. Commanders see k-anonymised aggregates.
Medical officers are T3/T4 consultants and are never case assignees.

## Packages

- `manobal-risk` — personal-baseline engine and signed ruleset
- `manobal-core` — Zone 2 Django service
- `manobal-identity` — Zone 3 vault
- `manobal-synth` — synthetic cohort generator
- `manobal-edge` — Zone 1 forwarder
- `manobal-web` — personnel, officer, clinical, commander, WDEC consoles
- `manobal-mobile` — Zone 0 protocol (not a shipping React Native app)

## Local run

Needs Python 3.12, Node, and the project-local PostgreSQL clusters
(`.pgdata/`, ports `55432` analytics and `55433` identity).

```bash
make install
make dev
```

Then, in separate terminals:

```bash
.venv/bin/python packages/manobal-core/manage.py runserver 127.0.0.1:8000
.venv/bin/python packages/manobal-identity/manage.py runserver 127.0.0.1:8001
cd packages/manobal-web && npm run dev
```

Consoles: [http://127.0.0.1:5173](http://127.0.0.1:5173). Development tokens
are minted from the gate (`/dev/token`) and are disabled when
`LOCAL_ISSUER_ENABLED` is false.

`make load-synth` writes a 60-day synthetic observation cohort into the
analytics stores. It does not write identifying files.

## Tests

```bash
make test          # Zone 2 then Zone 3 (separate Django settings)
make test-web
make test-mobile
make gates         # lint, typecheck, risk coverage, both zones
```

Zone 2/3 Django tests talk to the local PostgreSQL clusters. That is
deliberate: append-only triggers, check constraints, and the Zone 2/3
air-gap are enforced by the database.

GitHub Actions runs **gates** on every push to `main`: ruff, the risk
engine (90% coverage), and the web/mobile suites. That is the only check
this repository defines.

Railway, Vercel, Cursor and Greptile may also appear as queued or failed
on a commit. Those are GitHub Apps installed on the account for every
repository. This project is not deployed on Railway or Vercel, and those
suites never start a job here. Restrict them to selected repositories at
[GitHub → Settings → Applications](https://github.com/settings/installations)
so they stop attaching empty check suites to this repo.

## What this repo does not ship

A production React Native client, on-device ML, live NIC SMS, Keycloak,
mTLS between zones, Timescale hypertables in Django migrations, MinIO
object storage, and Playwright E2E. The contracts and local vertical
slice are here; those adapters are operational follow-on work.
