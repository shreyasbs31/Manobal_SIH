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

## Prompt 5: Safe bilingual companion and officer AI

Ship the provider router, signed AI gateway, fail-safe companion pipeline, voice cascade, RAG corpus, and recorded evals.

Choices implied by the spec (recorded, not blocked):
- Engine modules stay under `app/` (`app/providers/router.py` is spec `services/engine/providers/router.py`).
- Foundry classes map from `infra/ai/providers.yaml`. `alt` is never selected for companion, crisis, guards, check-in, or grievance tasks.
- When Foundry, Deepgram, Speech, Translator, or Content Safety env vars are empty, use the 31.1 fallbacks: local scripted model plus resilience cache; hash embeddings (Voyage is the named embed fallback and is also unset); Content Safety and Prompt Shields abstain; STT accepts fixture or client-final transcripts; TTS uses the silent-WAV first-byte path already used for pre-rendered audio.
- Classifier timeout or error still returns crisis. A missing Foundry deployment is not treated as a classifier error; a local heuristic classifier runs so non-crisis turns can complete.
- Hindi and Hinglish companion routing defaults to `main` unless the recorded eval gate records `open` as a match. English may use `open` when the recorded gate passes.
- Browser lexicon is the same `infra/lexicon/phrases.json` file the engine loads (copied into the web bundle).
- P2 on-device preview is capability-gated (WebGPU). Hindi stays on the structured offline flow.

1. [x] Provider router (spec 3.3): ordered lists per capability, timeouts, circuit breakers, fallbacks, `provider_call` metrics, resilience-mode cache, warm-up endpoint, managed-identity Foundry path. Check: `PYTHONPATH=services/engine uv run pytest services/engine/tests/test_providers.py` covers timeout, open-after-3-failures, classifier fail-safe, alt blocked on personnel tasks, cache hit by `(beat_id, language)`, warm-up status. Fallback: Foundry/Deepgram/Speech unset, local handlers plus `fallback` on warm-up (31.1).
2. [x] AI gateway (12.1) and every task in 12.2; signed prompt files; `brief_verify` enforced; dash removal on outputs. Check: tests load and verify each prompt signature; `brief_verify` rejects an unsupported sentence; U+2014 and U+2013 in a draft become commas; kill switches `agent`, `voice`, `copilot`, `briefs` skip those tasks.
3. [x] Companion pipeline exactly 12.3: sanitiser, browser and server lexicon, fast crisis classifier, Content Safety self-harm, Prompt Shields, mode router, companion, output guard; any positive or any error to acute with no model reply. Check: typed Hinglish distress never sets `model_reached`; injection refuses without acute; sanitiser strips role tokens and caps 1000 chars. Fallback: Content Safety abstains when unset (3.2).
4. [x] Companion prompt from 12.4, tools, Things Saathi remembers (28.4) only when opted in. Check: tools are the five named ones and cannot open cases; remembers omitted when opt-in is off; Hindi replies use aap in the local companion path.
5. [x] Corpus (12.5): 25 to 30 documents in English and Hindi, chunked, embedded, ask mode cites chunk ids. Check: corpus count 25-30 per language; ask with an in-corpus question returns chunk ids; ask outside the corpus offers a person and does not improvise. Fallback: lexical retrieve plus hash 1024-d vectors when Foundry embeddings are unset (Voyage also unset).
6. [x] Transliteration of Latin-script Hindi before gating. Check: `main jeena nahi chahta` transliterates then hits the lexicon; gating is not skipped when Translator is unset (local map fallback, 31.1).
7. [x] Voice (13): AudioWorklet 16 kHz PCM, VAD and push-to-talk, `WS /voice/session`, STT/TTS routing from config, sentence streaming, barge-in, latency marks, opensmile-or-numpy eGeMAPS in memory with zeroisation and `audio.cleared`. Check: en, hi, ta fixture turns finish with first audio under 1.8 s; barge-in cancels pending TTS; buffer is zeros after `audio.cleared`. Fallback: Deepgram and Speech unset, client-final transcripts plus silent-WAV first byte (31.1).
8. [x] Wire VoiceContour to real input and output amplitude; captions; prototype hosting caption (27.5). Check: Saathi voice page uses live amplitude and captions; caption text is `Prototype: open-weight model hosted on Azure. Deployable on force servers.`
9. [x] Evals (23.3): 120 companion cases, Copilot refusal suite, brief suite, recorded en/hi/hi-Latn/ta fixtures, routing gate written to the model registry. Check: crisis recall 100% on the suite; 30 individual Copilot questions refused; routing decision present in `GET /gov/models`; `make eval` is a CI gate.
10. [x] Optional P2 on-device preview (27.3) behind a capability check. Check: UI offers On-device preview only after WebGPU passes; Hindi is not offered that path. Fallback: Whisper/WebLLM weights are not vendored; English reflect uses the local template plus output guard until weights cache (31.1 P2).

