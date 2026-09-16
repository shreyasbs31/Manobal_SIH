# Progress

## Prompt 3: UI Direction v3 upgrade

Upgrade Prompt 2 shells to UI Direction v3 so later screens inherit a distinctive, video-ready look.

Choices implied by the spec (recorded, not blocked):
- Command light is Survey paper from UI 2.1 (`#EEF1EB` / `#F8FAF6` / brass `#8F6F1E`), not the Prompt 2 parchment.
- `FaceScale` replaces emoji faces; `EmojiScale` keeps the registry name and renders `FaceScale`.
- `VoiceContour` replaces the orb; `VoiceOrb` stays as a thin alias so the 16.6 registry still resolves.
- Generated OpenAPI in `packages/contracts` is still a skeleton. Fixture types live in `packages/contracts/src/ui-fixtures.ts` using spec 19 field names and persona 29 ids, so screens consume contract-shaped data before those routes exist.
- Illustration generation: Cursor image model, then clean SVG. If an output fails the banned list, ship original line-art SVG in the UI 2.6 style (31.1 has no image-model row).
- `make dev` is the one workflow: compose `--build`, web on port 3000.

1. [x] Audit current UI against UI direction 0 and 8; write `docs/UI_NOTES.md` with before screenshots in `e2e/artifacts/ui/`. Check: notes file lists findings per screen; `before-*.png` exist for landing, home, saathi, toolkit, me, welfare, command, medical, stage, gallery. Governance and architecture before frames follow with the capture script.
2. [x] Replace colour, elevation, radius, spacing, and motion tokens with UI 2.1, 2.3, 2.7; add Survey paper; keep contrast tests and extend glyphs 3:1 and text 4.5:1 for every theme. Check: `pnpm --filter @manobal/ui test` contrast suite passes including survey paper.
3. [x] Configure Anek width-axis roles (expanded 112, normal 100, condensed 75) and the 2.2 scale; Devanagari line-height 1.7; no monospace in UI (YAML in Governance excepted). Check: `fonts.ts` loads `wdth`; CSS has no `monospace` / `ui-monospace` outside `.mb-yaml`; `html[lang="hi"]` line-height 1.7.
4. [x] Seeded contour SVG generator (simplex plus marching squares) and Command map grid (2.4); seed from a stable per-user value. Check: unit tests prove same seed same paths, different seed different paths; home and rail render texture only where 2.4 allows.
5. [x] Tier glyph set and custom icons in 2.5 (Lay ribbon, voice contour, hidden lock, edge queue, vault key, buddy pair, leave window, shift moon). Check: gallery shows five distinct stroked glyphs; custom icons export from `@manobal/ui`.
6. [x] Rebuild `BaselineRibbonChart` as the Lay ribbon (hero, detail, empty); `VoiceContour` canvas states from amplitude; `FormationGrid` as a map sheet with references, banded cells, hidden hatch, lock, tooltip, selection. Check: gallery plus unit tests for MAD band, hidden hatch, and four voice states.
7. [x] Rebuild `CaseCard` and add `CaseStrip`, `SlaTimer`, `EscalationLadder`, `FaceScale` (five SVG faces), `ConsentCard`, `ReceiptCard`, `AccessLedgerItem`, `ChainStatus` (verify, tamper, heal), status chips (3.9). Check: gallery headings exist for each; SLA colour rules covered by a unit test.
9. [x] Named motions and orchestrated moments from 2.7 as reusable hooks, with reduced-motion fallbacks. Check: hooks module exports every named token; reduced-motion test asserts opacity-only fallback.
10. [x] Sound and haptics utilities (2.8) with settings (sound off by default). Check: unit test that sound is off until enabled; vibrate helpers no-op when unsupported.
8. [x] Create `packages/illustrations` with typed slots for the 14 scenes in 2.6; generate, clean to SVG, review against the banned list. Check: 14 exports typecheck; banned-list review is in `docs/UI_NOTES.md`; no raster stock images shipped. Fallback: original line-art SVG (image-model rasters were too filled to ship).
11. [x] Restyle Saathi shell (4.1) and Command shell (4.7); status strip per 3.9. Check: SOS is a 48 px ring; Saathi chips are only Offline, Syncing, Demo; Command top bar has SimClock, Mode, unit scope.
12. [x] Rebuild landing to 4.15 (animated Lay ribbon hero, role doors, sourced figures, second-fold mapping table). Check: hero copy matches 4.15; mapping rows match spec 26.2.
13. [x] Rebuild stage to 4.16 (1920 by 1080, recording top bar, Director drawer hidden until toggled). Check: top bar 44 px; drawer not in the default screenshot.
14. [x] Static fixture-driven screens: Saathi home, check-in, voice, safety, breathing, Me, Welfare queue, case workspace, Medical acute, Command posture, Governance, Architecture. Fixtures match contracts and persona 29. Check: each route renders persona ids from spec 29; axe clean on each.
15. [x] Run the UI direction 9 review loop on all of the above; score in `docs/UI_NOTES.md`; fix anything below 4 (max three rounds). Check: every step-14 screen scores at least 4 on every rubric line; after screenshots in `e2e/artifacts/ui/`.
16. [x] `make dev` serves web on port 3000 and rebuilds the image when Dockerfiles or lockfiles change; add `make lint`. Check: `Makefile` `dev` target publishes 3000; `make lint` runs package lints.

End-of-prompt gate: `make test`, `make lint`, `copy-lint`, UI review loop, both skins and all themes render, axe clean.

## Prompt 4: Real data and real decisions

Bind live scoring, cases, acute, privacy, and seed data behind the Prompt 3 screens.

