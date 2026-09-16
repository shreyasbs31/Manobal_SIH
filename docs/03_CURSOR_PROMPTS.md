# MANOBAL: Cursor Prompts v3 (combined)

You have already run the old Prompt 1 (foundation) and Prompt 2 (design system and shells). The rest is now **six combined prompts** (3 to 8), ordered as vertical slices so real, polished screens exist early.

## How to run them
1. Put these files in `docs/`: `02_MANOBAL_MVP_BUILD_SPEC.md`, `04_MANOBAL_UI_DIRECTION.md`.
2. Replace `.cursor/rules/manobal.mdc` with the rules block below.
3. Run each prompt in a **fresh Agent chat** with the strongest model. Paste the Execution protocol above every prompt.
4. If a chat runs out of context, open a new chat and paste the Resume prompt.
5. Do not start the next prompt until the current prompt's "Done when" list passes.

---

## Rules file (`.cursor/rules/manobal.mdc`)

```
---
description: MANOBAL project rules
alwaysApply: true
---
- Sources of truth: docs/02_MANOBAL_MVP_BUILD_SPEC.md (v2.1) and docs/04_MANOBAL_UI_DIRECTION.md (UI v3). For UI, the UI direction wins where they differ.
- All data is synthetic. No real names, service numbers, battalion numbers, crests, emblems, flags, or political or religious symbols.
- Never write U+2014 (em dash) or U+2013 (en dash) anywhere: code, comments, copy, seed data, prompts, docs, commits.
- Privacy is enforced server-side. Welfare, Counsellor and Command UIs never show numeric stress scores or rank people. Command and HQ routes never accept token, case, or person parameters. The engine never holds vault DB access or vault keys.
- No Anthropic SDKs or APIs. Language models are Microsoft Foundry deployments addressed by class (main, fast, open, alt) via the openai SDK with Entra auth. alt (Grok) is never used for personnel-facing or safety tasks.
- The companion voice path is a cascade: STT, gates, LLM, TTS. Classifier errors fail safe to crisis. The acute path cannot be disabled.
- Offline claims must be true: anything shown in an offline state must work with the network off.
- Personalisation never feeds scoring, forecasting, or officer views.
- Model ids, voice names and language lists live in config.
- UI: follow docs/04_MANOBAL_UI_DIRECTION.md exactly, including the banned list and the review loop in its section 9. No default shadcn look, no identical card grids, no all-caps, no eyebrow labels, no emoji faces, no AI sparkles, no red except T4 and call buttons.
- Copy: sentence case, plain, kind, non-clinical. Banned: diagnosis, disorder, suicide risk score, mentally ill, unfit, abnormal.
- TypeScript strict, no any. Python typed, Pydantic v2, mypy-clean. Loading, empty, error and offline states on every screen. WCAG 2.2 AA.
- One dev workflow: `make dev` runs everything; the web app always serves on port 3000. Rebuild images when Dockerfiles or dependencies change.
```

## Execution protocol (paste above every prompt)

```
Before coding: read the spec sections and UI sections named in this prompt. Write a numbered plan into docs/PROGRESS.md under a heading for this prompt, one line per deliverable, each with its check.
While coding: work through the plan in order. After each item, run its check, tick it in PROGRESS.md, and commit with a clear message. Do not skip checks. Do not mark anything done that is stubbed.
If blocked on an external service, use the fallback named in spec 31.1, note it in PROGRESS.md, and continue.
Do not ask me questions unless a decision would change the architecture. Make the choice the spec implies and record it.
At the end: run make test, make lint, copy-lint, and the UI review loop for touched screens, then give me a short summary with remaining issues.
```

## Resume prompt

```
Read docs/PROGRESS.md, docs/02_MANOBAL_MVP_BUILD_SPEC.md and docs/04_MANOBAL_UI_DIRECTION.md. Continue the unfinished prompt from the first unticked item. Follow the execution protocol.
```

---

## Prompt 3: UI elevation and design system v3

