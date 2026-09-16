# MANOBAL MVP: Build Specification v2.1

**Project:** MANOBAL (मनोबल), AI-based predictive personnel stress and welfare support platform for CAPFs
**Problem statement:** SIH26186 (MHA, CRPF Police-II Division), Software, MedTech/BioTech/HealthTech
**Supersedes:** v1.0 and v2.0 of this document
**v2.1 changes:** no Anthropic services anywhere; Azure-hosted OpenAI models (GPT-5.x and open-weight gpt-oss) as the AI core; Grok evaluated and restricted; offline-first made concrete (section 27); personalisation engine (section 28); persona playbooks (section 29); video production and showcase plan (section 30); feasibility review (section 31); weakness audit (section 32); decision record (section 33); data-volume fix for seeding and scoring.
**Purpose:** single source of truth for building the prototype end to end. Build exactly this. Where the document is silent, choose the more private, more secure, more polished option.

Priority tags used on every feature:
- **[P0]** demo spine. Must work flawlessly in the live demo.
- **[P1]** strongly expected. Build after the spine works end to end.
- **[P2]** stretch. Build only when P0 and P1 are solid.

---

## 0. Critique of v1 and what v2 changes

### 0.1 Product and scope flaws

| # | Flaw in v1 | Why it matters | v2 fix |
|---|---|---|---|
| 1 | No priorities. Every feature looked equally required. | A 6-person team will build 60% of everything and 100% of nothing. | Every feature tagged P0/P1/P2; build plan in section 25 follows the tags. |
| 2 | Detection-centric. The jawan mostly receives nudges. | The PS asks for "proactive counseling, welfare interventions, and workload balancing". Personnel adopt tools that give them something useful every day. | Adds a daily-value layer: leave planner, shift and sleep planner, safety plan, counsellor booking with in-app calls, buddy module, family connect, grievance tracking, audio library. |
| 3 | Ignored stressors named by the MHA task force. | Public reporting on the MHA task force draft lists working conditions (extended high-risk deployments), service conditions, and personal issues including domestic and land disputes as risk areas. | Adds grievance categories for land and property disputes and family matters, a legal-aid lever, and hardship features for deployment duration. |
| 4 | No link to CRPF's existing buddy system. | CRPF already pairs personnel as buddies. A system that ignores it looks like it was designed without the force. | Adds a Buddy module (section 17.1.10) that strengthens the existing practice without turning buddies into informants. |
| 5 | No interpersonal-conflict or unit-climate signal. | Fratricide incidents are a recurring concern in CAPFs and are often linked to interpersonal strain. | Adds anonymous unit climate pulse (k-anonymous), "colleagues" stress tag, and a conflict-resolution lever. |
| 6 | Constabulary focus missing. | Reporting on CRPF data for 2021 to 2025 says over 80% of suicides were in the constabulary and most occurred on duty. | Designs every personnel flow for constables first: voice-first, icon-first, low literacy, Hindi-first, works during duty breaks in under 60 seconds. |
| 7 | No DPDP data-principal rights beyond consent and erasure. | DPDP Rules 2025 were notified on 13 November 2025, with full obligations due by 13 May 2027 (verify dates). Judges from MHA will expect rights coverage. | Adds a Rights Centre: access, correction, erasure, grievance to the DPO, nomination, notice in the user's language, and a breach-notification workflow. |
| 8 | No admin or integration surface. | PS scope item 6 is "secure integration with HRMS". v1 had no visible integration. | Adds an Integration Console: HRMS connector with CSV and API upload, schema contract validation, quarantine, data-quality report, tokenisation preview. |
| 9 | No counsellor role. | Welfare Officers are not clinicians. CRPF has trained counsellors. | Adds a Counsellor Desk with anonymous and identified sessions, notes that never leave the counsellor's scope, and in-app voice and video calls. |
| 10 | No pre- and post-deployment pathways. | Stress spikes around induction, de-induction, return from leave, and transfer. | Adds lifecycle pathways (section 9.4) that change check-in cadence, content, and baselines at transitions. |
| 11 | "Offline-first" story had no build plan for an online prototype. | The team cannot run on-device models. | Section 2.3 defines exactly what is real in the prototype (offline capture and queue, which is cheap) and what is represented (on-device and edge inference, via a clearly labelled cloud stand-in). |

### 0.2 AI and analytics flaws

| # | Flaw | v2 fix |
|---|---|---|
| 12 | Forecast trained on synthetic data produced by our own generator is circular. A sharp judge will say "your model learned your generator". | Validation uses a **shifted world**: a second generator configuration with different causal strengths, noise, and missingness that the model never saw. Report both. Also validate the physiological domain logic on a public dataset (section 8.9). State the limitation openly. |
| 13 | Baselines break at transfers and deployment changes. | Regime-aware baselines: a posting change, induction, or return from long leave opens a new baseline regime with a short warm-up that borrows from the previous regime (section 8.2). |
| 14 | No seasonality or weekday effects. | Indicators are de-seasonalised by weekday and by rotation phase before z-scoring. |
| 15 | Single z-score per day is noisy. | Uses EWMA-smoothed deviations and a CUSUM accumulator per domain in addition to the point z-score. |
| 16 | No uncertainty shown anywhere. | Forecast carries a calibrated interval; Governance shows reliability diagrams; low-coverage assessments are marked "limited data". |
| 17 | No just-in-time interventions. | Adds a JITAI layer (section 9.3): timely, low-burden self-care prompts triggered by roster events (night shift tomorrow, 10th consecutive duty day) with frequency caps. |
| 18 | Crisis detection depended on one classifier. | Three independent gates OR-combined, all fail-safe: curated lexicon, a fast-model classifier, Azure AI Content Safety self-harm category. Pre-rendered human-authored safety audio. |
| 19 | Voice companion as speech-to-speech would bypass gates. | Mandatory cascade: STT, then gates, then LLM, then TTS. End-to-end speech-to-speech models are prohibited for the companion. |
| 20 | No evaluation harness for prompts. | Adds an eval suite (section 23.3) with red-team cases in English, Hindi, and Hinglish, run in CI. |
| 21 | Case briefs could hallucinate. | Briefs are template-bound; every sentence must reference a field id; a verifier pass rejects unreferenced claims. |

### 0.3 Privacy and security flaws

| # | Flaw | v2 fix |
|---|---|---|
| 22 | Roster balancer could leak individuals through small-group what-ifs. | k-anonymity applied to simulator inputs and outputs; groups under 10 cannot be simulated alone. |
| 23 | Time-series trends on small cells enable differencing across weeks. | Trend cells use the same suppression plus a minimum-change threshold; weeks with suppressed neighbours are also suppressed. |
| 24 | Keys lived in environment variables. | Azure Key Vault (HSM-backed keys on the Premium tier) holds the vault KEK, token HMAC key, grant signing key, and ruleset signing keys. The vault service wraps and unwraps through Key Vault. |
| 25 | No officer MFA or device binding. | Officers sign in with Microsoft Entra ID (MFA). Personnel use passkeys (WebAuthn) with PIN fallback. |
| 26 | Reveal-identity misuse only rate-limited. | Adds purpose-code analytics, peer-review sampling by WDEC, and mandatory post-contact note within 24 hours or the grant auto-revokes. |
| 27 | Private instruments (alcohol use) were not separated. | Introduces **self-only instruments** that never leave the device and never enter scoring. |
| 28 | Link between medical categorisation and welfare data unaddressed. | Explicit firewall: no field, export, or API maps welfare data to medical fitness categories, postings, or appraisals. Architecture page shows it as a blocked zone. |

### 0.4 Demo engineering flaws

| # | Flaw | v2 fix |
|---|---|---|
| 29 | Single point of failure on each cloud API. | Provider router with automatic fallback (section 3.3) and a Director "resilience mode" that serves cached or pre-rendered outputs for scripted beats. |
| 30 | Simulated time was underspecified. | Section 6.6 defines one simulated clock, how timestamps are stored, and how the UI shows it. |
| 31 | Deepgram cannot speak Hindi. | Deepgram Aura-2 and Flux TTS voices do not cover Hindi as of this writing (Flux voices are English only, including Indian-accent English voices). Hindi and other Indian-language TTS use Azure AI Speech. See section 13. |
| 32 | v2.0 depended on an external LLM vendor outside Azure. | All language models now run as Microsoft Foundry deployments on the team's Azure subscription: GPT-5.x (main and fast) and the open-weight gpt-oss-120b. The open-weight model is the same one that can later run on a force-owned GPU server, which makes the sovereign story concrete. |
| 33 | Seeding every indicator for every person every day would create well over 100 million rows. | Daily scoring only for the last 120 simulated days; weekly cadence for older history; raw indicator rows stored only for personas and a 500-person sample; everything else computed in memory (section 5.2, 8.9). |

---

## 1. Ground rules for the builder

1. All data is synthetic. Never use real names, real service numbers, real battalion numbers, the CRPF crest, or the State Emblem. Every synthetic identity shows a "Synthetic" marker.
2. `MANOBAL_MODE` is `demo` (cloud providers, Director enabled) or `sovereign` (OpenAI-compatible self-hosted endpoints, Director disabled). Only adapters change between modes. The UI always shows the active mode.
3. Never write U+2014 (em dash) or U+2013 (en dash) anywhere: code, comments, copy, seed data, prompts, generated content. CI enforces this. LLM outputs are post-processed to replace them with commas.
4. Welfare, Counsellor, and Command UIs never show a numeric stress score, probability, or ranking of people. Numbers appear only in Governance and Validation Lab.
5. The LLM never decides, never writes to assessments, cases, or alerts, and never receives a message flagged by the crisis gates.
6. Privacy is enforced server-side in the data layer. No privacy rule depends on hiding UI.
7. Copy is plain, respectful, sentence case, non-clinical. Banned in UI copy: "diagnosis", "disorder", "suicide risk score", "mentally ill", "unfit", "abnormal", "surveillance" (except in "support, not surveillance").
8. The acute safety path cannot be disabled by any kill switch, feature flag, or provider outage.
8a. No Anthropic services are used anywhere. All language models are Microsoft Foundry deployments on the team's Azure subscription (section 3.2).
9. Every screen has loading, empty, error, and offline states.
10. Accessibility is a requirement: WCAG 2.2 AA, keyboard navigable, screen-reader labels, 200% text zoom without breakage, reduced-motion respected.

---

## 2. Product map

### 2.1 Surfaces

| Surface | Route | Primary user | Priority |
|---|---|---|---|
| Saathi app (PWA) | `/app` | Personnel (constable first) | P0 |
| Welfare Console | `/welfare` | Unit Welfare Officer | P0 |
| Counsellor Desk | `/counsel` | Force counsellor | P1 |
| Medical Desk | `/medical` | Medical Officer | P0 (acute board), P1 (rest) |
| Command Console | `/command` | Company and Battalion Commanders | P0 |
| Force HQ | `/hq` | Sector and Force leadership | P1 |
| Governance (WDEC) | `/governance` | Welfare Data Ethics Cell | P0 (audit, fairness, kill switch), P1 (rest) |
| Rights and DPO Centre | `/dpo` | Data Protection Officer | P1 |
| Integration Console | `/integrations` | HRMS custodian, system admin | P1 |
| Admin | `/admin` | System admin | P1 |
| Validation Lab | `/lab` | Judges, engineers | P0 (core metrics), P1 (ablations) |
| Trust Centre | `/trust` | Everyone, including personnel and families | P1 |
| Architecture | `/architecture` | Judges | P0 |
| Demo Director | `/director` | Presenter | P0 |
| Stage | `/stage` | Presenter | P0 |
| Dial-in Saathi | phone number | Feature-phone users | P2 |

### 2.2 The demo spine (P0 flows that must be flawless)

1. Persona login to Saathi, language Hindi, consent cards, the one exception, consent receipt.
2. 20-second check-in and a Hindi voice check-in with captions.
3. Time travel on Arjun: baseline ribbon forms, drift detected, forecast turns Rising, case appears on the Welfare Console.
4. Case workspace: drivers, ranked levers, AI brief, identity reveal with purpose, the jawan's access ledger updates live.
5. Imran stays T1, Thomas stays T0 (corroboration and zero penalty).
6. Commander: formation grid, hidden tile, Copilot refusal, roster balancer projection.
7. Deepak's crisis disclosure: safety screen, T4 alert on Welfare and Medical in under 5 seconds, acknowledge.
8. Governance: fairness band, audit chain verify, tamper detection, kill switch.
9. Validation Lab: lead time, false-positive rate, shifted-world result.
10. Architecture: zones with live packets, demo vs sovereign mode.
11. Offline segment: mobile data off, check-in, structured voice check-in, toolkit, safety screen, SMS SOS, queued count, then resync and edge-queue drain (section 27).

### 2.3 What is real in the prototype and what is represented

| Capability | In the prototype | How it is presented |
|---|---|---|
| Offline capture and sync queue | **Real.** PWA with service worker, encrypted IndexedDB queue, idempotent resync. Cheap to build, runs in any browser. | Live demo with the airplane toggle. |
| Offline self-care toolkit and safety screen | **Real.** Cached assets and pre-rendered audio. | Live demo offline. |
| Offline crisis lexicon gate | **Real.** Runs in the browser before any network call. | Live demo offline. |
| On-device speech, on-device LLM (Tier A) | **Represented, with a real browser slice.** Rich voice and chat use Azure-hosted models behind the same adapter interface. A small in-browser model path (section 27.3) runs offline on the recording laptop. | Section 27 defines the wording and on-screen captions. |
| Battalion edge node (Zone 1) | **Represented.** A logical "edge" service boundary inside the backend that buffers and forwards. | Architecture page shows it as a separate zone with its own queue metrics. |
| On-prem LLM (sovereign mode) | **Real adapter.** The companion runs on gpt-oss-120b, an open-weight model that the force can host on its own GPU server; any OpenAI-compatible URL works. | Architecture page shows the same model name in both modes. |

Do not describe represented capabilities as running in the prototype. Say "designed for" and point to the adapter.

---

## 3. Technology stack

### 3.1 Application

| Layer | Choice |
|---|---|
| Web and PWA | Next.js 15 (App Router), React 19, TypeScript strict, Tailwind CSS v4, shadcn/ui (restyled), Framer Motion, TanStack Query, Zustand, visx and d3 (ribbon, heatmaps), Recharts (standard charts), cmdk, sonner, lucide-react, next-intl, Serwist (service worker), idb (IndexedDB), WebCrypto |
| Engine | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, pandas, numpy, scipy, scikit-learn, LightGBM, SHAP, ruptures, polars (fast rolling windows), statsmodels (seasonal adjustment), opensmile (eGeMAPSv02), APScheduler, openai SDK (Azure OpenAI v1 endpoint in Foundry, and sovereign OpenAI-compatible endpoints), azure-ai-contentsafety, azure-cognitiveservices-speech, azure-keyvault-keys, azure-identity, deepgram-sdk, httpx, structlog |
| Vault service | Python 3.12, FastAPI, cryptography, azure-keyvault-keys (wrap/unwrap), separate database and managed identity |
| Synthetic generator | Python package with CLI (Typer), numpy, pandas, Faker (Indian locales) plus a curated name list |
| Data | PostgreSQL 16 with extensions: `timescaledb` (Apache-2 edition on Azure, so do not rely on continuous aggregates or compression; use materialized views), `vector`, `ltree`, `pgcrypto`, `uuid-ossp` |
| Realtime | Azure Web PubSub (hosted) with a local fallback WebSocket hub for development |
| Cache and queues | Azure Managed Redis (or Azure Cache for Redis) for rate limits, locks, job queues (arq) |
| Object storage | Azure Blob Storage: pre-rendered TTS audio, exports, ruleset artefacts, model artefacts |
| Calls | Azure Communication Services (web voice and video calling between personnel and counsellors) |
| Telephony (P2) | Twilio or Exotel voice webhook for Dial-in Saathi; verify Azure Communication Services phone-number availability for India before choosing it |
| Push | Web Push (VAPID) from the backend; no third-party push SDK |
| Auth | Personnel: passkeys (WebAuthn via `@simplewebauthn`) plus 4-digit PIN fallback, JWT sessions. Officers: Microsoft Entra ID (OIDC, MFA). Demo: role cards that mint equivalent tokens. |
| Evals | promptfoo (or a pytest harness) for LLM evals and red-teaming |
| E2E tests | Playwright |
| IaC and deploy | Bicep plus Azure Developer CLI (`azd`), GitHub Actions |

### 3.2 AI and speech providers

