# ADR 0001 — Monorepo with package boundaries that mirror the zone model

- **Status**: Accepted
- **Date**: 2026-09-10
- **Relates to**: SDD §1.1, §3.1, §3.2, NFR-M1

## Context

SDD §1.1 names six repositories (`manobal-mobile`, `manobal-core`, `manobal-edge`,
`manobal-risk`, `manobal-web`, `manobal-infra`). NFR-M1 requires a monorepo with
trunk-based development. These are in tension only if "repository" is read
literally rather than as "deployable unit".

## Decision

One Git repository. The six names become package directories under `packages/`,
plus two the SDD implies but does not name in §1.1: `manobal-synth` (Appendix A.3
calls the generator "a first-class deliverable, not a test fixture") and
`manobal-identity` (SDD §3.1 requires the identity resolver to be a separate
process, not merely a separate module).

Package boundaries follow the zone model rather than the technology:

| Package | Zone | Why it is separate |
|---|---|---|
| `manobal-risk` | 2 | Must be *incapable* of reaching Zone 3, not merely forbidden from it |
| `manobal-identity` | 3 | Separate process, separate database credential, separate deployment |
| `manobal-core` | 2 | The modular monolith: API, ingest, consent, cases, alerting, aggregation |
| `manobal-synth` | dev | Generates every environment that is not production |
| `manobal-web` | 2 | Officer, commander and WDEC SPAs |
| `manobal-edge` | 1 | Sync gateway and Tier-B inference |
| `manobal-infra` | — | Compose, database bootstrap, network policy, CI gates |

## Consequences

`manobal-risk` is a plain Python package whose dependency list is `numpy`,
`pyyaml` and `pynacl`. It has no database driver, no HTTP client and no
credential store in its transitive dependencies. SDD §3.2 rule 1 ("the Risk
Engine has no path to Zone 3 — it is not trusted to decline; it is unable") is
therefore checkable by reading a dependency graph, which is what the §9.6 gate
`test_risk_engine_holds_no_identity_credential` asserts.

The cost is that a single repository holds code with sharply different review
requirements. SDD §9.7 already requires a second reviewer plus WDEC
acknowledgement for changes to `manobal-risk` or the ruleset; that is enforced by
path-scoped review rules rather than by repository separation.