```
Goal: upgrade what Prompt 2 built to UI Direction v3 so every later screen inherits a distinctive, video-ready look.

Read: UI direction sections 0 to 9 fully; spec 16, 17.14, 17.15.

Do:
1. Audit the current UI against UI direction section 0 and section 8. Write findings to docs/UI_NOTES.md with screenshots before changes.
2. Tokens: replace colours, elevation, radii, spacing, and motion tokens with UI direction 2.1, 2.3, 2.7. Add the Survey paper light theme for Command. Keep contrast tests; extend them to glyphs (3:1) and text (4.5:1) for every theme.
3. Typography: configure Anek width axis roles (expanded, normal, condensed) and the scale in 2.2; Devanagari line-height 1.7; remove any monospace from UI.
4. Textures: build a seeded contour SVG generator (simplex noise plus marching squares) and the Command map grid (2.4). Seed from a stable per-user value.
5. Icons: tier glyph set and the custom icons in 2.5.
6. Signature components: rebuild BaselineRibbonChart as the Lay ribbon (3.1) with hero and detail variants and empty state; build VoiceContour (3.2) on canvas with listening, thinking, speaking, and crisis-settle states driven by an amplitude prop; rebuild FormationGrid (3.3) as a map sheet with references, banded single-hue cells, hidden hatch with lock and tooltip, selection outline.
7. Rebuild CaseCard and add CaseStrip (3.4), SlaTimer and EscalationLadder (3.5), FaceScale with five custom SVG faces (3.6), ConsentCard, ReceiptCard, AccessLedgerItem (3.7), ChainStatus with verify, tamper, and heal animations (3.8), status chips (3.9).
8. Illustration kit: create an `illustrations/` package with typed slots for the 14 scenes in 2.6. Generate first versions with an image model using the base prompt, clean them to optimised SVG, and review every output against the banned list. Where generation is not possible, ship tasteful line-art placeholders in the same style, never stock images.
9. Motion: implement the named motions and the orchestrated moments listed in 2.7 as reusable hooks; reduced-motion fallbacks.
10. Sound and haptics utilities (2.8) with settings.
11. Shells: restyle Saathi shell and Command shell to match 4.1 and 4.7 framing; status strip per 3.9.
12. Landing: rebuild to 4.15 with the animated Lay ribbon hero and role doors; second fold mapping table.
13. Stage: rebuild to 4.16 with the recording top bar and hidden Director drawer.
14. Build static, fixture-driven versions of these screens so they look real before the backend exists: Saathi home (4.1), check-in (4.2), Saathi voice (4.3, simulated amplitude), safety screen (4.4), breathing (4.5), Me privacy and ledger (4.6), Welfare queue (4.7), case workspace (4.8), Medical acute board (4.9), Command posture (4.10), Governance overview (4.12), Architecture (4.14). Fixtures must match the OpenAPI contracts in packages/contracts and use the personas from spec 29.
15. Run the review loop (UI direction section 9) on all of the above.
16. Fix the dev workflow so make dev serves web on port 3000 and rebuilds the image when needed.

Done when: every screen in step 14 scores at least 4 on every rubric line in UI_NOTES.md, axe is clean on each, both skins and all themes render, and before and after screenshots are in e2e/artifacts/ui/.
```

## Prompt 4: The world and the brain (synthetic data, engine, cases, safety, privacy)

```
Goal: real data and real decisions behind the screens.

Read: spec 5, 6, 7, 8, 9.1, 9.2, 10.1, 10.2, 10.6, 11, 14.1, 23.1, 23.2, 29.

Do:
1. Synthetic generator (spec 5): org tree, causal generator in the order of 5.2, primary and shifted worlds, the data-volume rules in 5.2, identities only via vault /tokenise, ground truth, fairness attributes, consent ledger, buddy pairs, climate pulse, grievances. Personas and officer personas with the storylines, profiles, and personalisation settings in spec 29. CLI: generate, personas, snapshot, restore (under 20 s).
2. Engine core (spec 8.1 to 8.5, 8.8): indicators, de-seasonalisation, regimes, cold start, floors, z, EWMA, CUSUM, domain scores with coverage and consent gating, renormalised WSI, tiers, corroboration, hysteresis, acute override, limited_data, change points, signed ruleset and shadow ruleset. Use polars; meet the performance rules in 8.9.
3. Forecast and drivers (8.6, 8.7): LightGBM with monotone constraints, isotonic calibration, conformal interval, excluded attributes, SHAP drivers through phrases.yaml (English and Hindi), trajectory and forecast authority, model registry with metrics on both worlds.
4. Levers and closed loop (9.1, 9.2) with ranking and weekly re-ranking.
5. Cases, SLAs, alerts, digest, escalation ladder with compressed timers.
6. Acute module (10.1, 10.2) isolated with its own worker; automatic grant, vault resolve, access ledger, WDEC audit category; POST /acute.
7. Incident protocol (11) with HMAC webhook, 72-hour cards, 28-day follow-up, aggregate commander card.
8. Pre-rendered audio pipeline (10.6): manifest, generation job using the speech providers, Blob storage, service-worker cache list.
9. Privacy plane (14.1): k-anonymity with complementary suppression, churn, trend neighbour suppression, simulator and tool enforcement, grants with contact-note rule, break-glass with approver, trend-share requests, consent withdrawal with purge and signed receipts, kill switches (acute path excluded), Zone X test, audit anchors.
10. Realtime events (spec 18) with Azure Web PubSub and the local fallback hub; server-side filtering by role and unit.
11. Replace the fixtures from Prompt 3 with live API data on every screen built there; keep fixtures only for Storybook-style gallery pages.
12. Tests: 23.1 and the full privacy suite in 23.2 as a CI gate.

Done when: make seed completes under 3 minutes; the eight personas land exactly as spec 5.3 says; POST /acute produces a T4 case and alerts in under 2 seconds; the privacy suite is green; the Prompt 3 screens show live data with no visual regression.
```