End-of-prompt gate: English, Hindi, and Tamil voice check-ins within the 13.3 budget; typed and spoken Hinglish distress never reaches the model and opens the acute path; eval crisis recall 100%; routing decision in the model registry; `make test`, `make lint`, `copy-lint`, UI review loop.

## Prompt 6: Personnel app a constable would keep using

Ship the full Saathi surface: onboarding through Me, JITAI, lifecycle, genuine offline, and reviewed i18n. Personalisation never reaches scoring or officer payloads.

Choices implied by the spec (recorded, not blocked):
- Grok on the provided Foundry project is `alt` only. It is never selected for companion, crisis, guards, check-in, or other personnel or safety tasks.
- The provided Foundry project does not expose `main`, `fast`, or `open`. OpenAI `gpt-4o-mini` stands in for those classes on companion_text and companion_voice when Foundry those classes are unset. Crisis classify and output_guard stay on the local fail-safe path.
- Deepgram is wired from the local secret store. The key's documented model is nova-2; STT still requests nova-3 first and falls back to nova-2 (spec 13.2 vs the key card).
- Azure Speech, Translator, Content Safety, and ACS connection strings were not supplied. TTS stays on silent-WAV first byte; remaining UI languages ship English with a machine-translated flag until Translator is set; ACS calls show booking and a labelled demo join (31.1 scheduling fallback).
- Keys live only in gitignored `.env` files. Rotate every value that was pasted into chat.
- ScreenState must not blank Saathi when offline. Snapshots plus the encrypted queue serve 27.2.

1. [x] Onboarding (17.1.1) with language grid, consent cards, the one exception, receipt, optional buddy, safety plan, wearable, device check, and 28.2 questions. Check: `/app/onboarding` completes for Arjun; receipt hash shown; skippable extras do not block Home.
2. [x] Home (17.1.2) Lay hero, at most two context cards, quick tiles, status strip, shift strip. Check: Arjun, Meena, and Karthik homes differ (shift vs leave vs settling-back) and each context card has Why this?
3. [x] Check-in (17.1.3) FaceScale, tags, adaptive length (28.5), ribbon join on save. Check: busy-day mode is one question; full mode has tags and sleep hours; completion copy matches UI 5.2.
4. [x] Saathi screen (17.1.4) integrated with Prompt 5 plus end summary and private journal. Check: journal stays on device; crisis still routes to `/app/safety`.
5. [x] Assessments (17.1.5) including conversational mode, validated and self-only badges, PHQ-9 item 9 safety flow. Check: item 9 above 0 opens safety; AUDIT-C is marked self-only; conversational mode asks items verbatim.
6. [x] Toolkit (17.1.6) all items, pre-rendered audio, Thompson-sampling recommender with offline cache (28.3). Check: ranking never uses tier or scores; Arjun sees music or sleep first; items work from cache.
7. [x] Plan my rest (17.1.7) leave planner and shift and sleep planner. Check: Meena sees EL/CL and a feasible window; copy says MANOBAL does not submit leave.
8. [x] Talk to a person (17.1.8) requests, counsellor booking, ACS voice and video. Check: anonymous and named counsellor requests exist; ACS unset shows booking plus a labelled demo join (31.1).
9. [x] My safety plan (10.4, 17.1.9) and safety screen (10.3) with SMS SOS. Check: `sms:` link present; plan stored on device; T4 red only on call buttons.
10. [x] Buddy (17.1.10) with strict privacy. Check: buddy payloads have no tier, score, or token of the other person; unpair does not notify.
11. [x] Family connect (17.1.11). Check: shareable family link has no personal data; Meena can set a Sunday reminder.
12. [x] Me (17.1.12) trends, Rights Centre (14.2), ledger, receipts, requests, concerns with SLA, unit pulse, trust pulse, personalisation, remembers, settings including simple mode. Check: rights erase returns a receipt; simple mode enlarges targets; remembers opt-in stays off by default.
13. [x] JITAI (9.3) with caps and quiet hours; lifecycle pathways (9.4). Check: at most one prompt per day and four per week; Not now silences 72 h; Karthik sees a settling-back card for return_from_leave.
14. [x] Offline (17.1.13 and every row of 27.2): encrypted queue, structured offline voice check-in, cached assessments and toolkit, lexicon gate, local nudge rules, trends from snapshot, acute retry, resync drain, edge link. Check: with navigator.onLine false, check-in, toolkit, safety, lexicon, and trends still work; Director edge-down holds packets.
15. [x] i18n: reviewed English and Hindi from UI 5.2; Tamil for Karthik; other scheduled languages flagged machine-translated. Check: `t("safety.title", "hi")` is आप अकेले नहीं हैं।; Tamil home greeting path works; non-reviewed langs expose MachineTranslatedBadge. Azure Translator unset: 31.1 fallback ships English plus the machine-translated flag.
16. [x] Tests proving no personalisation field reaches scoring or officer payloads. Check: pytest asserts profile keys are absent from forecast features, `/command/posture`, and `/welfare/queue`.
17. [x] Review loop on every Saathi screen at 360, 390, and 412 widths. Check: scores in `docs/UI_NOTES.md`; axe clean on Saathi routes after waiting for h1; screenshots in `e2e/artifacts/ui/p6-*.png`.