| Capability | Primary | Fallback | Notes |
|---|---|---|---|
| Companion (text) | `open`: gpt-oss-120b deployed in Microsoft Foundry, if it passes the Hindi and Hinglish eval gate (section 23.3); otherwise `main` | `main` | gpt-oss is open-weight (Apache 2.0) and is designed to run on a single 80 GB GPU, so the prototype model is the production on-prem model |
| Companion (voice turns, low latency) | `fast`: a GPT-5.x mini or nano deployment | `open` | Voice needs time-to-first-token under 700 ms |
| Crisis classifier, output guard, extraction, brief verification | `fast` | `main` | Fail safe on error |
| Case briefs, Copilot, HQ brief, transparency report | `main`: a GPT-5.x chat deployment | `open` | |
| Optional non-personnel fallback | `alt`: Grok deployed in Foundry, or the xAI API | none | Never used for any personnel-facing or safety task; see section 33 |
| Safety classifier (third gate) | Azure AI Content Safety (self-harm category, Prompt Shields for injection) | none (gate simply abstains) | Its strongest language coverage may not include Hindi; treat as an additional gate, never the only one |
| Embeddings | Azure OpenAI `text-embedding-3-large` (dims reduced to 1024) | Voyage AI | |
| Translation (UI and content) | Azure AI Translator (covers 20 of the 22 scheduled languages per Microsoft's announcements) | `main` model for Sanskrit and Santali, flagged for review | Also use Translator transliteration for Hinglish in Latin script to Devanagari |
| STT English | Deepgram Nova-3 (streaming), Flux for end-of-turn detection | Azure AI Speech | |
| STT Hindi and Hinglish | Deepgram Nova-3 with `language=hi` when the user selected Hindi; `language=multi` for code-switched speech; keyterm prompting with the force glossary | Azure AI Speech `hi-IN` | Deepgram community reports show `multi` can misdetect Hindi and return Latin-script Hinglish; pin `hi` when known and transliterate |
| STT other Indian languages | Azure AI Speech (Indian locales) | text-only fallback | Verify each locale in the Speech docs |
| TTS English | Deepgram Flux TTS Indian-accent English voices (for example `flux-meena-en`, `flux-naveen-en`, `flux-priya-en`) | Deepgram Aura-2, Azure `en-IN` | |
| TTS Hindi | Azure AI Speech `hi-IN-SwaraNeural` with the empathetic style where supported; bilingual Hindi-English voices (for example `hi-IN-AaravNeural`, `hi-IN-AnanyaNeural`, `hi-IN-KavyaNeural`) for Hinglish | Azure `hi-IN-MadhurNeural` | Deepgram TTS does not currently offer Hindi |
| TTS other Indian languages | Azure AI Speech neural voices | text only | |
| Acoustic features | opensmile eGeMAPSv02 in the engine, in memory | disabled | |

Model classes (`main`, `fast`, `open`, `alt`) map to Foundry deployment names in configuration. Choose deployment types with the strictest data residency your subscription offers for the chosen model (regional or data zone before global) and show the choice on the Architecture page. Request quota early; credit-based subscriptions often start with low tokens-per-minute limits.

Model IDs, voice names, and language coverage change often. Keep them in configuration, never in code, and verify each against the provider documentation during setup.

### 3.3 Provider router

`services/engine/providers/router.py` implements:
- Ordered provider list per capability from config.
- Per-call timeout budgets (companion text 8 s, voice turn 3 s to first token, classifier 1.5 s, TTS first byte 800 ms).
- Circuit breaker per provider (open after 3 failures in 60 s, half-open after 30 s).
- Automatic fallback; the response records which provider served it.
- Safety rule: a classifier timeout or error returns `crisis=true`.
- Cost and latency metrics per provider to Application Insights.
- Director "resilience mode": scripted demo beats first try a cached response keyed by `(beat_id, language)`.

### 3.4 Repository

```
manobal/
  apps/web/                    Next.js: all consoles, Saathi PWA, stage, director
  services/engine/             FastAPI: ingest, features, risk, forecast, cases, alerts, acute,
                               incidents, aggregation, ai gateway, voice gateway, realtime, calls
    risk/ forecast/ cases/ acute/ incidents/ agg/ ai/ voice/ providers/ integrations/
    rights/ jitai/ lifecycle/ lab/ demo/
  services/vault/              FastAPI: identity vault
  services/synth/              generator CLI and scenario scripts
  packages/ui/                 design tokens and components
  packages/contracts/          OpenAPI TS client, zod schemas
  packages/i18n/               message catalogs (22 languages), glossary, validated-instrument texts
  infra/
    bicep/                     Azure resources
    docker-compose.yml         local development
    rulesets/                  signed YAML rulesets
    prompts/                   signed prompt files
    corpus/                    psychoeducation markdown (en, hi)
    lexicon/                   crisis lexicon files (clinician review required)
    audio/                     pre-rendered safety and toolkit audio manifest
  evals/                       LLM eval and red-team suites
  e2e/                         Playwright tests
  docs/
```

---

## 4. Roles and access

| Role | Can see | Can never see | Auth |
|---|---|---|---|
| `personnel` | Own data, trends, consents, access ledger, requests | Anyone else | Passkey or PIN |
| `buddy` (a personnel capability, not a separate account) | That their buddy asked for a check-in call; nothing else | Buddy's data, tier, or scores | Passkey or PIN |
| `uwo` Welfare Officer | Cases for assigned unit; identity only via case grant | Other units, numeric scores, enrolment status, counsellor notes | Entra ID + MFA |
| `counsellor` | Sessions assigned to them; anonymous requests; identity only if the person shares it | Cases they are not assigned to, scores | Entra ID + MFA |
| `mo` Medical Officer | T4 cases and referrals in jurisdiction | Non-referred cases, counsellor notes | Entra ID + MFA |
| `commander` | k-anonymous aggregates for own unit subtree | Any individual, token, case id, enrolment metrics | Entra ID + MFA |
| `hq` | Sector and force aggregates | Individuals | Entra ID + MFA |
| `wdec` | Audit (tokens only), fairness, accuracy, rulesets, agent turns (assistant side), enrolment integrity | Names, raw personal data | Entra ID + MFA |
| `dpo` | Rights requests, breach register, notices, retention jobs | Welfare content beyond what a request requires | Entra ID + MFA |
| `hrms_integrator` | Integration jobs, schema reports, quarantine | Any analytics output | Entra ID + MFA |
| `admin` | Org structure, role assignments, feature flags (except acute path) | Personal data | Entra ID + MFA |
| `director` | Demo controls | n/a | Demo only |

Enforcement:
- FastAPI dependency `require(scope, predicate)` on every route.
- Row predicates via `ltree`: `unit_path <@ :scope_path`.
- Postgres row-level security on `case`, `assessment`, `session`, `grievance` as defence in depth.
- A static route test asserts that no `commander` or `hq` route declares a parameter named or shaped like a token, case id, or person id.
- Officer assignments are time-bound (`valid_from`, `valid_to`). A transfer revokes the old assignment before the new one activates.

---

## 5. Synthetic world

### 5.1 Organisation (fictional)

- Force HQ, 4 sectors mapped to theatre types:
  - Sector North: J&K theatre (counter-insurgency, high altitude, extreme cold)
  - Sector Central: LWE theatre (jungle operations, heat, vector-borne illness exposure)
  - Sector East: North-East theatre (insurgency, monsoon, remote posts)
  - Sector Capital: static and VIP security duty (long standing hours, urban)
- 3 battalions per sector (`Bn N-01` to `Bn C-03`), 6 companies each (Alpha to Foxtrot, about 100 each), 3 platoons per company, 3 sections per platoon, detached posts of 7 to 9 people.
- About 7,200 personnel, 540 simulated days.
- Unit master data carries a coarse `climate_class` (cold, hot-humid, temperate) and `altitude_class` (plain, high), never live location.
- Rank bands: Constable/GD 70%, Head Constable 15%, ASI 5%, SI 5%, Inspector 2%, gazetted officers 3%.
- Enrolment about 42%; of enrolled: wearables about 35%, voice about 25%, companion about 60%.
- Fairness-only attributes (never features): gender, home region, primary language, tenure band, rank band, sector.
- Welfare staffing: 1 UWO per battalion, 1 counsellor per sector, 1 MO per battalion.

### 5.2 Causal generator

Order of generation (each step conditions on earlier ones):
1. Deployment calendar per company: induction, de-induction, rotations, operation flags, hard-area days.
2. Roster per person: shift starts, hours, night shifts, rest days, rest denials (driven by intensity and unit shortfall).
3. Leave: EL, CL, emergency short leave; approvals and rejections (driven by operations, shortfall, family events).
4. Life events: family illness, marriage, childbirth, land or property dispute, financial stress (base rates by home region band, never used as features).
5. Org events: transfer requests, duty swaps, training, grievances (linked to life events and workload).
6. Latent state per person: stress load accumulates from workload, hardship, and life events; recovers with rest and leave; 6% distress cohort with Weibull onset; recovery after effective interventions.
7. Sleep and HRV for wearable users (driven by roster and latent state).
8. EMA check-ins (mood, energy, sleep quality, sleep hours, tags); missingness rises with latent state and deployment.
9. Instruments on cadence (section 8.1 D5) with validated item-level generation.
10. Voice features for voice users: 88-dim vectors from a personal baseline plus small state-linked shifts.
11. Unit climate pulse responses (aggregate only).
12. Critical incidents (about 12 per year) affecting companies; post-incident latent-state bumps with individual variation.
13. Acute events for 0.4% of the cohort: 80% preceded by multi-domain drift, 20% sudden.
14. Gaming cohort 2%: suppresses self-report while org signals remain honest.
15. Ground truth: onset dates, acute dates, cohort labels (lab role only).

Two configurations:
- `world=primary` for the demo and model training.
- `world=shifted` for validation: different causal coefficients, noise, missingness, and a different mix of theatres. The forecast model never sees it during training.

CLI:
```
uv run synth generate --world primary --personnel 7200 --days 540 --seed 20260916
uv run synth generate --world shifted --personnel 3000 --days 540 --seed 7
uv run synth personas
uv run synth snapshot demo-baseline
uv run synth restore demo-baseline
```
Data volume rules (mandatory):
- Simulate all 540 days in memory with polars, but persist only: raw source rows (duty, leave, events, EMA, instruments, bio) as generated; `indicator_day` only for the eight personas plus a fixed 500-person sample; `domain_score` and `assessment` at weekly cadence for days 1 to 420 and daily cadence for days 421 to 540.
- Everything else is recomputed on demand from raw rows.
- Use `COPY` with binary format and drop secondary indexes during load.

Target: primary world under 3 minutes; restore under 20 seconds.

### 5.3 Hero personas

Each has a hand-scripted trajectory so outcomes are deterministic. Names are fictional and tagged "Synthetic".

| Case | Persona | Unit | Language | Story | Expected outcome | Demo use |
|---|---|---|---|---|---|---|
| MB-4091 | Ct/GD Arjun Rathore | Central, Bn C-02, Charlie | Hindi | 19 consecutive duty days, night-shift volatility, sleep 6.5 h to 4.2 h, mood falling, check-ins thinning | T3; drivers roster overtime and sleep loss; lever "48-hour rest cycle"; forecast Rising at least 21 simulated days before his synthetic crisis date | Time travel, case workspace, reveal |
| MB-2217 | HC Meena Kumari | East, Bn E-01, Alpha | Hindi | 14 months at a non-family station, two leave rejections, PSS-10 rising, CBI personal burnout rising | T2; "Prioritise pending earned leave"; leave planner shows a feasible window | Leave planner, T2 digest |
| MB-3380 | Ct/GD Imran Sheikh | North, Bn N-03, Delta | English | One bad week of sleep only | T1 self-only nudge; never reaches an officer | Corroboration proof |
| MB-1506 | SI Thomas Varghese | Capital, Bn C-01, Echo | English | Declined wearables and voice; stable | T0 | Zero-penalty proof |
| MB-5120 | Ct/GD Lalit Oraon | Central, Bn C-02, Bravo | Hindi | Unit IED incident (Director-triggered) | 72-hour check-in card, asks to talk, appears on Incident board; 28-day follow-up scheduled | Incident protocol |
| MB-6604 | Ct/GD Deepak Negi | North, Bn N-01, Foxtrot | Hinglish | Types or says a distress message | Crisis gates fire, safety screen, T4 in under 5 s | Acute path |
| MB-7342 | HC Rajesh Yadav | Central, Bn C-03, Delta | Hindi | Land dispute back home, grievance pending 60 days, duty swaps rising, sleep ok | T2; lever "Expedite grievance and legal-aid referral" | Grievance lever, HQ grievance trends |
| MB-8815 | Ct/GD Karthik Selvam | East, Bn E-02, Charlie | Tamil | Returning from long leave after a family bereavement | Lifecycle "return from leave" pathway, Tamil voice check-in | Multilingual voice, lifecycle |

---

## 6. Data model

All personal tables in `manobal_core` are keyed by `subject_token` (`st_` plus 16 base32 characters). No names, service numbers, phone numbers, or free-text identity exists in the core database.

### 6.1 Organisation and people

```
unit(id, path ltree unique, name, level, theatre, climate_class, altitude_class, parent_id)
subject(token pk, unit_path ltree, rank_band, tenure_band, enrolled bool, device_tier,
        lifecycle_state, lifecycle_since, created_at)
subject_audit_attrs(token pk, gender, home_region, language, sector)             -- wdec role only
officer(id, entra_oid, display_label, role, unit_path, valid_from, valid_to)
buddy_pair(id, token_a, token_b, unit_path, since, active)                      -- consented pairs only
```

### 6.2 Consent and rights

```
consent_ledger(id, token, data_type, purpose, action grant|withdraw, text_hash, lang, app_version, at)
  data_type: hr_derived | self_report | wearable | voice_features | ai_conversation |
             trend_share | buddy | family_line
consent_receipt(id, token, ledger_ids[], sha256, signature, at)
rights_request(id, token, kind access|correction|erasure|grievance|nomination, status, payload jsonb,
               opened_at, due_at, closed_at)
nominee(token pk, nominee_name_enc, relation, contact_enc, at)                   -- stored via vault
erasure_receipt(id, token, data_type, row_count, sha256, signature, at)
breach_register(id, detected_at, description, affected_count, board_notified_at, users_notified_at, status)
notice_version(id, lang, text_hash, published_at)
```

### 6.3 Source signals

```
duty_day(token, date, hours, shift_start, night bool, rest_day bool, rest_denied bool)      -- hypertable
leave_balance(token, as_of, el_days, cl_days, other jsonb)
leave_event(id, token, type EL|CL|HPL|emergency, applied_at, from_date, to_date, status, reason_code)
org_event(id, token, type transfer_request|duty_swap|training|grievance|posting_change, at, meta jsonb)
deployment_event(id, unit_path, type induction|de_induction|operation_start|operation_end, at)
incident(id, unit_path, type encounter|ied|casualty|colleague_death|accident|disaster, occurred_at, severity)
ema(id, token, at, mood, energy, sleep_quality, sleep_hours, tags text[], source app|voice|ivr)
instrument(id, token, at, kind, items jsonb, total, lang, validated bool, visibility shared|self_only)
bio_day(token, date, sleep_min, sleep_eff, rhr, hrv_rmssd, steps, spo2, wear_minutes)         -- hypertable
voice_features(id, token, at, egemaps real[88], duration_s, lang)
engagement_day(token, date, expected, completed)
climate_pulse(id, unit_path, week, question_id, response_bucket, n)                            -- aggregate only
grievance(id, token_hash, unit_path, category, text_enc, status, sla_due, opened_at, closed_at)
  category: leave | pay | housing | transfer | family | land_property | medical_admin | colleagues | other
```

### 6.4 Analytics

```
indicator_day(token, date, indicator, value, seasonal_adj_value)                   -- hypertable
baseline(token, indicator, regime_id, median, mad, n, window_end)
regime(id, token, started_at, reason posting_change|induction|return_from_leave|initial, warmup_until)
domain_score(token, date, domain, z, ewma, cusum, coverage, breached)
assessment(id, token, date, wsi, raw_tier, final_tier, corroborating_domains text[],
           trajectory, forecast_p, forecast_lo, forecast_hi, drivers jsonb, onset_date,
           limited_data bool, ruleset_version, model_version, created_at)                -- immutable
shadow_assessment(... same shape ..., ruleset_version)
nudge(id, token, kind, reason_codes text[], trigger, shown_at, dismissed_at, feedback)
jitai_log(id, token, rule_id, fired_at, delivered bool, suppressed_reason)
```

### 6.5 Cases, sessions, alerts

```
case(id 'MB-####', token, unit_path, tier, status, opened_at, sla_due_at, assigned_uwo,
     dominant_domains text[], recommended jsonb, source engine|incident|self_referral|acute)
case_action(id, case_id, actor, kind note|decision|contact|referral|followup|outcome, payload jsonb, at)
case_grant(id, case_id, actor, purpose_code, justification, granted_at, expires_at, revoked_at,
           contact_note_due_at)
breakglass(id, actor, approver, target_token, justification, at, wdec_review_status)
consent_request(id, case_id, token, kind trend_share, domain, status, at)
alert(id, case_id, tier, recipient, channel inapp|digest|push|sms|call, status, dedup_key, at, ack_at)
escalation_step(id, case_id, step, recipient, due_at, fired_at, ack_at)
self_referral(id, token, target uwo|counsellor_anon|counsellor_named, note_enc, status, at)
counsel_session(id, counsellor_id, token nullable, anon_handle, mode chat|voice|video,
                scheduled_at, started_at, ended_at, status, notes_enc)                   -- counsellor scope
safety_plan(token pk, content_enc, updated_at)                                          -- device-first, optional backup
access_ledger(id, token, actor_role, actor_label, action, purpose_code, at)              -- visible to the person
audit_log(seq bigserial, at, actor, action, object, meta jsonb, prev_hash, hash)
agent_session(id, token, mode, lang, channel text|voice|ivr, started_at, ended_at, crisis bool)
agent_turn(id, session_id, role assistant, text, mode, guard_result, provider, latency_ms, at)
wo_outcome_label(case_id, label helpful|not_needed|false_alarm|escalated, at)
```

### 6.6 Governance, system, simulation

```
ruleset(version, yaml, signature, signers text[], status active|shadow|draft, created_at)
model_registry(version, kind, metrics jsonb, card jsonb, artefact_uri, status, created_at)
killswitch(name, enabled, changed_by, at)
feature_flag(name, enabled, audience jsonb)
integration_job(id, source, kind csv|api|webhook, started_at, finished_at, status, rows_in,
                rows_quarantined, report jsonb)
quarantine_row(id, job_id, reason, redacted_payload jsonb)
data_quality(date, source, missingness, staleness_hours, drift_score)
corpus_chunk(id, doc_id, lang, title, text, embedding vector(1024), version)
ground_truth(token, world, distress_onset, acute_date, cohort)                           -- lab role only
sim_clock(id=1, sim_now timestamptz, speed, running bool)
provider_call(id, capability, provider, latency_ms, ok, cost_estimate, at)
```

**Simulated time:** every event row stores `sim_at` (simulated time) as its business timestamp and `created_at` (wall time) separately. All UI shows simulated time with a clock chip. All scheduling (nightly scoring, SLAs, escalations) runs off `sim_clock`. Escalation timers in the live demo use wall time compressed by a configurable factor so a 15-minute SLA can be shown in real seconds.

### 6.7 Vault database (`manobal_vault`)

```
identity(token pk, service_no_enc, name_enc, phone_enc, posting_enc, dek_wrapped, kek_version, created_at)
resolve_log(id, token, requester, case_id, purpose_code, at, hash, prev_hash)
nominee_store(token pk, payload_enc, dek_wrapped)
```
Token: `st_` + base32(HMAC-SHA256(key from Key Vault, service_no))[:16]. Field encryption: per-row AES-256-GCM data key, wrapped by an RSA-HSM key in Azure Key Vault. Only the vault's managed identity can use the wrap and unwrap operations.

---

## 7. Logical architecture

### 7.1 Zones (represented in the prototype as service and database boundaries)

| Zone | Prototype component | Holds | Talks to |
|---|---|---|---|
| Zone 0 Device | Saathi PWA | Encrypted queue, safety plan, journal, self-only instruments, lexicon | Zone 1 only |
| Zone 1 Edge | `engine.edge` router with its own queue table and metrics | Buffered packets, sync state | Zone 2 |
| Zone 2 Analytics | `engine` core modules, `manobal_core` DB | Tokens and derived data only | Zone 3 only through grant-bound calls |
| Zone 3 Identity | `vault` service, `manobal_vault` DB, Key Vault keys | Identities, nominees | Nothing outbound except audit events |
| Zone X Blocked | none | Appraisal, promotion, posting, medical categorisation, disciplinary systems | No route exists; CI test asserts no client, env var, or URL for them |

### 7.2 Key flows

**Check-in:** PWA writes packet to IndexedDB, returns instantly, service worker posts batch to `/edge/sync`, edge validates signature and schema, dedups on packet id, acknowledges, forwards to core ingestion, realtime event `sync.batch` animates the Architecture page.

**Nightly scoring:** sim clock hits 02:00, scheduler runs `risk.run(date)` partitioned by sector, writes assessments, cases, nudges, and alerts, emits events.

**Identity reveal:** officer submits purpose, engine issues a grant JWT (signed with a Key Vault key), vault verifies grant, unwraps data key through Key Vault, decrypts, returns identity, writes resolve log, engine writes access ledger and audit entries, Saathi receives `identity.resolved` and updates the ledger.

**Acute:** see section 10.

---

## 8. Analytics engine

### 8.1 Domains and indicators

| Domain | Weight | Source | Indicators (+ means higher is adverse) |
|---|---|---|---|
| D1 Workload and duty | 0.18 | HRMS | duty_hours_7d (+), duty_hours_28d (+), consecutive_duty_days (+), night_shift_ratio_28d (+), roster_volatility_28d (+), rest_denials_28d (+), quick_returns_14d (+, shifts starting under 11 h after the previous ended) |
| D2 Leave dynamics | 0.15 | HRMS | days_since_last_leave (+), leave_rejections_90d (+), short_leave_fano_28d (+), leave_apply_rate_delta (abs), unplanned_absence_28d (+), el_balance_unused_ratio (+) |
| D3 Hardship and context | 0.12 | HRMS and unit master | family_separation_days (+), hard_area_days_365 (+), climate_hardship_days_90 (+), incident_exposure_30d (+), transfer_requests_180d (+), duty_swap_rate_delta (+), grievance_open_age_max (+) |
| D4 Body vitals | 0.18 | Wearable (opt-in) | sleep_minutes_7d (-), sleep_efficiency_7d (-), sleep_midpoint_variability_14d (+), hrv_rmssd_7d (-), resting_hr_7d (+), activity_delta (abs) |
| D5 Wellness self-report | 0.22 | App | ema_mood_7d (-), ema_energy_7d (-), ema_sleep_q_7d (-), pss10 (+, monthly), cbi_personal and cbi_work (+, monthly), who5 (-, fortnightly), phq9 (+, fortnightly when enrolled for it), gad7 (+, fortnightly when enrolled for it) |
| D6 Vocal acoustics | 0.08 | Voice (opt-in) | Robust Mahalanobis distance of eGeMAPS vector from personal baseline; F0 variability, jitter, shimmer, speech rate deltas |
| D7 Engagement cadence | 0.07 | App | checkin_completion_14d (-), response_latency_delta (+). Silence is weak evidence by design. |

Self-only instruments (never scored, never leave the device): AUDIT-C (alcohol use), a private sleep diary, private journal. Verify licensing for every instrument before release; WHO-5 and AUDIT-C are published by WHO; PHQ-9 and GAD-7 are widely distributed without fees; confirm terms for PSS-10 and CBI.

### 8.2 Baselines

- Trailing 90-day window per indicator, median and `1.4826 * MAD`, minimum 21 observations.
- **Regimes:** a posting change, induction into a new theatre, or return from leave longer than 20 days opens a new regime. During a 21-day warm-up, the baseline is a weighted blend of the previous regime (weight falling linearly from 0.7 to 0) and a cohort prior (same rank band, same theatre).
- **Cold start:** before 21 observations, shrink toward the cohort prior with weight `n/21`; mark `limited_data`.
- **De-seasonalisation:** subtract weekday effects and rotation-phase effects (STL or grouped medians) before computing deviations.
- **Floors:** `mad_floor_i` per indicator prevents very stable people from being flagged for trivial absolute changes.

### 8.3 Deviation and domain scores

```
z_i      = direction_i * (x_adj - median) / max(mad_scaled, floor_i)
zhat_i   = clip(z_i / 3, 0, 1)
ewma_i   = 0.3 * zhat_i + 0.7 * ewma_i(prev)
domain_Z = mean(ewma_i over available indicators in domain)
coverage = available / expected
cusum_d  = max(0, cusum_d(prev) + domain_Z - k_d)      # k_d from ruleset
breached = (domain_Z >= threshold_d) or (cusum_d >= h_d)
```
A domain participates only when `coverage >= 0.6` and its consent is granted.

### 8.4 Composite and tier

```
WSI = sum(w_d * domain_Z) / sum(w_d)        over participating domains
raw_tier: T0 < 0.35 <= T1 < 0.55 <= T2 < 0.75 <= T3
if count(breached) < 2:  final = min(raw, T1)                  # corroboration
if final < previous and lower_cycles < 2: final = previous      # hysteresis
if acute_trigger: final = T4                                    # override
limited_data = participating weight share < 0.5
```

### 8.5 Change points and onset

`ruptures` PELT with an RBF cost on WSI and on each breached domain over the last 120 days. The earliest change point within the current elevated episode becomes `onset_date`. UI phrase: "Drift began about N days ago".

### 8.6 Forecast

- Target: reaches T2 or higher within the next 14 days.
- Features: domain_Z, 7/14/28-day slopes per domain, CUSUM values, coverage per domain, days since onset, regime age, lifecycle state, incident exposure, theatre, tenure band.
- Excluded, always: gender, home region, language, religion, caste, any free text.
- LightGBM, monotone constraints so higher adverse deviations can never lower risk, isotonic calibration, subject-grouped temporal split.
- Interval: split-conformal on the calibrated probability, shown as low/high in Governance only.
- Outputs: `forecast_p`, `forecast_lo`, `forecast_hi`, SHAP top 3.
- Authority: `rising` at T0 creates a T1 self-only nudge. The forecast never lifts a tier above T1 without corroboration.

Trajectory: `rising` if `forecast_p >= 0.5` or 14-day WSI slope above +0.01 per day; `falling` if slope below -0.01; else `stable`.

### 8.7 Drivers

SHAP features and breached domains map through `infra/rulesets/phrases.yaml` into plain language, in every UI language. Examples: `consecutive_duty_days` "Long stretch without a rest day"; `leave_rejections_90d` "Leave requests not approved recently"; `sleep_minutes_7d` "Less sleep than usual"; `grievance_open_age_max` "A concern has been pending for a long time".

### 8.8 Ruleset

Signed YAML in `infra/rulesets/v1.0.0.yaml` (weights, tier bounds, domain thresholds, CUSUM k and h, min corroboration, hysteresis cycles, baseline params, coverage min, SLAs, acute triggers, k-anonymity, JITAI caps). Ed25519 signature by two WDEC keys (from Key Vault). Every assessment stores the ruleset version. `v1.1.0-shadow` runs in parallel into `shadow_assessment`.

### 8.9 Validation

- Primary world: temporal hold-out.
- Shifted world: never seen in training; report the drop.
- Metrics: precision, recall, F1 at T2+, AUROC, AUPRC, Brier score, calibration curve, lead time (days from detected onset or T2 to ground-truth distress peak or acute event), alert burden per 1,000 per month, subgroup parity.
- Ablations: no corroboration, no hysteresis, no renormalisation, population baseline, no regimes, no CUSUM.
- Physiology sanity check (P2): run the D4 feature pipeline on WESAD and report whether HRV features shift between baseline and stress conditions. Import results as JSON.
- Performance: nightly run of 7,200 in under 60 s using polars rolling windows over the last 90 days only; change-point detection runs only for people whose WSI is above 0.35 (typically under 15%); SHAP only for people whose tier or trajectory changed. The benchmark endpoint scores 80,000 generated subjects in memory and reports wall time.

---

## 9. Interventions, JITAI, lifecycle

### 9.1 Lever library (`infra/rulesets/interventions.yaml`)

| Code | Label | Owner |
|---|---|---|
| `REST_48H` | Sanction a 48-hour rest cycle | UWO recommends, commander approves (company-level) |
| `ROSTER_NIGHT_ROTATE` | Rotate off night duty for 7 days | UWO, commander |
| `ROSTER_QUICK_RETURN_FIX` | Remove quick-return shifts for 14 days | Commander |
| `LEAVE_PRIORITISE` | Prioritise pending earned leave | UWO, commander |
| `LEAVE_SHORT_FAMILY` | Approve short family leave | UWO, commander |
| `FAMILY_CONNECT` | Arrange a private video call home | UWO |
| `GRIEVANCE_EXPEDITE` | Expedite pending administrative grievance | UWO, admin branch |
| `LEGAL_AID_REFERRAL` | Connect with legal aid for a land or family dispute (legal services authority or force legal cell) | UWO |
| `FINANCE_COUNSEL` | Financial counselling session | UWO |
| `INFORMAL_CHAT` | Informal one-to-one conversation, no paperwork | UWO |
| `BUDDY_CHECKIN` | Ask the buddy (if paired and consented) to check in, without sharing any details | UWO sends a neutral prompt |
| `CONFLICT_RESOLUTION` | Facilitated conversation for a colleague conflict | UWO |
| `SLEEP_SUPPORT` | Sleep session and quiet billet arrangement | UWO |
| `YOGA_GROUP` | Unit yoga or breathing session | UWO, commander |
| `COUNSELLOR_OFFER` | Offer a confidential counsellor session | UWO |
| `MO_REFERRAL` | Refer to Medical Officer (maximum clinical step) | UWO |
| `POST_INCIDENT_CHECKIN` | Voluntary post-incident check-in | UWO |
| `REINTEGRATION_CHAT` | Return-from-leave or post-transfer welcome conversation | UWO |
| `NO_ACTION` | No action needed (always available, never penalised) | UWO |

Ranking: base rank from `(tier, dominant_domain, lifecycle_state)`; adjusted by observed de-escalation rate within 21 days in similar cases; filtered by unit constraints (operation flag, minimum strength). The LLM only rephrases and suggests conversation openers.

### 9.2 Closed loop

Every decision records the lever; every closure records an outcome. HQ shows lever effectiveness (observational, clearly labelled as not causal). Lever ranking updates weekly.

### 9.3 JITAI self-care prompts [P1]

Rules in `infra/rulesets/jitai.yaml`, delivered only to the person, capped at 1 prompt per day and 4 per week, never during a scheduled duty window, silenced by "Not now" for 72 hours.

| Rule | Trigger | Prompt |
|---|---|---|
| `NIGHT_TOMORROW` | Night shift starts within 24 h | Nap and light plan for tonight |
| `DUTY_STREAK_10` | 10th consecutive duty day | 5-minute recovery routine |
| `QUICK_RETURN` | Next shift starts under 11 h after the last | Wind-down audio and caffeine timing tip |
| `LEAVE_WINDOW` | Leave balance high and a feasible window exists | Leave planner suggestion |
| `POST_INCIDENT` | Unit incident within 72 h | Check-in window card |
| `LOW_SLEEP_3` | Three nights under personal baseline | Sleep toolkit |
| `SILENCE_7` | No check-in for 7 days | Gentle "we are here" card, no guilt |
| `BIRTHDAY_AWAY` (P2) | Family event date flagged by the user | Family connect reminder |

### 9.4 Lifecycle pathways [P1]

States: `recruit`, `pre_induction`, `inducted`, `de_induction`, `on_leave`, `return_from_leave`, `post_transfer`, `pre_retirement`.
Each state changes check-in cadence, toolkit ordering, JITAI rules, and baseline regime handling. Example: `return_from_leave` shows a 3-day "settling back" card and opens a new regime if leave was longer than 20 days.

---

## 10. Acute path and safety protocol

### 10.1 Triggers
PHQ-9 item 9 above 0; any crisis gate in Saathi text, voice, journal (if the user chose to scan it), or IVR; SOS with "ask someone to call me"; self-referral marked urgent; Director trigger.

### 10.2 Sequence (target under 5 s end to end in the demo)
1. Device shows the human-authored safety screen immediately; works offline; plays pre-rendered audio in the user's language.
2. Out-of-band acute packet to `/acute` (bypasses batch sync; offline retry every 10 s; screen says "Trying to reach your unit" and keeps helplines visible).
3. Engine creates T4 assessment and case, logs legal basis "vital interest" (verify the exact DPDP clause for medical emergency before citing it).
4. Automatic case grant, vault resolve, access ledger entry for the person.
5. Parallel alerts to UWO and MO: push, SMS (simulated or provider), call (simulated or provider); 15-minute SLA; escalation after 5 minutes without acknowledgement to Company Commander's welfare deputy, then Battalion MO, then sector counsellor.
6. WDEC notified with a distinct audit category.
7. The LLM never runs on the triggering message. The companion session ends with a fixed script.

### 10.3 Safety screen content
- Calm layout; the T4 colour appears only on call buttons.
- One-tap calls: Tele-MANAS 14416 (national mental health helpline), force helpline (configurable), "Ask my welfare officer to call me" (preselected).
- 60-second grounding exercise with audio.
- "My safety plan" shortcut if the user has one.
- "Send SOS by SMS" (prefilled `sms:` link to the configured unit number) for no-data situations.
- Status line: "A person is being asked to reach you" with progress.

### 10.4 My safety plan [P1]
A personal plan built by the user, stored on device (optional encrypted backup), modelled on the structure of the Safety Planning Intervention (warning signs, coping steps, people and places for distraction, people to ask for help, professionals to contact, making the environment safer). Verify template terms before using its exact wording. Never shared with officers.

### 10.5 Officer acute guide [P1]
Shown on the Medical Desk and Welfare case for T4: a human-authored checklist following force SOP (stay with the person, reach them in person, involve MO, follow force policy on the environment around them). If the force adopts a structured screener such as the Columbia Suicide Severity Rating Scale screener, show it as a human-administered guide only, with training reminder; verify licensing and force approval. The system never computes a suicide-risk score.

### 10.6 Pre-rendered audio
Safety scripts, grounding, and breathing audio are generated at build time in all supported TTS languages, reviewed by a human, stored in Blob Storage, and cached by the service worker. Live TTS is never used on the safety screen.

---

## 11. Critical-incident protocol [P0 core, P1 follow-up]

- Trigger: `POST /incidents` (HMAC-signed webhook) or Director.
- Within one simulated minute: every enrolled member of the affected unit sees "Your unit went through something hard. A private check-in is open for 72 hours." with psychological first aid content (based on WHO Psychological First Aid principles), PC-PTSD-5 offer (validated languages only), and "I want to talk".
- Follow-up at about 28 days: a second voluntary check-in (timing modelled on peer-led trauma risk management practice in other militaries).
- Nobody is flagged for not responding.
- Commander sees an aggregate incident card: window status, number of people who asked to talk (only if at least 10 personnel in the unit and the count is suppressed below 3 as "a few").
- UWO Incident board lists only people who asked to talk.
- HQ tracks incident exposure by theatre.

---

## 12. AI layer

### 12.1 Gateway
`ai.run(task, inputs, lang)`:
- Loads a signed prompt file for the task.
- Binds user content as a typed parameter inside XML-style delimiters; never concatenates it into the system prompt.
- Applies temperature caps, max tokens, stop rules.
- Routes via provider router; records provider, latency, cost estimate.
- Runs output guard; replaces U+2014 and U+2013 with commas; strips markdown where the channel is voice.
- Logs assistant output only.
- Respects kill switches (`agent`, `voice`, `copilot`, `briefs`).

### 12.2 Tasks

| Task | Model class | Temp | Allowed input | Output |
|---|---|---|---|---|
| `companion_turn` | `open` or `main` (text), `fast` (voice) | 0.3 | Sanitised user text, mode, language, top-k corpus chunks, current-session memory only, tier band (T0 to T2 vs T3+) | Streamed reply; tool calls |
| `checkin_extract` | `fast` | 0 | Session turns | JSON mood, energy, sleep_quality, sleep_hours, tags (nulls allowed) |
| `instrument_conversational` | `main` | 0.2 | Validated item text | Asks items verbatim; maps answers to item scores through a tool; confirms each |
| `crisis_classify` | `fast` | 0 | Sanitised text | `{crisis, confidence, category}`; error or timeout returns crisis |
| `output_guard` | `fast` plus lexicon | 0 | Draft reply | pass or block with reason; block sends fixed safe fallback |
| `case_brief` | `main` | 0.2 | Tier, domain labels, driver phrases, onset, trajectory, lifecycle, lever list | 4 sentences with field references, 3 conversation openers in the officer's chosen language |
| `brief_verify` | `fast` | 0 | Brief plus field set | pass or list of unsupported claims |
| `command_copilot` | `main` | 0.2 | Question plus aggregate tools | Answer and chart spec; refuses individual-level questions |
| `hq_brief` | `main` | 0.3 | Force aggregates | Monthly brief (markdown) |
| `transparency_report` | `main` | 0.3 | Governance metrics | Public-style report |
| `grievance_triage` | `fast` | 0 | Grievance text (encrypted at rest, decrypted in memory) | Category, urgency, PII redaction for aggregate display |
| `translate_ui` | Azure Translator (`main` for gaps) | n/a | Catalog plus glossary | Cached translations flagged machine-translated |
| `conversation_coach` (P2) | `main` | 0.4 | Officer's practice text | Feedback on a practice welfare conversation with a simulated jawan persona |

### 12.3 Companion pipeline (every turn, text and voice)

```
input
 -> [1] sanitiser: strip role tokens, markup, instruction-like patterns; cap 1,000 chars
 -> [2a] lexicon gate (also runs in the browser before sending)
 -> [2b] crisis_classify (fast model)       } OR-combined, any positive or any error
 -> [2c] Azure Content Safety self-harm      }   -> acute path, fixed script, no LLM reply
 -> [2d] Prompt Shields (injection)          -> if attack: safe refusal, log, continue session
 -> [3] mode router: checkin | ask | reflect  (reflect disabled at T3+ and by kill switch)
 -> [4] companion_turn (ask mode: RAG only, must cite chunk ids, else offer a person)
 -> [5] output_guard: no diagnoses, no medication names, no clinical labels, no promise of
        total secrecy, no operational details, grounded-only in ask mode
 -> reply (text, and TTS for voice)
```

### 12.4 Companion prompt essentials (`infra/prompts/companion.v2.md`)
- Identity: Saathi, a welfare companion inside MANOBAL. Not a doctor, counsellor, or officer.
- Voice: warm, brief (2 to 4 sentences; 1 to 2 in voice mode), respectful, uses "aap" in Hindi, mirrors the user's language and code-mixing, no lectures, no emojis in voice.
- Cultural fit: understands duty, leave, roster, barracks, family far away, festival duty, without assuming religion, caste, or region.
- Modes: check-in (natural conversation, then `record_checkin`), ask (corpus only), reflect (listen, reflect, one gentle question, no advice).
- Always: offer human options when difficulty is expressed; respect "I don't want to talk about it".
- Never: diagnose, name medications, judge, discuss other personnel, discuss operations or locations, promise nobody will ever know, argue about leave decisions, criticise commanders.
- Operational security: if the user mentions locations or movements, do not repeat them; gently note Saathi does not need those details.
- Tools: `record_checkin`, `suggest_toolkit_item`, `offer_human_contact`, `open_leave_planner`, `open_safety_plan`. No tool writes assessments or cases.

### 12.5 RAG corpus
25 to 30 team-written documents in English and Hindi with frontmatter (`id, title, lang, reviewed_by, version`): sleep on rotating shifts, tactical napping, recovering after night duty, caffeine timing, box breathing, grounding, anger after a hard day, talking to family during long deployments, staying close to children from far away, what a welfare conversation is, what counsellors do, how MANOBAL uses your data, the one safety exception, leave planning, return from leave, starting in a new posting, money stress basics, handling a land or property dispute (where to get legal aid), alcohol and sleep (non-judgemental), after a critical incident (PFA), grief, conflict with a colleague, heat and cold stress basics, loneliness, being a buddy. Chunk about 400 tokens, embed, store.

---

## 13. Voice layer

### 13.1 Session architecture
- Browser captures 16 kHz mono PCM via AudioWorklet, streams over WebSocket to `/voice/session`.
- Browser-side VAD (Silero VAD web build or WebRTC VAD) for hands-free mode; push-to-talk also available.
- Engine opens a streaming STT connection to the selected provider, receives interim and final results, shows live captions.
- On end of turn (Deepgram Flux end-of-turn events for English, endpointing for Nova-3, Azure segmentation for others), the final transcript enters the companion pipeline (section 12.3).
- Reply text streams to TTS sentence by sentence; audio streams back; barge-in stops playback and cancels the pending TTS.
- If the user has voice-feature consent, the engine buffers the utterance audio in memory, runs opensmile eGeMAPSv02, stores only the 88 values, zeroises the buffer, and emits `audio.cleared` with elapsed milliseconds.
- Demo banner: "Demo mode: speech is processed by a cloud service. In deployment this runs on the phone or your unit's server."

### 13.2 Language routing

| User language | STT | TTS voice |
|---|---|---|
| English | Deepgram Nova-3 English with Flux end-of-turn | Deepgram Flux Indian-accent English voice (configurable) |
| Hindi | Deepgram Nova-3 `language=hi` with keyterms | Azure `hi-IN-SwaraNeural` (empathetic style where supported) |
| Hinglish | Deepgram Nova-3 `language=multi` with keyterms; transliterate Latin-script Hindi to Devanagari with Azure Translator before gating | Azure bilingual Hindi-English voice |
| Tamil, Bengali, Telugu, Marathi, Kannada, Malayalam, Gujarati, Punjabi, Odia, Assamese, Urdu (as available) | Azure AI Speech locale | Azure neural voice for that locale |
| Others | Text only in that language; voice button explains why | none |

Keyterms (force glossary): MANOBAL, Saathi, roster, duty, chutti, EL, CL, company, platoon, post, battalion, welfare officer, counsellor, Tele-MANAS, and common rank abbreviations.

### 13.3 Latency budget (voice turn)
End of speech to first audio under 1.8 s: end-of-turn 300 ms, gates 400 ms (lexicon instant; classifier and Content Safety in parallel with a 1.2 s cap that fails safe), LLM first sentence 700 ms (`fast` deployment), TTS first byte 300 ms. Show a subtle "thinking" orb state if exceeded.

### 13.4 Voice check-in UX
- Orb reacts to input amplitude and output audio.
- Captions for both sides, with language chip.
- "Audio cleared" chip.
- End summary: what was saved (structured values only); "Save as private journal" stores the transcript locally, encrypted, never synced by default.

### 13.5 Dial-in Saathi [P2]
Phone number via Twilio or Exotel. IVR: language choice by keypad, three voice questions (mood, sleep, "anything you want to tell us"), same gates, crisis goes to acute path with caller ID resolved only through vault if the number is registered. Short, fixed prompts from pre-rendered audio.

---

## 14. Privacy, security, rights

### 14.1 Controls
1. Two databases, two services, two managed identities; the engine identity has no access to the vault database or vault keys. Startup self-test proves it; Architecture page shows the result with timestamp.
2. Directional vault API: `/tokenise` accepts only the ingest identity; `/resolve` accepts only a grant JWT signed with the engine's Key Vault grant key, bound to case, actor, purpose, expiry.
3. Resolve rate limit 5 per officer per hour; anomalies (out-of-unit, bursts, odd hours) alert WDEC.
4. Grants expire after 14 days or case closure; a contact note is required within 24 hours of reveal or the grant revokes and WDEC is notified.
5. Break-glass requires typed justification and a second officer's approval; WDEC reviews every instance; the person sees it in the access ledger.
6. Trend disclosure needs the person's in-app approval per domain per case.
7. Consent withdrawal stops collection instantly; purge job deletes raw rows of that type (demo: immediately; stated policy: within 24 hours); signed erasure receipt.
8. Opt-out invisibility: no officer or commander endpoint exposes enrolment; non-enrolled personnel are assessed on org domains only and look identical to enrolled T0 people.
9. Audit hash chain: `hash = sha256(prev_hash || canonical_json(entry))`; verify endpoint; daily anchor hash written to immutable Blob Storage (versioning plus immutability policy).
10. Access ledger visible to the person for every identity resolve, trend view, break-glass, and rights request action.
11. Transport: TLS everywhere; HSTS; strict CSP; CORS locked; security headers.
12. Sessions: 15-minute access tokens, refresh rotation, device binding for personnel passkeys.
13. PII redaction middleware for logs; no request bodies logged for personnel routes.
14. PWA storage: IndexedDB encrypted with AES-GCM; key derived from PIN with PBKDF2 (310,000 iterations or current OWASP guidance) into a non-extractable CryptoKey; auto-lock after 2 minutes idle.
15. Kill switches: `agent`, `voice`, `copilot`, `briefs`, `alerts_t2_t3`, `forecast`, `jitai`. The acute path has no switch.
16. k-anonymity everywhere aggregates appear, including the simulator, Copilot tools, exports, and trend cells.
17. Zone X firewall test in CI.

### 14.2 Rights Centre (personnel side, inside Saathi) [P1]
- Read the privacy notice in my language (versioned, hash shown).
- See my data (structured download JSON and a readable PDF summary).
- Correct my data (for self-report entries and HR-derived facts; HR corrections create a request to the HRMS custodian).
- Erase a data type (with receipt).
- Nominate a person to exercise my rights if I am unable to.
- Raise a grievance with the DPO; track status and due date.
- See who accessed what and why.

### 14.3 DPO console [P1]
Rights request queue with due dates; notice versions per language; retention jobs and their last run; breach register with a workflow (detect, assess, notify Board, notify users) and templates; export of processing records.

### 14.4 Trust Centre (public page) [P1]
Plain-language explanation for personnel and families: what is collected, what is never collected (no location tracking, no call monitoring, no social media, no always-on microphone), the tiers, the one exception, who can see what (visual matrix), the WDEC and how to complain, the latest transparency report, and the open synthetic-data repository. Available in all UI languages with audio read-aloud.

---

## 15. Integrations

### 15.1 HRMS connector [P1]
- Upload CSV (roster, leave, deployment, transfers, grievances) or push JSON to `/integrations/hrms/batch`.
- Schema contract (JSON Schema per feed, versioned); violations go to quarantine with redacted previews.
- Tokenisation at the boundary through the vault; the UI shows "identifiers removed" with a before/after preview using synthetic data.
- Data-quality report per run: row counts, missingness, staleness, distribution drift (PSI); alerts when thresholds are crossed.
- Incremental and idempotent; job history with replay.

### 15.2 Incident webhook [P0]
HMAC-signed JSON; replay protection with timestamp and nonce.

### 15.3 Wearables [P1]
- Simulated device panel (default).
- Real Web Bluetooth Heart Rate Service (0x180D) for live demo with a chest strap or compatible watch (Chrome desktop or Android).
- Health Connect or HealthKit integration is future work; say so.

### 15.4 Calls [P1]
Azure Communication Services web calling for counsellor sessions (voice and video), with a pre-call device check and "anonymous handle" display for anonymous sessions. No recording. Call metadata only (start, end) is stored.

### 15.5 Notifications [P0 in-app, P1 web push]
Web Push with VAPID for officers and personnel; content is always the fixed minimal string. SMS and phone calls simulated in the demo unless a provider is configured.

---

## 16. Design system

> Detailed, binding UI direction lives in `docs/04_MANOBAL_UI_DIRECTION.md` (UI v3). It refines this section and wins where they differ.

### 16.1 Direction
Two skins on one token system.
- **Saathi (personnel):** calm, warm, spacious, voice-first, icon plus text on every action, big touch targets (minimum 48 px), usable with one thumb during a duty break, readable in bright sunlight (high-contrast option).
- **Command (all officer, governance, admin consoles):** monsoon-slate dark by default with a daytime light theme, dense and precise, brass accents from insignia metal, khaki neutrals from the uniform.

Signature elements (spend boldness only here):
- **Baseline ribbon:** every personal trend shows the person's own 90-day median inside a soft band; values outside the band get a small marker. The ribbon is also the logo motif and the loading animation.
- **Formation grid:** commander heatmap of companies, platoons, and posts; suppressed cells render as hatched tiles with a lock glyph.

### 16.2 Tokens

| Token | Hex | Use |
|---|---|---|
| `neem-700` | #2F5D50 | Saathi primary |
| `neem-100` | #E4EFEA | Saathi surfaces |
| `mist-50` | #F5F8F7 | Saathi background |
| `monsoon-950` | #131C24 | Command background |
| `monsoon-800` | #1E2A35 | Command panels |
| `brass-400` | #C8A24A | Command accent, focus rings |
| `khaki-300` | #C9BB8E | Command secondary text and dividers |
| `ink-900` | #1B2127 | Body text on light |
| T0 Steady | #6E927F | circle icon |
| T1 Watch | #4D8BAE | drop icon |
| T2 Elevated | #D6A13D | triangle icon |
| T3 High | #D06A34 | diamond icon |
| T4 Acute | #B83A2E | octagon icon; only for T4 and call buttons |
| `hidden` | 45 degree hatch on `monsoon-800` | suppressed cells |

Tier is never communicated by colour alone. Check every pairing for WCAG AA in both themes; adjust lightness per theme.

### 16.3 Typography
- **Anek** (variable width; Latin and several Indic scripts): headings and numerals; condensed width for dense tables and KPI numerals.
- **Mukta**: body for Latin and Devanagari.
- Noto Sans families as fallbacks for other scripts (Tamil, Telugu, Kannada, Malayalam, Gujarati, Gurmukhi, Odia, Bengali and Assamese if not covered, Meitei Mayek, Noto Nastaliq Urdu for Urdu and Kashmiri with right-to-left layout).
- Scale (px): 12, 14, 16, 20, 24, 32, 44. Saathi body 17; Command body 14. Tabular numerals in tables. No all-caps labels. Sentence case.
- Right-to-left layout supported for Urdu, Kashmiri, and Sindhi (logical CSS properties throughout).

### 16.4 Layout
- Saathi: single column, bottom tabs (Home, Saathi, Toolkit, Me), persistent SOS top right, status strip under the header.
- Command: collapsible left rail, top bar (unit switcher limited to scope, simulated clock chip, mode chip, language, notifications, profile), 12-column grid.
- Stage: phone frame on the left, console on the right, Director drawer at the bottom (demo only).

### 16.5 Motion
One orchestrated moment per surface: ribbon draw-in on Saathi home; brass pulse on new case; full-width T4 banner with timer; packets moving on Architecture. Everything else is instant or a short fade. Respect reduced motion.

### 16.6 Components (`packages/ui`)
`TierBadge`, `TrajectoryArrow`, `LimitedDataTag`, `DomainChip`, `DriverList`, `BaselineRibbonChart`, `FormationGrid`, `HiddenTile`, `SlaTimer`, `EscalationLadder`, `CaseCard`, `LeverOption`, `BriefPanel` (with field-reference hover), `ConsentToggleCard`, `ReceiptCard`, `AccessLedgerItem`, `AuditRow`, `ChainStatus`, `KpiTile`, `FairnessBar`, `ReliabilityChart`, `PhoneFrame`, `OfflineChip`, `SyncQueueIndicator`, `AudioClearedChip`, `VoiceOrb`, `CaptionStream`, `SOSButton`, `EmojiScale`, `LanguageGrid`, `ValidatedBadge`, `MachineTranslatedBadge`, `ModeChip`, `SimClock`, `EmptyState`, `ErrorState`, `ProviderBadge` (Governance only), `ZoneDiagram`, `CallPanel`, `SafetyPlanEditor`, `LeaveWindowPicker`, `ShiftTimeline`.

### 16.7 Copy
- Personnel: second person, short, kind. "You have been on duty 11 days in a row. A short recovery routine can help."
- Officers: factual and non-judgemental. "Contributing: Roster overtime, Sleep loss."
- Errors: what happened and what to do next.
- No streaks, no scores, no guilt, no exclamation marks in personnel flows.

---

## 17. Surfaces

### 17.1 Saathi app (`/app`, PWA)

#### 17.1.1 Onboarding [P0]
1. Language grid (22 scheduled languages in their own scripts) with audio greeting.
2. Sign in: service number and OTP (demo shows the OTP), then create a passkey or a 4-digit PIN. Demo: persona picker.
3. Three cards: "Support, not surveillance", "Your commander never sees you", "You control your data".
4. Consent cards per data type, each with toggle, "What leaves your phone", "Who can ever see this", and "Change anytime". Defaults: HR-derived on (explained), all others off.
5. The one exception card with "I understand".
6. Consent receipt (hash, time, download).
7. Optional: set up buddy, safety plan, wearable. All skippable.
8. Device check card: "This phone: Tier A or Tier B" with what it means.

#### 17.1.2 Home [P0]
- Greeting in selected language with simulated time of day.
- Today's check-in card or "Done for today" with ribbon snippet.
- Context cards (at most two, prioritised): T1 nudge with "Why am I seeing this?", incident window, JITAI prompt, leave window suggestion, pending trend-share request.
- Quick actions: Talk to Saathi, Breathe 2 minutes, Talk to a counsellor, Plan my leave, Raise a concern.
- Status strip: offline chip, queued count, last sync, wearable status.
- SOS always visible.
- Optional "shift today" strip from roster (start, end, next rest day).

#### 17.1.3 Daily check-in [P0]
Three `EmojiScale` rows (Mood, Energy, Sleep quality), sleep hours stepper, optional tags (Duty, Family, Health, Money, Colleagues, Leave, Land or property, Nothing specific). "Say it instead" opens voice. Completion shows a short affirmation and updates the ribbon. Under 20 seconds.

#### 17.1.4 Saathi companion [P0 text and Hindi/English voice, P1 other languages]
Orb, captions, mode tabs (Check in, Ask, Talk it through), language chip, privacy banner, audio-cleared chip, end-of-session summary, save as private journal, crisis handoff overlay.

#### 17.1.5 Assessments [P0 PSS-10 and PHQ-9, P1 rest]
List with due dates and badges (Validated translation, Self-only). One question per screen, large options, read-aloud, back allowed. Results in supportive, non-diagnostic language with suggestions. PHQ-9 item 9 above 0 enters the safety screen. Instruments: PSS-10, WHO-5, CBI (personal and work subscales), PHQ-9, GAD-7, PC-PTSD-5 (incident only), AUDIT-C (self-only). Conversational mode available (Saathi asks items verbatim).

#### 17.1.6 Toolkit [P0 breathing and grounding, P1 rest]
Box breathing and 4-7-8 (animated, haptics), 5-4-3-2-1 grounding, 10-minute sleep wind-down (pre-rendered audio per language), short yoga nidra, body scan, post-duty decompression, tactical nap guide, heat and cold stress tips, anger cool-down, "Letter home" prompt, private journal, articles from the corpus with audio read-aloud. Everything works offline.

#### 17.1.7 Plan my rest [P1]
- **Leave planner:** EL and CL balance from HRMS, operational blackout windows (unit-level only), suggested windows, travel-day estimate entered by the user, "Draft leave request" that the user copies or sends through the normal channel (MANOBAL does not submit leave).
- **Shift and sleep planner:** roster timeline for the next 7 days with suggested sleep windows, nap slots, and light and caffeine timing for night shifts.

#### 17.1.8 Talk to a person [P0 request, P1 calls]
- Request a conversation with my Welfare Officer (identity shared by my choice).
- Talk to a counsellor anonymously (anonymous handle) or with my name.
- Book a slot or "call now if someone is free"; voice or video via Azure Communication Services.
- Status tracking for requests.

#### 17.1.9 My safety plan [P1]
Guided editor (section 10.4), audio prompts, stored on device, optional encrypted backup, quick access from the safety screen.

#### 17.1.10 Buddy [P1]
- Pair with a buddy by mutual consent (QR code or code exchange within the same unit).
- Buddy can send and receive "Check in with me" pings and one-tap "I'm okay" replies.
- Buddy learns how to support: short lessons on noticing and listening, and how to ask for help from the UWO.
- A buddy never sees any data, tier, or score. The UWO can send a neutral "please check in with your buddy" prompt only when the person has consented to buddy involvement.
- Unpair anytime without notification.

#### 17.1.11 Family connect [P2]
- Call reminders at chosen times and around family dates.
- Shareable family resources link (no personal data): how to support someone far away, Tele-MANAS, force family welfare contacts.
- Family concern line: a family member can reach the sector counsellor anonymously; no flag is created in MANOBAL unless the person consents after the counsellor reaches out.

#### 17.1.12 Me [P0 trends, privacy, ledger; P1 rest]
- My trends: ribbon charts (mood, energy, sleep, duty hours, days since leave), 30 or 90 days, "limited data" tags.
- Privacy and rights (section 14.2), access ledger, consent receipts, privacy switch (pause all sync).
- Requests: trend-share approvals, referral status, counselling bookings.
- Concerns: raise a grievance (category, text, optional anonymity), track status and SLA.
- Unit pulse (P1): one anonymous question per week, answered in one tap; results never shown individually.
- Trust pulse (P1): "I believe this system exists to support me" (monthly, anonymous) for KPI K10.
- Settings: language, text size, high contrast, voice speed, voice choice, app lock, dark mode.

#### 17.1.13 Offline behaviour [P0]
Airplane toggle (Director and Settings in demo). Offline: captures queue with visible count; toolkit, safety screen, lexicon gate, and safety plan work; acute packet retries. Online: animated sync; Architecture page shows packets moving from Zone 0 to Zone 1 to Zone 2.

### 17.2 Welfare Console (`/welfare`)

#### 17.2.1 Queue [P0]
Header (unit, open cases by tier, overdue, my capacity against a recommended maximum). Tier sections with T4 pinned and live timer; sorting by SLA due time only. `CaseCard`: case id, tier, trajectory, limited-data tag, domain chips, "Drift began about N days ago", recommended lever, SLA timer, status, source. Filters and tabs: Queue, Incident check-ins, Self-referrals, Follow-ups due, Closed, Digest (T2 daily digest view).

#### 17.2.2 Case workspace [P0]
- Timeline: tier steps over 120 days, onset marker, incident and lifecycle markers, action markers.
- What changed: domain chips with driver phrases.
- Recommended actions: ranked levers with rationale, "often helpful in similar situations" hint, constraints note, and "No action needed".
- AI brief with field-reference hovers, language selector, 3 conversation openers, "AI-written, check before use" label.
- Trend disclosure request per domain with live status.
- Identity panel: locked; purpose code and justification to reveal; identity card (synthetic tag, rank, unit, contact, posting); grant countdown; "This person will see that you viewed their identity."; contact-note reminder.
- Actions: contacted (mode), decision (lever or none), follow-up date, refer to counsellor or MO, buddy prompt (if consented), close with outcome.
- Every action writes case action, audit entry, and a realtime event.

#### 17.2.3 Other tabs [P1]
Incident check-ins (only people who asked), self-referrals, follow-ups, grievance-linked cases (category only), my workload trend, conversation practice (P2, `conversation_coach`).

### 17.3 Counsellor Desk (`/counsel`) [P1]
Session calendar; anonymous and named requests; join call (ACS); private notes (counsellor scope only, encrypted); referral to MO; "suggest welfare lever" to the UWO without sharing notes (only a lever code and a consented summary sentence); caseload view.

### 17.4 Medical Desk (`/medical`)
- [P0] Acute board: T4 cases, 15-minute timers, escalation ladder, acknowledge, call (simulated or provider), outcome.
- [P1] Referrals from UWO and counsellors with minimum necessary context; acute guide (section 10.5); follow-up scheduling.

### 17.5 Command Console (`/command`)

#### 17.5.1 Unit posture [P0]
Formation grid (companies expand to platoons and posts; 12 weeks), banded share at T2+, hidden tiles with explanation tooltip; KPI tiles (duty hours, rest denials, night load, quick returns, leave backlog, median days since leave, incident exposure, open grievance age); aggregate drivers; aggregate alerts; nothing resolves to a person; no enrolment numbers.

#### 17.5.2 Roster balancer [P0 projection, P1 draft order]
Company sliders: weekly duty hours, rest days, night share, quick-return cap, leave release per week. "Project 14 days" shows projected posture and coverage side by side. Groups under 10 cannot be simulated alone. "Create draft order" produces a printable company-level note.

#### 17.5.3 Leave pressure [P1]
Backlog by company, longest-waiting bands, release plan that keeps minimum strength.

#### 17.5.4 Unit climate [P1]
Anonymous weekly pulse trends (k-anonymous), colleague-conflict tag trend, grievance categories and ages.

#### 17.5.5 Command Copilot [P0]
Streaming chat with aggregate tools (`get_unit_metrics`, `get_posture`, `simulate_roster`, `list_top_drivers`, `get_grievance_trends`). Inline charts. Refusal for individual-level questions with a helpful aggregate alternative. Suggested questions in Hindi and English.

### 17.6 Force HQ (`/hq`) [P1]
Theatre comparison (posture, workload, leave, incidents, grievances) over 18 months; schematic sector board (use an official-boundary map only if an official file is supplied); welfare capacity vs demand with recommended counsellor redeployment; lever effectiveness (observational); retention pressure (aggregate transfer requests and exit-intent tags); policy simulator (leave approval rate, max consecutive duty days, rotation length, quick-return cap) with projected force posture; monthly AI brief with edit and PDF export.

### 17.7 Governance (`/governance`)
- [P0] KPIs: K1 lead time, K3 false-positive rate (from outcomes), alert burden, SLA adherence, K10 trust index, K11 break-glass rate, K12 parity, K13 offline capture success, K14 agent safety. Definitions on hover.
- [P0] Fairness: flag rates and disparate impact ratio by rank band, gender, region, language, tenure, sector, with the 0.8 to 1.25 band.
- [P0] Audit: searchable (tokens only), anomalies, `ChainStatus` verify, daily anchor status.
- [P0] Kill switches.
- [P1] Accuracy: FP and FN over time, reliability chart, shadow ruleset agreement.
- [P1] Break-glass and reveal reviews (sampled), purpose-code analytics.
- [P1] Ruleset registry: versions, YAML diff, signatures, two-signer activation, shadow toggle.
- [P1] Model registry and model card: data (synthetic), features, excluded attributes, metrics on primary and shifted worlds, limitations.
- [P1] Agent safety: gate hit rates by gate, guard trips per 1,000 turns, provider mix, sampled assistant turns, lexicon version.
- [P1] Enrolment integrity: force-level trend; units with anomalous uniformity flagged as possible coercion.
- [P1] Grievances and contests.
- [P1] Provider health: latency, failures, fallbacks.
- [P1] Transparency report generator.

### 17.8 DPO Centre (`/dpo`) [P1]
Section 14.3.

### 17.9 Integration Console (`/integrations`) [P1]
Section 15.1 UI: sources, schedules, run now, upload CSV, schema versions, quarantine viewer (redacted), data-quality charts, tokenisation preview, webhook tester for incidents.

### 17.10 Admin (`/admin`) [P1]
Org tree editor (synthetic), officer assignments with validity dates, role mapping to Entra groups, feature flags (acute path not listed), language catalog status (machine-translated vs reviewed), corpus manager (upload, review status, re-embed), audio manifest (pre-rendered clips and review status), lexicon versions.

### 17.11 Validation Lab (`/lab`)
- [P0] Confusion matrix at T2+, precision, recall, F1, AUROC, AUPRC, lead-time histogram and median, alert burden, primary vs shifted world toggle.
- [P1] Calibration and Brier, ablations with cached reruns, zero-penalty proof (opt-out vs opt-in flag rates for equal latent state), regime ablation, benchmark button, WESAD panel (P2).

### 17.12 Architecture (`/architecture`) [P0]
Animated zone diagram (Zone 0, 1, 2, 3, X blocked) driven by realtime events; self-tests (analytics cannot reach identity, command routes have no individual parameters, audit chain intact, Zone X unreachable); mode panel (demo vs sovereign) listing what changes; provider map (Governance data, read-only).

### 17.13 Trust Centre (`/trust`) [P1]
Section 14.4.

### 17.14 Landing (`/`) [P0]
One calm screen: the problem with sourced statistics (source and date shown under each number), the promise "Support, not surveillance", the ribbon motif, and role cards for demo login. A second fold shows the four PS expected-solution components mapped to screens.

### 17.15 Demo Director (`/director`, Ctrl+K palette) [P0]
- Simulated clock: date, play and pause, speed, +1 day, +1 week, +30 days, "Run nightly scoring now".
- Persona time-travel slider.
- Scenarios: Arjun drift to T3; Imran one bad week; Thomas opts out; Meena leave pressure; Rajesh grievance; Lalit IED incident; Karthik return from leave (Tamil); Deepak crisis (auto-type or auto-speak option); Commander drill-down attempt; tamper audit row and restore; go offline and online; provider outage simulation (forces fallback).
- Resilience mode toggle (cached outputs for scripted beats).
- Reset to snapshot.
- Stage presets for each demo beat.

---

## 18. Realtime and notifications

- Transport: Azure Web PubSub (hub `manobal`), groups per role and unit path; local fallback hub in development.
- The engine publishes; clients subscribe with a short-lived token that encodes allowed groups.
- Filtering happens server-side before publishing: commander and HQ groups receive aggregate events only; personnel receive only their own events.
- Event types: `clock.tick`, `checkin.received`, `sync.batch`, `edge.buffer`, `assessment.created`, `nudge.created`, `case.opened`, `case.updated`, `alert.dispatched`, `alert.acknowledged`, `acute.triggered`, `escalation.step`, `identity.resolved`, `consent.changed`, `trend_share.requested`, `trend_share.decided`, `incident.created`, `audit.verified`, `audit.tampered`, `killswitch.changed`, `provider.fallback`, `audio.cleared`, `integration.job`.
- Notification centre in every console with read state; Web Push for officers and personnel (fixed minimal text only).

---

## 19. API (engine, prefix `/api/v1`)

```
# auth
POST /auth/demo-login                 POST /auth/otp/request   POST /auth/otp/verify
POST /auth/passkey/register/options   POST /auth/passkey/register/verify
POST /auth/passkey/login/options      POST /auth/passkey/login/verify
GET  /auth/entra/callback

# edge and personnel
POST /edge/sync                        (batch of signed packets, idempotent)
POST /acute                            (out-of-band)
GET  /me/home     GET /me/trends?metric&days     GET /me/roster?days
GET  /me/instruments/due     POST /me/instruments/{kind}
GET  /me/consents POST /me/consents   POST /me/purge/{data_type}   GET /me/receipts
GET  /me/access-ledger
GET  /me/requests POST /me/requests/{id}/decision
POST /me/self-referrals   GET /me/self-referrals
POST /me/grievances       GET /me/grievances
GET  /me/nudges   POST /me/nudges/{id}/feedback
GET  /me/leave/plan       POST /me/leave/draft
GET  /me/sleep/plan
POST /me/buddy/pair       POST /me/buddy/ping   POST /me/buddy/unpair
POST /me/pulse            POST /me/trust-pulse
GET  /me/rights           POST /me/rights/{kind}   GET /me/export
POST /me/safety-plan/backup   GET /me/safety-plan/backup
POST /companion/turn      (SSE)
WS   /voice/session
POST /calls/token         (ACS user token)   POST /counsel/requests

# welfare
GET  /welfare/queue   GET /welfare/digest
GET  /welfare/cases/{id}
POST /welfare/cases/{id}/actions
POST /welfare/cases/{id}/grant           {purpose_code, justification}
POST /welfare/cases/{id}/trend-request   {domain}
GET  /welfare/cases/{id}/brief?lang
POST /welfare/cases/{id}/close           {outcome}
POST /welfare/breakglass                 {target_hint, justification, approver}
GET  /welfare/incidents   GET /welfare/self-referrals   GET /welfare/workload

# counsellor and medical
GET  /counsel/sessions   POST /counsel/sessions/{id}/notes   POST /counsel/sessions/{id}/suggest-lever
GET  /medical/acute      POST /medical/acute/{id}/ack        GET /medical/referrals

# command (aggregate only; no token, case, or person parameters exist)
GET  /command/posture?unit&weeks
GET  /command/metrics?unit&metric&period
POST /command/simulate
GET  /command/leave-pressure?unit
GET  /command/climate?unit&weeks
GET  /command/grievances?unit
POST /command/copilot                    (SSE)
POST /command/draft-order

# hq
GET  /hq/theatres  GET /hq/capacity  GET /hq/levers  GET /hq/retention
POST /hq/policy-sim  POST /hq/brief

# governance and dpo
GET  /gov/kpis  GET /gov/fairness  GET /gov/accuracy  GET /gov/audit  POST /gov/audit/verify
GET  /gov/reviews  POST /gov/reviews/{id}
GET  /gov/rulesets  POST /gov/rulesets/{v}/sign  POST /gov/rulesets/{v}/activate
GET  /gov/models  GET /gov/agent-safety  GET /gov/enrolment-integrity  GET /gov/providers
GET  /gov/killswitches  POST /gov/killswitches/{name}
POST /gov/transparency-report
GET  /dpo/requests  POST /dpo/requests/{id}  GET /dpo/breaches  POST /dpo/breaches
GET  /dpo/notices   POST /dpo/notices

# integrations and admin
POST /integrations/hrms/upload   POST /integrations/hrms/batch
GET  /integrations/jobs  GET /integrations/jobs/{id}  GET /integrations/quality
POST /incidents                          (HMAC webhook)
GET/POST /admin/units  GET/POST /admin/officers  GET/POST /admin/flags
GET/POST /admin/corpus GET /admin/audio  GET /admin/i18n

# lab, system, demo
GET  /lab/metrics?world&ablation   POST /lab/benchmark
GET  /system/selftest   GET /system/mode   GET /system/health
POST /realtime/negotiate
POST /demo/clock  POST /demo/scenario/{name}  POST /demo/reset
POST /demo/tamper POST /demo/restore  POST /demo/network  POST /demo/outage/{provider}
POST /demo/resilience
```

Vault: `POST /tokenise`, `POST /resolve`, `POST /nominee`, `GET /health`.

All responses use a consistent error envelope: `{ "error": { "code", "message", "hint" } }`. All list endpoints paginate with cursors.

---

## 20. Azure deployment

### 20.1 Resources (Bicep in `infra/bicep`)

| Resource | Purpose | Notes |
|---|---|---|
| Resource group per environment | `rg-manobal-demo` | Region: Central India where every service is available; otherwise South India. Record any service that runs outside India (for example model endpoints) on the Architecture page. |
| Azure Container Apps environment (VNet-integrated) | `engine`, `vault` (separate app, internal ingress only), `web` (or App Service), jobs | Container Apps Jobs for nightly scoring, purge, retention, anchors |
| Azure Container Registry | Images | |
| Azure Database for PostgreSQL Flexible Server x2 | `core` and `vault` on separate servers | PostgreSQL 16; enable `timescaledb`, `vector`, `ltree`, `pgcrypto` via server parameters; private endpoints; Entra authentication |
| Azure Key Vault (Premium) | KEK (RSA-HSM), token HMAC key, grant signing key, ruleset signing keys, VAPID keys | Separate access policies: vault identity can wrap/unwrap KEK; engine can sign grants; neither can do the other's operation |
| Azure Managed Redis | Rate limits, locks, queues | |
| Azure Web PubSub | Realtime | |
| Azure Blob Storage | Audio, exports, artefacts, audit anchors (immutability policy) | |
| Azure AI Speech | STT and TTS for Hindi and Indian languages | |
| Azure AI Translator | UI and content translation, transliteration | |
| Azure AI Content Safety | Self-harm gate, Prompt Shields | |
| Microsoft Foundry | Deployments: `main` (GPT-5.x chat), `fast` (GPT-5.x mini or nano), `open` (gpt-oss-120b, needs a Foundry project), embeddings; optional `alt` (Grok) | Content filters on for every deployment; region and deployment type recorded |
| Azure Communication Services | Counsellor voice and video calls | |
| Microsoft Entra ID | Officer sign-in, app roles mapped to MANOBAL roles | |
| Azure Front Door with WAF | TLS, WAF rules, caching of static assets | |
| Application Insights and Log Analytics | Telemetry, traces, provider metrics | PII redaction enforced in code |
| Managed identities | One per app | No connection strings with passwords |

Local development mirrors this with Docker Compose (Postgres with extensions, Redis, a local WebSocket hub, Azurite for Blob, and a local key file standing in for Key Vault, clearly marked dev-only).

### 20.2 CI/CD
GitHub Actions: lint, type-check, unit tests, copy-lint, privacy tests, evals (recorded), build, SBOM, container scan, deploy with `azd` to the demo environment, smoke tests, Playwright demo-script run against the deployed URL.

### 20.3 Environment variables (names only; values from Key Vault or App Config)

```
MANOBAL_MODE, WEB_ORIGIN, SIM_TIME_COMPRESSION
CORE_DB_HOST, CORE_DB_NAME                       (engine identity)
VAULT_DB_HOST, VAULT_DB_NAME                     (vault identity only)
REDIS_URL, WEBPUBSUB_ENDPOINT, BLOB_ENDPOINT
KEYVAULT_URI, KV_KEK_NAME, KV_TOKEN_KEY_NAME, KV_GRANT_KEY_NAME, KV_RULESET_KEYS, KV_VAPID
FOUNDRY_ENDPOINT (Entra auth via managed identity)
AI_DEPLOYMENT_MAIN, AI_DEPLOYMENT_FAST, AI_DEPLOYMENT_OPEN, AI_DEPLOYMENT_EMBED
AI_DEPLOYMENT_ALT (optional), XAI_API_KEY (optional, non-personnel tasks only)
SOVEREIGN_LLM_BASE_URL (optional)
CONTENT_SAFETY_ENDPOINT
TRANSLATOR_ENDPOINT, TRANSLATOR_REGION
SPEECH_REGION, SPEECH_ENDPOINT
DEEPGRAM_API_KEY, DG_STT_MODEL_EN, DG_STT_MODEL_HI, DG_TTS_VOICE_EN
AZ_TTS_VOICE_HI, AZ_TTS_VOICE_HINGLISH, AZ_TTS_VOICE_MAP (json)
ACS_CONNECTION (or endpoint + identity)
TWILIO_* or EXOTEL_* (optional)
ENTRA_TENANT_ID, ENTRA_CLIENT_ID
HELPLINE_PRIMARY=14416, HELPLINE_FORCE
INCIDENT_WEBHOOK_SECRET
```

---

## 21. Reliability and demo resilience

- Provider router with fallbacks and circuit breakers (section 3.3).
- Resilience mode for scripted beats: cached LLM outputs, pre-rendered TTS, recorded STT transcripts keyed by beat and language.
- Pre-warm: Director "Warm up" button calls every provider once and shows green or red per capability.
- Degradation order: JITAI and briefs, then Copilot, then voice, then companion, then dashboards; acute path last and never disabled.
- Health page `/system/health` with dependency status.
- Snapshot reset under 20 seconds; the Director refuses to start a scenario while a reset is running.
- Two browser profiles prepared for the stage (phone and console) with passkeys pre-registered.
- Offline demo tested with DevTools network throttling and the airplane toggle.
- A 90-second screen recording of the full spine kept locally as the last-resort fallback.

---

## 22. Observability and cost

- OpenTelemetry traces across web, engine, vault; trace ids in the error envelope.
- Dashboards: request latency by route, voice turn latency breakdown, gate latencies, provider fallback counts, nightly run duration, queue depth, Web PubSub connections.
- Cost guard: per-capability daily budget; when exceeded, switch to the cheaper model class and show a Governance banner.
- Prompt caching for long system prompts and corpus chunks where the provider supports it.
- Cache translations and TTS by content hash.

---

## 23. Testing, evals, acceptance

### 23.1 Unit and integration
- Engine core (baselines, regimes, de-seasonalisation, z, EWMA, CUSUM, renormalisation, corroboration, hysteresis, cold start, floors, forecast authority, k-anonymity with complementary suppression and churn, hash chain, grants, purge): pytest with 90% coverage on these modules.
- Vault: token determinism, envelope encryption round trip, grant verification, rate limit.
- API contract tests from OpenAPI.

### 23.2 Privacy suite (CI gate)
- Fuzz every command and HQ route with token-like, case-like, and name-like parameters; assert no individual data.
- Engine identity cannot connect to vault database or use vault keys.
- Suppressed cells contain no numeric fields; complementary suppression holds on synthetic edge cases.
- Simulator refuses groups under 10.
- Enrolment status absent from all officer and commander payloads (schema scan).
- Zone X unreachable (no env var, URL, or client).
- Purge removes rows and issues a receipt.
- Audit tamper detected.

### 23.3 LLM evals and red team (CI gate on recorded runs, nightly live)
- 120 cases minimum across English, Hindi (Devanagari), Hinglish (Latin script):
  - direct and indirect distress (must route to acute path),
  - injection attempts and role-play jailbreaks,
  - requests for diagnosis or medication,
  - operational details and locations,
  - requests to identify other personnel,
  - abusive language (must stay calm and non-judgemental),
  - "promise you won't tell anyone" (must be honest about the one exception),
  - ask-mode questions outside the corpus (must offer a person, not improvise).
- Metrics: crisis recall (target 100% on the suite), false crisis rate (report), guard trip correctness, groundedness, language match, U+2014 and U+2013 absence.
- Copilot suite: 30 individual-seeking questions must be refused; 30 aggregate questions must be answered with correct numbers.
- Brief suite: every sentence must pass `brief_verify`.
- Model routing gate: run the companion suite on `open` and `main` in English, Hindi, and Hinglish; `open` serves a language only if it matches `main` on crisis handoff (both must be 100%), language match, and groundedness within a small margin. Record the routing decision in the model registry.

### 23.4 E2E
Playwright runs the full demo script (section 24) on `/stage`, including: T4 under 5 s, ledger update on reveal, hidden tile, Copilot refusal, tamper detection and restore, offline resync without duplicates, Hindi voice turn using recorded audio fixtures.

### 23.5 Quality bar
- Lighthouse on Saathi: installable PWA, performance 90+ on mobile, accessibility 95+.
- axe clean on all consoles; keyboard-only walkthrough of the demo spine.
- WCAG AA contrast in both themes; 200% zoom; right-to-left check in Urdu.
- No console errors; no unhandled rejections.
- Copy lint: no U+2014, no U+2013, no banned words.

### 23.6 Acceptance checklist
- [ ] Local and Azure environments deploy from scratch with one command each
- [ ] Seed under 3 minutes; reset under 20 seconds
- [ ] All eight personas behave as specified
- [ ] Demo spine passes E2E twice in a row with a reset between
- [ ] Voice works in English and Hindi end to end with captions and audio-cleared chip; Tamil works for Karthik
- [ ] Crisis suite recall 100%; acute path under 5 s
- [ ] Privacy suite green
- [ ] Validation Lab shows primary and shifted world metrics computed live
- [ ] Rights Centre flows complete with receipts
- [ ] Integration Console quarantines a malformed CSV and shows the report
- [ ] Provider outage simulation falls back without user-visible failure
- [ ] Architecture self-tests all green

---

## 24. Demo script (8 minutes)

| Time | Beat | Screens |
|---|---|---|
| 0:00 | The problem in one screen with sourced numbers; "Support, not surveillance" | Landing |
| 0:30 | Saathi onboarding in Hindi: consent cards, the one exception, receipt | Stage phone |
| 1:20 | 20-second check-in, then Hindi voice check-in with captions and audio-cleared chip | Stage phone |
| 2:10 | Time travel on Arjun: ribbon forms, drift detected, forecast Rising 3 weeks ahead; case slides into the queue | Director, phone, Welfare |
| 3:10 | Case workspace: drivers, ranked levers, Hindi brief; reveal identity with purpose; phone's access ledger updates | Welfare, phone |
| 4:00 | Imran stays T1, Thomas stays T0, explained in two sentences | Lab or Welfare |
| 4:25 | Commander: formation grid, hidden Post Delta-7 tile, Copilot refusal in Hindi, roster projection | Command |
| 5:15 | Deepak's Hinglish disclosure: safety screen with audio, T4 on Welfare and Medical with timer, acknowledge | Stage split |
| 6:05 | Governance: fairness band, verify chain, tamper, red, restore; kill switch shows acute path cannot be disabled | Governance |
| 6:50 | Validation Lab: lead time, false-positive rate, shifted-world result; honest note on synthetic data | Lab |
| 7:20 | Offline: data off on the phone, check-in, toolkit, SMS SOS; data back on, sync drains through the edge queue; zones, identity separation self-test, demo vs sovereign mode | Stage phone, Architecture |
| 7:45 | Close: PS expected-solution components mapped to what they just saw | Landing second fold |

Backup beats if time allows: Karthik's Tamil voice check-in; Rajesh's grievance lever; incident protocol for Lalit; leave planner for Meena.

---

## 25. Build plan

| Phase | Content | Priority | Rough effort (person-days) |
|---|---|---|---|
| 1 | Monorepo, compose, databases, migrations, auth (demo, passkey, Entra), design tokens, shells, copy-lint | P0 | 6 |
| 2 | Synthetic generator (primary and shifted), personas, snapshots | P0 | 5 |
| 3 | Engine core (indicators, de-seasonalisation, regimes, baselines, scores, tiers), tests | P0 | 7 |
| 4 | Forecast, change points, drivers, levers, cases, alerts, escalation, acute, incidents | P0 | 7 |
| 5 | Vault with Key Vault, grants, ledger, audit chain and anchors, k-anonymity, consent and purge | P0 | 6 |
| 6 | Saathi core (onboarding, home, check-in, assessments, toolkit, me, offline queue, safety screen) | P0 | 8 |
| 7 | AI gateway, provider router, gates, companion text, corpus, evals | P0 | 6 |
| 8 | Voice (Deepgram English and Hindi, Azure Hindi TTS and other locales), audio-cleared, pre-rendered audio | P0 | 6 |
| 9 | Welfare Console, Medical acute board | P0 | 6 |
| 10 | Command Console with Copilot and balancer | P0 | 5 |
| 11 | Governance core, Validation Lab core, Architecture, Director, Stage, realtime | P0 | 7 |
| 12 | Azure deployment, CI/CD, E2E of the spine | P0 | 4 |
| 13 | Counsellor Desk and calls, leave and sleep planners, buddy, safety plan, JITAI, lifecycle | P1 | 8 |
| 14 | HQ, DPO and Rights Centre, Trust Centre, Integration Console, Admin | P1 | 8 |
| 15 | Governance extensions, lab ablations, languages beyond Hindi and English, polish | P1 | 6 |
| 16 | Dial-in Saathi, family connect, WESAD panel, conversation coach | P2 | 5 |

Build order is by vertical slice, not by layer: polished, fixture-driven screens first (so every slice is visible early), then real data and decisions behind them, then AI and voice, then the full Saathi app, then officer surfaces, then trust, proof, and shipping. The combined Cursor prompts follow this order.

Parallelise across the team: one owner each for engine, AI and voice, Saathi, consoles, platform and Azure, data and lab. Freeze features 5 days before the round; the last days are rehearsal, bug fixing, and resilience checks.

---

## 26. Honest limitations and Q&A preparation

### 26.1 Limitations to state before a judge asks
- All data is synthetic; the model's accuracy on real personnel is unknown until a silent pilot with alerts disabled calibrates it.
- The shifted-world test reduces, but does not remove, the risk that the model learned the generator.
- Voice biomarkers have a weak and language-sensitive evidence base; that is why their weight is the second lowest and they are opt-in.
- Rich voice and chat in the prototype run on Azure-hosted models; the production design runs the same open-weight model on force hardware, with small models on capable phones.
- Clinical instruments are offered only in languages with validated translations.
- Lever effectiveness shown on HQ is observational, not causal.
- The crisis lexicon and all safety content require review by qualified clinicians before any real use.

### 26.2 PS expected-solution mapping (show this slide-free, in the Landing second fold)

| PS component | Where it is |
|---|---|
| Personnel Wellness Monitoring Dashboard | Welfare Console, Command Console, Force HQ |
| Mobile-based Wellness and Self-Assessment Application | Saathi PWA |
| Predictive Behavioral Analytics Engine | Engine (baselines, regimes, CUSUM, change points), Validation Lab |
| Stress and Burnout Risk Prediction Models | 14-day forecast with calibration and drivers; CBI burnout domain |
| Welfare Intervention Recommendation System | Lever library, ranking, closed loop, JITAI |
| Role-based Access Control and Privacy Management Framework | Roles, grants, vault, Rights Centre, DPO Centre, Trust Centre |
| Automated Alerts for authorized welfare personnel | Tiered alerts, escalation ladder, acute path |
| Data anonymization and secure storage mechanisms | Tokenisation, envelope encryption with Key Vault, k-anonymity, audit chain |
| Secure integration with HRMS | Integration Console |

### 26.3 Likely questions and where the answer is shown
- "How do you avoid false alarms?" Corroboration, hysteresis, CUSUM, K3 on Governance, ablation in Lab.
- "What if a commander wants names?" Hidden tile, Copilot refusal, route-scan self-test.
- "What stops a welfare officer from snooping?" Purpose codes, rate limits, contact-note rule, WDEC sampling, the person's own access ledger.
- "What if someone opts out?" Zero-penalty proof in Lab; opt-out invisibility.
- "Is this AI or rules?" Forecast plus drivers plus calibration; rules decide, humans act.
- "Does it work without network?" Offline segment recorded with the phone genuinely in airplane mode: capture, structured voice check-in, toolkit, safety screen, lexicon gate, local nudges, then resync. Rich AI conversation needs the unit server, exactly as the architecture describes.
- "Which AI models?" Open-weight gpt-oss for the companion (hostable on force hardware), GPT-5.x on Azure for officer briefs, all behind content filters and our own gates.
- "Why would a jawan use it?" Leave planner, sleep planner, counsellor calls, safety plan, buddy, voice in their language, nothing reaches the commander.
- "Which laws?" DPDP Act 2023 and Rules 2025 (rights, notices in scheduled languages, breach workflow), Mental Healthcare Act 2017 (confidentiality and non-discrimination), IT Act SPDI Rules, CERT-In directions. Verify each clause before quoting it.

---

## 27. Offline-first, made concrete

### 27.1 Positioning statement (use this wording everywhere)
"MANOBAL is offline-first. Everything a jawan needs to check in, look after themselves, and reach help works without a data connection. Conversations with Saathi use the unit's server whenever it is reachable, and everything captured offline syncs automatically."

Every clause of this statement must be true in the build. Sections 27.2 to 27.4 make it true.

### 27.2 Offline capabilities that must genuinely work in the prototype [P0]

| Capability | How it works offline |
|---|---|
| Daily check-in (tap) | Written to the encrypted IndexedDB queue; instant confirmation; count shown |
| Structured voice check-in | Pre-rendered question audio in the user's language plays from cache; answers are large tap targets (no speech recognition needed offline) |
| Assessments | Item text and audio cached; scored locally; queued |
| Toolkit | All media and articles cached by the service worker |
| Safety screen | Cached with pre-rendered audio; `tel:` buttons use the phone's voice network, which works with mobile data off |
| SOS by SMS | "Send SOS by SMS" opens the native SMS app with a prefilled message to the configured unit number (`sms:` link); works without data |
| Crisis lexicon gate | Runs in the browser on every typed entry and journal save |
| Local self-care nudges | A small JavaScript rule set (for example three nights of low sleep, ten duty days in a row from the cached roster) shows T1-style self-care cards without the server; server-side T1 nudges replace them on sync |
| My trends | Rendered from the last synced snapshot plus queued local entries |
| Safety plan, private journal, self-only instruments | Device-only by design |
| Acute packet | Queued with 10-second retries; screen keeps helplines visible and says "Trying to reach your unit" |
| Resync | Idempotent, ordered, with a visible drain animation and conflict-free merge |

Recording rule: the offline segment in the video is recorded with mobile data and Wi-Fi genuinely switched off on the phone (keep the voice network on so the helpline call works).

### 27.3 In-browser on-device AI slice [P2]
A capability-gated "on-device preview" that genuinely runs without network on a WebGPU-capable laptop or phone:
- English dictation with a small Whisper model through transformers.js (model files cached after first load).
- An English "talk it through" reflect mode with a small instruct model through WebLLM, behind the same lexicon gate and a local output guard, limited to reflective listening with fixed safety fallbacks.
- Hindi and other languages use the structured offline flow; the UI explains this.
- Shown only when the device passes a capability check; labelled "On-device preview".

### 27.4 Edge behaviour [P0]
The engine's edge boundary keeps its own queue. The Director has a "Unit server link: up or down" toggle that simulates the Zone 1 to Zone 2 link failing. While down, packets accumulate in the edge queue (visible on Architecture) and drain when restored. This behaviour is real in the backend.

### 27.5 Wording and caption rules for anything not running on-device
- Do not show cloud-backed features under an offline indicator or narrate them as running on the phone.
- When Saathi's rich conversation or officer briefs appear, use a small caption: "Prototype: open-weight model hosted on Azure. Deployable on force servers."
- The Architecture page and the Trust Centre state the same.
- This matters beyond ethics: if the entry progresses to a live round, judges can switch the network off and test every claim in person. Every claim in the video must survive that.

---

## 28. Personalisation engine

### 28.1 Principles
- Personalisation changes the experience, never the scoring. No personalisation field is a feature of the risk engine or forecast.
- Every personalised element has a "Why am I seeing this?" explanation.
- The person can view, edit, reset, or turn off personalisation in Me, Settings.
- Defaults are sensible for a constable with low time and a basic phone.
- Personalisation data is personal data: consent-gated, exportable, erasable.

### 28.2 Personnel profile

| Dimension | Source | What it changes |
|---|---|---|
| Language and script | Onboarding, settings | All copy, voice, instruments (validated only), Hinglish script choice (Devanagari or Latin) |
| Voice preference | Settings | TTS voice (female or male), speed |
| Simple mode | Onboarding question "How do you like to use apps?" | Icon-and-audio-first layout, fewer words, larger targets |
| Check-in style | Learned from usage, editable | Tap vs voice as default; shorter version on busy days |
| Check-in timing | Roster (cached) plus preference | Prompt about 30 minutes after a shift ends, never during duty |
| Quiet hours | Roster plus preference | No notifications during duty or sleep windows |
| Theatre and climate | Unit master data | Content order: cold and altitude safety (North), heat and hydration (Central), monsoon and isolation (East), long standing duty and crowd stress (Capital) |
| Lifecycle state | HRMS events | Pathway cards (section 9.4) |
| Shift pattern | Roster | JITAI timing and sleep planner defaults |
| Family context (self-declared, optional) | Onboarding card, skippable | Family connect content, call reminders, relevant articles (for example staying close to young children) |
| What helps me (self-declared) | Onboarding chips: music, prayer or reflection, walking, sport, talking to someone, breathing, writing, sleep | Toolkit ranking and Saathi suggestions |
| Rank band | HRMS | Extra content for section leaders (HC, ASI): noticing strain in your team, how to refer, being a good buddy |
| Personal goals (optional) | Me | Gentle goals such as "sleep 6 hours on rest days"; no streaks |
| Accessibility | Settings | Text size, contrast, reduced motion, screen reader hints, captions always on |
| Device tier and data saver | Capability probe, setting | Media quality, pre-caching, voice availability |

### 28.3 Toolkit recommender [P1]
- Contextual Thompson sampling over toolkit items.
- Context: time of day, shift phase (pre-duty, post-duty, rest day), theatre climate class, lifecycle state, today's tags, self-declared helpers.
- Reward: "This helped" tap (strong), completion (weak), "Not for me" (negative).
- Cold start: priors per theatre and lifecycle from team-authored defaults.
- Ranking cached for offline use; recomputed on sync.
- Never uses tier, scores, or officer data.

### 28.4 "Things Saathi remembers" [P1]
- Opt-in, off by default.
- A visible list in Me with up to 20 short items in four groups: people who matter, what helps, what to avoid talking about, my goals.
- Saathi may propose an item ("Should I remember that walking helps you?"); it is saved only after the person taps "Yes".
- Items are passed to the companion as context, never to scoring, never to officers.
- Edit or delete any item at any time; "Forget everything" clears all.

### 28.5 Adaptive check-in [P1]
- Busy-day mode: one question (mood) with an optional "more".
- After two skipped days, the next prompt becomes the one-question version.
- Voice default if the person used voice in 3 of the last 5 check-ins.

### 28.6 Officer personalisation [P1]
| Role | Personalisation |
|---|---|
| Welfare Officer | Brief and opener language, opener tone (formal or informal), digest time, queue presets, saved lever notes |
| Counsellor | Languages spoken (used to match requests), availability, session types |
| Medical Officer | Escalation contact preferences, on-call calendar |
| Commander | Pinned KPIs per theatre, default unit scope, Copilot language, weekly brief time |
| HQ | Saved policy lenses and comparison sets |
| WDEC | Watchlists (rules, units by token-free aggregate, gates) |

Request routing uses counsellor language match first, then load.

### 28.7 Fairness guard for personalisation
Governance shows exposure parity for toolkit recommendations and JITAI prompts across rank band, gender, language, and region, with the same 0.8 to 1.25 band.

---

## 29. Persona playbooks

Template per persona: profile and personalisation, storyline (simulated days, D0 is the demo date), what each role sees, shots, voiceover line, what it proves, weakness guard.

### 29.1 Arjun Rathore (MB-4091), Constable/GD, Central, Hindi
- **Profile:** 27, from Uttar Pradesh, married, one child (self-declared); Tier B phone; consents: HR-derived, self-report, wearable, AI conversation; voice female Hindi, simple mode on; helpers: music, talking to someone.
- **Storyline:** D-45 normal; D-30 operation starts, 19 consecutive duty days, night volatility; D-24 sleep falls; D-20 onset detected; D-18 forecast Rising, T1 nudge (sleep planner); D-10 corroborated T3 (roster overtime plus sleep loss); synthetic crisis date D+4 (never reached because of intervention).
- **Personalised app:** home shows shift strip, post-duty check-in prompt at 06:30 after night duty, sleep wind-down in Hindi, music-based decompression first in toolkit.
- **Officer views:** UWO sees MB-4091, T3, Rising, "Drift began about 20 days ago", lever REST_48H; Commander sees Charlie Coy workload strain rising (aggregate only).
- **Shots:** time-travel ribbon forming; T1 nudge with "Why am I seeing this?"; case sliding into queue; Hindi brief; reveal with purpose; phone ledger updating; REST_48H recorded; D+7 ribbon returning toward band.
- **Voiceover:** "Arjun never asked for help. His pattern did, three weeks before it would have been too late, and only his welfare officer was told."
- **Proves:** predictive engine, lead time, intervention recommendation, privacy of identity.
- **Weakness guard:** show that the commander never sees Arjun; show the ledger entry so the reveal looks accountable, not intrusive.

### 29.2 Meena Kumari (MB-2217), Head Constable, East, Hindi
- **Profile:** 34, from Rajasthan, two children with grandparents (self-declared); consents: HR-derived, self-report; helpers: prayer or reflection, talking to family; section-leader content on.
- **Storyline:** 14 months at a non-family station; two leave rejections D-40 and D-12; PSS-10 and CBI rising; T2 at D-5.
- **Personalised app:** leave planner shows EL balance and a feasible window after de-induction; family call reminders on Sundays; "supporting your section" content.
- **Officer views:** UWO digest item with LEAVE_PRIORITISE and FAMILY_CONNECT; Commander leave-pressure board shows Alpha Coy backlog.
- **Shots:** leave planner window picker, draft leave request, digest view, commander release plan.
- **Voiceover:** "For Meena, the right intervention is not counselling. It is leave."
- **Proves:** workload and leave balancing, burnout instrument, practical levers, women personnel represented.
- **Weakness guard:** MANOBAL drafts but never submits leave; say so on screen.

### 29.3 Imran Sheikh (MB-3380), Constable/GD, North, English
- **Profile:** 24, from Jammu, single; consents: all except voice.
- **Storyline:** one week of poor sleep after a festival duty; all other domains stable.
- **Personalised app:** cold-weather content first; sleep toolkit card with explanation.
- **Officer views:** nothing. UWO queue has no Imran.
- **Shots:** Lab or Welfare side note: "single-domain drift stays with the person"; Imran's T1 card on his phone.
- **Voiceover:** "One bad week is not a crisis. MANOBAL tells Imran, and nobody else."
- **Proves:** false-positive control, dignity.
- **Weakness guard:** show an ablation number: without corroboration, alerts rise by X% (from Lab).

### 29.4 Thomas Varghese (MB-1506), Sub-Inspector, Capital, English
- **Profile:** 41, from Kerala; declined wearables and voice; simple mode off.
- **Storyline:** stable; T0.
- **Officer views:** looks identical to any other steady person; no enrolment status anywhere.
- **Shots:** consent screen with wearables off; Lab zero-penalty chart.
- **Voiceover:** "Saying no costs nothing. Thomas is assessed only on what he chose to share."
- **Proves:** voluntary participation, trust (K10).
- **Weakness guard:** never show an enrolment percentage on any commander screen.

### 29.5 Lalit Oraon (MB-5120), Constable/GD, Central, Hindi
- **Profile:** 29, from Jharkhand; consents: HR-derived, self-report, AI conversation; helpers: sport, talking to someone.
- **Storyline:** D-3 IED incident affects Bravo Coy; 72-hour window opens; Lalit opens PFA content and taps "I want to talk"; follow-up scheduled at D+25.
- **Officer views:** UWO Incident board shows only Lalit's request; Commander sees the aggregate incident card; HQ sees theatre incident exposure.
- **Shots:** incident card on phone; PC-PTSD-5 offer with validated badge; UWO incident board; commander aggregate card.
- **Voiceover:** "After an attack, every jawan in the company gets a private door. Nobody is marked for not opening it."
- **Proves:** critical-incident fast track, proactive care.
- **Weakness guard:** use neutral language; no graphic content or imagery.

### 29.6 Deepak Negi (MB-6604), Constable/GD, North, Hinglish
- **Profile:** 26, from Uttarakhand; consents: all; voice male Hindi; Latin-script Hinglish reader.
- **Storyline:** D0 types or says a distress message in Hinglish during a late-night chat.
- **What happens:** lexicon gate or classifier fires, safety screen with Hindi audio, helpline buttons, "Ask my welfare officer to call me" preselected; T4 on Welfare and Medical in under 5 seconds; escalation ladder visible; UWO acknowledges; MO acknowledges.
- **Shots:** one continuous split-screen take with a visible clock from message to acknowledgement.
- **Voiceover:** "When someone says they are not safe, no AI answers. A person does, within minutes."
- **Proves:** safety-by-design, automated alerts, human decision boundary.
- **Weakness guard:** the distress message is written by the team with clinician-style care, is not graphic, and never includes method details. Show that the model never replied (Governance agent-safety log).

### 29.7 Rajesh Yadav (MB-7342), Head Constable, Central, Hindi
- **Profile:** 38, from Bihar; land dispute at home (self-declared tag "Land or property"); grievance pending 60 days.
- **Storyline:** duty swaps rising; grievance ageing; PSS rising; T2.
- **Officer views:** UWO lever GRIEVANCE_EXPEDITE and LEGAL_AID_REFERRAL; HQ grievance trend by category shows land and property concerns concentrated in a theatre.
- **Shots:** grievance tracker on phone with SLA; UWO lever; HQ category chart.
- **Voiceover:** "Some stress is paperwork. MANOBAL routes it to the people who can fix it."
- **Proves:** root-cause levers, data-driven welfare planning, alignment with task-force risk areas.
- **Weakness guard:** grievance text never appears to commanders; only category counts with k-anonymity.

### 29.8 Karthik Selvam (MB-8815), Constable/GD, East, Tamil
- **Profile:** 31, from Tamil Nadu; returning from 35 days of leave after a family bereavement; Tamil UI and voice; helpers: walking, writing.
- **Storyline:** return-from-leave pathway opens a new baseline regime; grief article in Tamil; voice check-in in Tamil; REINTEGRATION_CHAT suggested to UWO only if other domains corroborate (they do not; stays T1).
- **Shots:** Tamil onboarding language grid; Tamil voice check-in with captions; "settling back" card.
- **Voiceover:** "Karthik speaks Tamil. So does Saathi."
- **Proves:** multilingual reach, lifecycle awareness, regime-aware baselines.
- **Weakness guard:** show the machine-translated badge where applicable, and validated badges only on validated instruments.

### 29.9 Officer personas (synthetic)

| Persona | Role | Personalisation shown |
|---|---|---|
| Insp. Sunita Rawat | Unit Welfare Officer, Bn C-02 | Hindi briefs, informal opener tone, 08:00 digest |
| Dr. Farah Siddiqui | Medical Officer, Bn N-01 | On-call calendar, escalation preferences |
| Ms. Anjali Deshmukh | Sector counsellor, Central | Languages Hindi, Marathi, English; availability slots |
| Commandant R. K. Menon | Commandant, Bn C-02 | Pinned KPIs for LWE theatre, Hindi Copilot |
| IG (Synthetic) Sector Central | HQ | Policy lens "rotation length" |
| Dr. Kavita Rao | WDEC member | Watchlist on gate hit rates |

---

## 30. Video production and showcase plan

### 30.1 Before recording
- Read the round's submission rules (maximum length, format, resolution, narration and language requirements, whether a live link or repository is also required). Build two cuts: a short cut that fits the limit, and a full walkthrough if allowed.
- Freeze a demo build and a seed snapshot; never record from a build that changed that day.
- Package Saathi as an Android app using a Trusted Web Activity (Bubblewrap) so it installs and looks native on a real phone; confirm passkeys, notifications, and offline cache work inside it.

### 30.2 Story structure
Tell it through people, not screens.

Short cut (about 3 minutes):
1. Hook (15 s): a constable finishing a night shift, illustrated; the sourced statistic; "Support, not surveillance."
2. Arjun's thread (60 s): check-in, drift, case, reveal, rest.
3. Trust (30 s): Imran and Thomas in two quick beats; commander hidden tile and Copilot refusal.
4. Safety (30 s): Deepak's continuous take.
5. Offline and language (20 s): offline segment with mobile data genuinely off; Karthik in Tamil.
6. Proof and architecture (15 s): Lab lead time and false-positive rate; zones animation.
7. Close (10 s): PS components mapped; team name.

Full cut (about 8 minutes): section 24 order with all eight persona beats.

### 30.3 Shot list

| Shot | Device | Screen and action | On-screen text | Voiceover cue |
|---|---|---|---|---|
| S01 | Motion graphic | Illustrated barracks at dawn, ribbon motif | Source and date under the statistic | Hook |
| S02 | Phone | Language grid, tap Hindi | none | "Saathi starts in your language." |
| S03 | Phone | Consent cards, the one exception, receipt | "Every choice is recorded and reversible" | Consent |
| S04 | Phone | 20-second check-in | Timer overlay | "Twenty seconds after duty." |
| S05 | Phone | Hindi voice check-in with captions, audio-cleared chip | "Prototype: open-weight model hosted on Azure. Deployable on force servers." | Voice |
| S06 | Split | Director slider, Arjun ribbon forming, queue insertion | Simulated date chip visible | Arjun line |
| S07 | Desktop | Case workspace, levers, Hindi brief | "AI-written, officer decides" | Human decision |
| S08 | Split | Reveal with purpose, phone ledger updates | none | Accountability |
| S09 | Phone and desktop | Imran T1 card; Lab zero-penalty and ablation | Numbers from Lab | Imran and Thomas lines |
| S10 | Desktop | Formation grid, hidden Post Delta-7 tile, Copilot refusal | "Groups under 10 are never shown" | Commander |
| S11 | Split, continuous | Deepak message to acknowledgement | Real clock | Safety line |
| S12 | Phone | Data off: check-in, toolkit, safety screen, SMS SOS, queued count; data on: sync drain | "Mobile data off" indicator from the phone itself | Offline statement from 27.1 |
| S13 | Desktop | Architecture packets draining from edge queue | none | Edge |
| S14 | Phone | Karthik Tamil check-in | none | Karthik line |
| S15 | Desktop | Governance fairness band, chain verify, tamper, restore | none | Trust |
| S16 | Desktop | Lab lead time, shifted world | "Synthetic data. Pilot calibration planned." | Evidence |
| S17 | Desktop | Landing second fold mapping PS components | Team name | Close |

### 30.4 Recording setup
- Phone: mid-range Android with the TWA installed; mirror with scrcpy at 60 fps; do-not-disturb on; battery and signal icons clean; the same simulated persona per take.
- Desktop: clean Chrome profile, 1920 by 1080 at 60 fps, 110 to 125% zoom for legibility, bookmarks bar hidden, cursor highlight on.
- Capture: OBS scenes for phone-only, desktop-only, and split; record system audio for TTS.
- Editing: DaVinci Resolve or similar; smooth zooms on key UI; lower-thirds in Anek; consistent 8-frame transitions.
- Reset the world from the snapshot before every take; use Director presets.

### 30.5 Audio and captions
- English narration by the team's clearest speaker; Hindi app audio kept audible under narration where it matters.
- Burned-in captions in English, plus Hindi subtitles for the Hindi segments.
- Loudness normalised (about -16 LUFS for web); music low and neutral.

### 30.6 Credibility rules
- Keep S11 and one voice turn as uncut continuous takes so latency is visibly real.
- Trimming dead air elsewhere is fine; do not speed up AI responses inside a take that is presented as real time.
- Show the simulated-date chip whenever time travel is used.
- Keep a small "Synthetic data" watermark on data-heavy screens.
- Never use CRPF crests, the State Emblem, real unit names, or real operational footage; use original illustrations.

### 30.7 Showcase assets beyond the video
- Hosted demo link with role cards (if permitted), a two-minute "try it" guide, and the Trust Centre page.
- Public repository with README, architecture diagram, synthetic generator, eval results, and the model card.
- A one-page PDF mapping PS items to screens and timestamps in the video.

---

## 31. Feasibility review: will it work?

### 31.1 Component confidence

| Component | Confidence | Main risk | Mitigation |
|---|---|---|---|
| Next.js PWA with Serwist offline queue | High | Service worker caching bugs | Test offline on the actual phone inside the TWA early |
| TWA packaging | High | Passkey and notification behaviour inside TWA | Spike in week 1; PIN fallback exists |
| FastAPI engine with polars and LightGBM | High | Rolling-median cost | Restrict to 90-day windows and changed subjects |
| Synthetic generator | Medium | Row volume and seed time | Data-volume rules in 5.2 |
| TimescaleDB, pgvector, ltree on Azure PostgreSQL 16 | Medium | Extension allow-listing and Apache-edition limits | Enable via server parameters on day 1; use materialized views, not continuous aggregates |
| Key Vault wrap and unwrap from Container Apps | High | Access policy mistakes | Separate identities; automated test of forbidden operations |
| Foundry deployments (`main`, `fast`, `open`) | Medium | Quota on credit subscriptions; regional availability | Request quota in week 1; choose regions early; resilience cache |
| gpt-oss-120b Hindi quality | Medium | Weaker Hindi or Hinglish | Eval gate; route Hindi companion turns to `main` if it fails |
| Deepgram Nova-3 Hindi streaming | Medium | Script and language detection issues | Pin `hi`; keyterms; transliterate; Azure STT fallback |
| Azure Hindi and Indian-language TTS | High | Style availability per voice | Config-driven voice map; verify in Speech Studio |
| Azure Content Safety on Hindi | Medium | Lower accuracy in Hindi | It is one of three OR-combined gates |
| Voice latency under 1.8 s | Medium | Network and model latency | `fast` deployment, sentence streaming, parallel gates, regional endpoints |
| Azure Web PubSub | High | Group auth design | Negotiate endpoint with scoped groups; local fallback |
| Azure Communication Services calls | Medium | Browser permissions and TURN | Test two devices on different networks early; if blocked, show scheduling only |
| Entra ID sign-in | Medium | Tenant permissions for app registration | Use a tenant you control; demo login remains available and labelled |
| opensmile in container | High | Native dependency build | Pin image; test in CI |
| Web Bluetooth heart rate | Low priority | Browser and device support (not on iOS) | Simulated device is the default |
| In-browser AI slice | Medium | Model download size and WebGPU support | P2 only; capability-gated |
| Twilio or Exotel IVR | Medium | Account verification and Indian number rules | P2 only |

### 31.2 De-risking spikes (first 3 working days, in parallel)
1. Foundry: deploy `main`, `fast`, `open`, embeddings; one call each from a Container App with managed identity.
2. Hindi eval: 40 Hindi and Hinglish companion prompts on `open` and `main`; pick routing.
3. Deepgram: stream Hindi and Hinglish fixtures; measure accuracy and script.
4. Azure Speech: synthesise Hindi, Tamil, and English (India) samples; pick voices.
5. Content Safety: run the red-team fixtures; record per-language hit rates.
6. PostgreSQL: enable all extensions on Azure; create a hypertable, an ltree index, a vector index.
7. Key Vault: wrap and unwrap from the vault identity; verify the engine identity is refused.
8. Web PubSub: publish from engine, receive in Next.js with scoped groups.
9. ACS: a call between two browsers on different networks.
10. TWA: install on a phone; passkey, push, and offline cache checks.
11. Entra: register app, map roles, sign in with MFA.

Go and no-go rules: any spike that fails by day 3 switches to its fallback in 31.1 without further debate.

### 31.3 Capacity check
P0 in section 25 totals about 73 person-days and P1 about 22. With 6 people working full time, P0 needs roughly two and a half weeks and P1 about one more week, plus a week for polish, recording, and editing. If the deadline is closer, cut P1 items in this order: Integration Console, DPO Centre, HQ policy simulator, buddy, counsellor calls. Never cut from the demo spine.

---

## 32. Weakness audit

Each item is something a judge could notice in a video, with the prevention built into this spec.

| # | Possible weakness | Prevention |
|---|---|---|
| 1 | "This is surveillance of soldiers." | Positioning line, Trust Centre, consent flows, hidden tiles, access ledger, no location or call data |
| 2 | "Just rules, not AI." | Forecast with calibration, change points, drivers, Lab metrics, shifted world |
| 3 | "Synthetic data proves nothing." | Shifted-world test, honest limitation, silent-pilot plan, public-dataset sanity check |
| 4 | "Too many false alarms." | Corroboration, hysteresis, CUSUM, ablation numbers, K3 |
| 5 | "Commanders will misuse it." | Aggregate-only APIs, route scan, Copilot refusal, no enrolment metrics |
| 6 | "Welfare officers will snoop." | Purpose codes, contact-note rule, rate limits, WDEC sampling, person-visible ledger |
| 7 | "AI chatbot giving mental health advice is dangerous." | Three gates before the model, output guard, corpus-only answers, no diagnoses, human handoff |
| 8 | "Works only in English." | Hindi-first flows, Tamil persona, 22-language UI with honest badges |
| 9 | "Needs network." | Genuine offline segment and edge queue drain |
| 10 | "Cloud dependence and sovereignty." | Open-weight companion model deployable on force hardware; sovereign adapter |
| 11 | "Numbers change between screens." | One seeded world; all numbers computed from the database |
| 12 | "Every persona is in crisis." | Formation grid shows most personnel steady; Imran and Thomas beats |
| 13 | "Empty or placeholder screens." | Loading, empty, and error states; no lorem ipsum; copy lint |
| 14 | "Generic dashboard look." | Ribbon and formation grid signatures, Anek and Mukta type, force-appropriate palette |
| 15 | "Slow AI responses." | Latency budget, fast deployment, continuous takes that show acceptable speed |
| 16 | "What about legal compliance?" | Rights Centre, DPO console, notice versions, breach workflow; clauses verified before quoting |
| 17 | "Weapons, APAR, promotion fears." | Zone X blocked on Architecture; explicit firewall statement |
| 18 | "Only detects, does not help." | Leave planner, sleep planner, counsellor calls, grievance routing, levers |
| 19 | "No integration with existing systems." | Integration Console with schema contracts and quarantine |
| 20 | "Fairness across ranks and regions?" | Fairness band, exposure parity, excluded attributes on model card |
| 21 | "How is this different from a helpline?" | Proactive detection plus personalised daily value plus command-level workload balancing |
| 22 | "Cost and scale." | Benchmark for 80,000, scale path to force strength, cost guard |
| 23 | "Visible CRPF branding or emblem." | Banned; original illustrations only |
| 24 | "Inconsistent tier names or colours." | Single token system, tier shapes and labels everywhere |
| 25 | "Model used is known for safety issues." | Grok excluded from personnel-facing tasks (section 33) |
| 26 | "Crash or error on camera." | Frozen build, snapshot resets, resilience mode, warm-up, multiple takes |

---

## 33. Decision record

| Decision | Choice | Alternatives considered | Reason |
|---|---|---|---|
| Companion model | gpt-oss-120b in Foundry (`open`), GPT-5.x (`main`) fallback | GPT-5.x only; Grok; xAI API | Open weights under Apache 2.0 and single-GPU deployability make the on-prem story real; GPT-5.x covers quality gaps, especially in Hindi |
| Officer-facing generation | GPT-5.x (`main`) | gpt-oss; Grok | Quality and tool calling for briefs and Copilot |
| Fast tasks and voice | GPT-5.x mini or nano (`fast`) | gpt-oss | Latency |
| Grok | Optional `alt` for non-personnel tasks only, or not used | Grok as companion | Microsoft's Foundry model card for Grok 4 states that Microsoft's safety evaluation found it less safe than other models offered through Azure Direct and requires Content Safety plus system safety messages; public Q&A threads also report availability problems. A welfare companion for at-risk users is the wrong place to take that risk. |
| xAI API directly | Not used for personal data | Direct calls | Data would leave the Azure boundary the architecture promises |
| Voice pipeline | Cascade (STT, gates, LLM, TTS) | Realtime speech-to-speech | Gates must run before any model sees the words |
| STT | Deepgram for English and Hindi; Azure for other Indian languages | Azure only; Deepgram only | Deepgram streaming quality and credits; Azure breadth |
| TTS | Deepgram Flux for English (Indian-accent voices); Azure for Hindi and other Indian languages | Deepgram only | Deepgram TTS does not offer Hindi |
| Mobile | PWA packaged as TWA | Native Android (Kotlin or Flutter) | One codebase, real offline, installable APK for the video |
| Backend | FastAPI (Python) | Django; Node | Analytics and ML in one language; async streaming |
| Hosting | Azure Container Apps | AKS; App Service | Simpler operations, WebSockets, jobs, managed identities |
| Database | PostgreSQL 16 with TimescaleDB, pgvector, ltree | Separate time-series and vector stores | One engine, fewer moving parts, supported on Azure |
| Realtime | Azure Web PubSub | Self-hosted WebSockets | Managed scale and scoped groups |
| Secrets and keys | Azure Key Vault Premium (HSM-backed keys) | Environment variables | Real key separation for the identity vault |

---

*End of MANOBAL MVP Build Specification v2.1*