## Prompt 5: AI and voice

```
Goal: a safe, fast, bilingual companion and trustworthy officer AI.

Read: spec 3.2, 3.3, 12, 13, 23.3, 27.3; UI direction 3.2, 4.3.

Do:
1. Provider router (3.3) with Foundry classes main, fast, open, embeddings, optional alt (non-personnel only), optional sovereign endpoint, Azure Content Safety, Azure Translator, Deepgram, Azure Speech. Managed identity auth, timeouts, circuit breakers, fallbacks, provider_call metrics, resilience-mode cache, warm-up endpoint.
2. AI gateway (12.1) with signed prompt files; all tasks in 12.2; brief_verify enforced; dash removal on outputs.
3. Companion pipeline exactly per 12.3: sanitiser, browser and server lexicon gate, fast-model crisis classifier, Content Safety self-harm, Prompt Shields, mode router, companion, output guard. Any positive or any error routes to the acute path with no model reply.
4. Companion prompt from 12.4, tools, "Things Saathi remembers" context injection (spec 28.4) only when opted in.
5. Corpus (12.5): write 25 to 30 accurate, warm documents in English and Hindi, embed into pgvector, ask mode cites chunk ids.
6. Transliteration of Latin-script Hindi before gating.
7. Voice (13): AudioWorklet capture, VAD and push-to-talk, WebSocket session, STT routing (Deepgram Nova-3 English with end-of-turn, Nova-3 hi and multi with keyterms, Azure Speech for other Indian locales), TTS routing (Deepgram Flux Indian-accent English, Azure Hindi and other Indian voices from config), sentence streaming, barge-in, latency instrumentation, opensmile in memory with zeroisation and audio.cleared events.
8. Wire VoiceContour to real input and output amplitude; captions; prototype hosting caption (spec 27.5).
9. Evals (23.3) including the model routing gate that decides per language whether open or main serves the companion; Copilot refusal suite; brief suite; recorded fixtures for English, Hindi, Hinglish, Tamil.
10. Optional P2: on-device preview (27.3) behind a capability check.

Done when: English, Hindi and Tamil voice check-ins work end to end within the latency budget in 13.3; typed and spoken Hinglish distress never reaches the model and triggers the acute path; eval crisis recall is 100%; the routing decision is recorded in the model registry.
```

## Prompt 6: Saathi complete

```
Goal: the personnel app a constable would actually keep using.

Read: spec 9.3, 9.4, 10.3 to 10.5, 14.2, 17.1 (all), 27, 28; UI direction 3, 4.1 to 4.6, 5.

Do:
1. Onboarding (17.1.1) with consent cards, the one exception, receipt, optional buddy, safety plan, wearable, device check, and the personalisation questions in 28.2.
2. Home (17.1.2) with Lay hero, one context card maximum two, quick tiles, status strip, shift strip.
3. Check-in (17.1.3) with FaceScale, tags, adaptive length (28.5), completion joining the ribbon.
4. Saathi screen (17.1.4) integrated with Prompt 5.
5. Assessments (17.1.5) including conversational mode, validated and self-only badges, PHQ-9 item 9 safety flow.
6. Toolkit (17.1.6) with all items, pre-rendered audio, contextual Thompson-sampling recommender with offline cache (28.3).
7. Plan my rest (17.1.7): leave planner and shift and sleep planner.
8. Talk to a person (17.1.8): requests, counsellor booking, ACS voice and video calls.
9. My safety plan (10.4, 17.1.9) and the safety screen (10.3) with SMS SOS.
10. Buddy (17.1.10) with strict privacy.
11. Family connect (17.1.11) if time allows.
12. Me (17.1.12): trends, privacy, Rights Centre (14.2), ledger, receipts, requests, concerns with SLA, unit pulse, trust pulse, personalisation controls, "Things Saathi remembers", settings including simple mode.
13. JITAI (9.3) with caps and quiet hours; lifecycle pathways (9.4).
14. Offline (17.1.13 and every row of 27.2): encrypted queue, structured offline voice check-in, cached assessments and toolkit, lexicon gate, local nudge rules, trends from snapshot, acute retry, resync drain, edge link behaviour.
15. i18n: English and Hindi reviewed strings from UI direction 5.2; Tamil for Karthik; all 22 languages machine-translated and flagged via Azure Translator.
16. Tests proving no personalisation field reaches scoring or officer payloads.
17. Review loop on every Saathi screen at 360, 390 and 412 widths.

Done when: Arjun, Meena and Karthik show visibly different, explained home screens; everything in 27.2 works with the phone's data off; Lighthouse PWA installable, mobile performance 90+, accessibility 95+.
```