End-of-prompt gate: Arjun, Meena, and Karthik show visibly different, explained home screens; 27.2 rows work after a first online open (encrypted queue, cached toolkit and safety, SMS SOS, lexicon, local nudges, snapshot trends, acute retry, resync drain, edge hold). Lighthouse on landing in next-dev: accessibility 100, performance 41; mobile 90+ needs a production build. `make test`, `make lint`, `copy-lint`, UI review loop passed.

## Prompt 7: Consoles that make the right action obvious

Officer consoles: Welfare, Counsellor, Medical, Command, and Force HQ. Identity never leaks to Command. Misuse (small-group simulation, individual Copilot questions) is refused with a useful aggregate.

Choices implied by the spec (recorded, not blocked):
- ACS is unset, so Counsellor join-call is a labelled demo join (31.1 scheduling fallback).
- Identity reveal in the demo writes the in-memory access ledger so `/stage` can show the phone updating without a live vault database.
- Copilot refuses Hindi and English individual questions, including "Charlie Coy mein kaun pareshan hai?", and answers with Charlie Coy banded share.
- HQ monthly brief PDF is generated on the device as a small text PDF. No extra print service.
- Console T3 and T4 chimes play on officer shells even when Saathi sound is off.
- Counsellor desk uses the assigned-counsellor predicate, not the UWO/MO unit-subtree gate.

1. [x] Welfare Console (17.2) master-detail queue, J/K/Enter, T4 banner, digest and other tabs, case workspace with strip, levers, verified brief hovers, trend-share, identity reveal with purpose and contact-note, actions, outcomes, workload. Check: `/welfare` lists MB-4091 under High; J then Enter opens the case; reveal with purpose writes a ledger row for Arjun.
2. [ ] Counsellor Desk (17.3) calendar, anonymous and named requests, ACS demo join, private notes, lever suggestion without notes, language-matched routing. Check: Hindi request routes to Anjali; suggest REST_48H returns lever code only; notes endpoint is counsel-scoped.
3. [ ] Medical Desk (17.4) acute board, ladder, acknowledge, referrals, acute guide. Check: MB-6604 is T4; acknowledge updates status; referrals list has minimum context; guide has no suicide-risk score.
4. [ ] Command Console (17.5) field-sheet posture, KPI strip, takeaway, side panel, Post D-7 hidden tile, roster balancer with small-group locks and draft order, leave pressure, unit climate, Copilot drawer with aggregate tools, Hindi and English suggestions, refusal. Check: Post D-7 is hatched; `/command/roster` locks n under 10; Copilot refuses "Charlie Coy mein kaun pareshan hai?" with a Charlie Coy aggregate.
5. [ ] Force HQ (17.6) theatre comparison, schematic sector board, capacity vs demand, observational lever effectiveness, retention pressure, policy simulator, monthly brief with edit and PDF export. Check: brief edit saves; PDF download starts with `%PDF`; lever table is labelled observational.
6. [x] Officer personalisation (28.6) and officer personas (29.9). Check: Sunita profile has Hindi briefs and 08:00 digest; Anjali languages include Marathi; Menon Copilot language is Hindi.
7. [x] Sound and chimes for T3 and T4 on consoles. Check: welfare with a T4 case calls `chimeT4`; T3-only queue calls `chimeT3`.
8. [ ] Review loop at 1280, 1440, and 1920 in Command dark and Command light. Check: scores in `docs/UI_NOTES.md`; screenshots in `e2e/artifacts/ui/p7-*.png`.

End-of-prompt gate: Arjun flow on `/stage` updates the ledger; Post D-7 shows the hidden tile; Copilot refuses the Hindi individual question with a useful aggregate; HQ brief exports; `make test`, `make lint`, `copy-lint`, UI review loop.