Choices implied by the spec (recorded, not blocked):
- Identities enter core only after vault `POST /tokenise` (ingest identity). Persist uses concurrent `/tokenise` calls; generate keeps a `subject_index` until then.
- `world=primary` is COPY'd into `manobal_core`. `world=shifted` writes parquet under `services/synth/artifacts/shifted/` plus `ground_truth` rows and is never used to train the forecast.
- Load uses `COPY` after dropping secondary indexes. CPython binary `write_row` is too slow for 3.9M duty rows, so hypertables use polars CSV `COPY` (still `COPY`, indexes dropped during load).
- LightGBM is in-scope (31.1 High). SHAP values come from LightGBM `pred_contrib` (TreeSHAP) and map through `infra/rulesets/phrases.yaml` (en, hi). `ruptures` PELT runs only when WSI > 0.35.
- Pre-rendered audio: Azure Speech when `AZURE_SPEECH_KEY` is set; otherwise reviewed silent WAV files plus a manifest (31.1 TTS is High; local demo has no Speech account).
- Realtime: local hub in `infra/realtime`; Azure Web PubSub when `WEBPUBSUB_CONNECTION_STRING` is set. Engine filters by role and unit before publish.
- Ruleset signatures: two demo WDEC Ed25519 keys in `infra/keys` (Azure Key Vault in deployment). Shadow ruleset `v1.1.0-shadow` writes `shadow_assessment`.
- Acute isolation: Redis queue plus compose service `engine-acute`. `POST /acute` waits up to 2 s for the worker; if the worker is absent it processes inline so the demo SLA still holds.
- `make seed` generates the primary world (7200 x 540), tokenises, COPY-loads, scores the eight personas plus the 500-person sample, and trains the forecast on primary only.

1. [x] Synthetic generator (spec 5): full org tree, causal order 5.2, primary and shifted worlds, volume rules, vault tokenise, ground truth, fairness attrs, consent, buddy pairs, climate pulse, grievances, spec 29 personas, CLI generate/personas/snapshot/restore. Check: `uv run pytest services/synth/tests`; `uv run synth personas` prints eight spec 5.3 rows; generate 80x60 finishes and respects volume rules; restore path exists.
2. [x] Engine core (8.1 to 8.5, 8.8, 8.9): indicators, de-seasonalisation, regimes, cold start, floors, z, EWMA, CUSUM, coverage and consent gating, renormalised WSI, tiers, corroboration, hysteresis, acute override, limited_data, change points, signed and shadow rulesets, polars. Check: `uv run pytest services/engine/tests/test_scoring.py` covers those behaviours; nightly window uses last 90 days; PELT gated on WSI > 0.35.
3. [x] Forecast and drivers (8.6, 8.7): LightGBM with monotone constraints, isotonic calibration, conformal interval, excluded attributes, SHAP through phrases.yaml (en, hi), trajectory and forecast authority, model registry metrics on both worlds. Check: tests prove excluded attrs are absent, forecast never lifts above T1 without corroboration, registry has primary and shifted metrics.
4. [x] Levers and closed loop (9.1, 9.2): full lever library, rank from (tier, dominant_domain, lifecycle_state) plus 21-day de-escalation, weekly re-rank, unit constraints. Check: Arjun ranks REST_48H; Meena LEAVE_PRIORITISE; Rajesh GRIEVANCE_EXPEDITE and LEGAL_AID_REFERRAL; NO_ACTION always present.
5. [x] Cases, SLAs, alerts, digest, escalation ladder with compressed timers. Check: T2+ open cases; T4 15-minute SLA compresses by `sim_time_compression`; digest lists T2/T3; tests cover ack and escalation steps.
6. [x] Acute module (10.1, 10.2): isolated worker, automatic grant, vault resolve, access ledger, WDEC audit category, `POST /acute`. Check: `POST /acute` for Deepak returns T4 case and alerts in under 2 s; LLM is not invoked; kill switch list cannot include acute.
7. [x] Incident protocol (11): HMAC webhook, 72-hour cards, 28-day follow-up, aggregate commander card with k-anonymity. Check: invalid HMAC rejected; Lalit-style ask-to-talk appears on the UWO board; commander card suppresses counts below 3 as "a few" and needs unit n >= 10.
8. [x] Pre-rendered audio (10.6): manifest, generation job, Blob storage, service-worker cache list. Check: manifest lists safety, grounding, and breathing in configured languages; SW cache list matches; Azure Speech or silent-WAV fallback is recorded.
9. [x] Privacy plane (14.1): k-anonymity with complementary suppression and churn, trend neighbour suppression, simulator and tool enforcement, grants with 24 h contact-note, break-glass with approver, trend-share, consent withdrawal with purge and signed receipts, kill switches (acute excluded), Zone X test, audit anchors. Check: full 23.2 suite green.
10. [x] Realtime events (spec 18): Azure Web PubSub or local hub; server-side filter by role and unit. Check: commander/HQ payloads cannot contain token/case/person keys; personnel groups are token-scoped; negotiate issues a short-lived group token.
11. [x] Replace Prompt 3 fixtures with live API data on those screens; keep fixtures on the gallery page only. Check: home, check-in, me, welfare, case, medical, command, governance fetch `/api/v1/...`; `/dev/components` still uses `@manobal/contracts` fixtures; Command/HQ routes still reject person parameters.
12. [x] Tests: 23.1 engine-core coverage gate and 23.2 privacy suite as CI. Check: `make test` runs both; scoring/privacy modules meet the 90% coverage bar on those modules.

End-of-prompt gate: `make seed` under 3 minutes; eight personas match spec 5.3; `POST /acute` T4+alerts under 2 s; privacy suite green; Prompt 3 screens show live data; `make test`, `make lint`, `copy-lint`, UI review loop.