## Prompt 7: Officer and command surfaces

```
Goal: consoles that make the right action obvious and make misuse impossible.

Read: spec 17.2 to 17.6, 28.6, 29.9; UI direction 3.3 to 3.5, 4.7 to 4.11.

Do:
1. Welfare Console (17.2): master-detail queue with keyboard navigation, T4 banner, digest, case workspace with case strip, levers, verified brief with field-reference hovers, trend-share requests, identity reveal with purpose and contact-note rule, actions, outcomes, incident check-ins, self-referrals, follow-ups, workload.
2. Counsellor Desk (17.3) with ACS calls, private notes, lever suggestions without notes, language-matched routing.
3. Medical Desk (17.4) with acute board, ladder, acknowledge, referrals, acute guide.
4. Command Console (17.5): field-sheet posture, KPI strip, takeaway sentences, side panel, roster balancer with small-group locks and draft order, leave pressure, unit climate, grievance categories, Command Copilot drawer with aggregate tools, charts, Hindi and English suggestions, refusal behaviour.
5. Force HQ (17.6): theatre comparison, schematic sector board, capacity vs demand, lever effectiveness (labelled observational), retention pressure, policy simulator, monthly brief with edit and PDF export.
6. Officer personalisation (28.6) and officer personas (29.9).
7. Sound and chimes for T3 and T4 on consoles.
8. Review loop at 1280, 1440 and 1920 in both Command themes.

Done when: the full Arjun flow works end to end with the ledger updating on /stage; Post D-7 shows the hidden tile; "Charlie Coy mein kaun pareshan hai?" is refused with a useful aggregate answer; the HQ brief exports.
```

## Prompt 8: Trust, proof, showcase, ship

```
Goal: everything a judge needs to believe it, and a flawless recording setup.

Read: spec 14.3, 14.4, 15, 17.7 to 17.15, 20, 21, 22, 23.4 to 23.6, 24, 27.4, 28.7, 30, 31, 32; UI direction 3.8, 4.12 to 4.16.

Do:
1. Governance (17.7) complete, including exposure parity (28.7), provider health, model card, ruleset registry with two signers, transparency report.
2. DPO Centre (14.3), Trust Centre (14.4) with audio read-aloud, Integration Console (15.1, 17.9) with schema contracts, quarantine, data quality, Admin (17.10).
3. Validation Lab (17.11) with primary and shifted worlds, calibration, ablations, zero-penalty proof, benchmark.
4. Architecture (17.12) with live packets, edge queue and link toggle (27.4), self-tests, mode panel.
5. Director (17.15) with all scenarios, outage simulation, resilience mode, warm-up, reset, and a preset for every shot in spec 30.3; Stage presets per spec 24.
6. Azure (20): Bicep and azd for every resource, managed identities, Key Vault access split, Front Door, Web PubSub, ACS, Speech, Translator, Content Safety, Foundry deployments; GitHub Actions per 20.2.
7. Observability and cost guard (22).
8. Prepare Saathi for iPhone Home Screen install (see 06_MANOBAL_WALKTHROUGH.md iPhone hardening list); optional Android TWA.
9. Walk the weakness audit (32) screen by screen and fix anything that could show one.
10. Playwright E2E for the full demo script (23.4) locally and on Azure, twice with a reset between.
11. Docs: DEMO_RUNBOOK.md (clicks, timings, fallbacks, resets, Q&A from spec 26 with the screen for each answer) and SHOT_LIST.md (preset, persona, click path per shot).
12. Final review loop across every screen; fix all scores below 4.

Done when: the acceptance checklist in spec 23.6 is fully ticked, every shot in SHOT_LIST.md reproduces from a reset in under 2 minutes, and the deployed Azure URL passes the E2E run.
```
