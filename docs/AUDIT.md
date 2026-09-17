# MANOBAL verification audit (Prompt 9)

Date: 17 Sep 2026. Machine: Apple Silicon Mac. Env file: `infra/.env` (template `infra/.env.example`). This audit did not open `infra/.env`, `infra/secrets.env`, or `infra/keys/`. Settings load those files through the settings loader and print only pass or fail.

Goal: an honest status before go-live. No features were added beyond the checks and the small fixes listed below.

## Status table

| Item | Spec | Status | Evidence |
|---|---|---|---|
| Demo spine exists as screens | 2.2, 24, 30.3 | pass | Routes and Director presets match `docs/SHOT_LIST.md`. Local demo-spine E2E exists in `e2e/tests/demo-spine.spec.ts`. |
| Stub search on recorded paths | 2.2, 32.13 | partial | No TODO, FIXME, or lorem in app code. Recorded paths still use labelled fallbacks, one landing fixture ribbon, Me fixture copy, and hardcoded Lab or Governance figures. See section 1. Owner: Prompt 10 plus the numbers owner steps below. |
| Foundry main, fast, open, embeddings | 3.2, 3.3, 31.1 | fail | Real client in `services/engine/app/providers/foundry.py`. `make providers-check` (host): all four fail, unconfigured. OpenAI stand-in is configured for chat classes; embeddings use hash vectors. Architecture labels "Foundry: unset, local fallback". Owner: Prompt 10, you create Foundry deployments and set `FOUNDRY_ENDPOINT` plus class deployment names. |
| Deepgram | 13.2, 31.1 | pass | Real STT and TTS clients in `voice/stt.py` and `voice/tts.py`. `make providers-check`: pass, listen 1539 ms. |
| Azure Speech | 13.2, 31.1 | fail | Real client when `SPEECH_KEY` and `SPEECH_REGION` are set. Check: fail, unconfigured (silent WAV). UI labels it on Architecture. Owner: Prompt 10, you add Speech. |
| Translator | 3.2, 27.2 i18n | fail | Real transliterate and translate clients. Check: fail, unconfigured (English plus machine-translated badge). Owner: Prompt 10, you add Translator. |
| Content Safety | 12.3, 3.2 | fail | Real analyze and Prompt Shields clients; abstain when unset. Check: fail, unconfigured. Owner: Prompt 10, you add Content Safety. |
| ACS | 15.4, 31.1 | fail | No calling client. Flag plus labelled demo join only (`personnel.py` `talk_state`, Architecture). Check: fail, unconfigured. Owner: Prompt 10, you add ACS and a real join path. |
| Web PubSub | 18, 31.1 | fail | Connection string is read; Azure send is not implemented. Local hub is the working path. Check: fail, unconfigured. Owner: Prompt 10, wire Azure Web PubSub send. |
| Key Vault | 14.1, 31.1 | fail | Real wrap and unwrap in `services/vault/app/key_provider.py` when `KEY_PROVIDER=azure`. Check: fail, local wrap file. Owner: Prompt 10, Azure Key Vault and the vault identity split. |
| `make providers-check` | 05 go-live 8.2 | pass | `make providers-check` prints a pass or fail table and does not print secrets. 1 pass, 10 fail on this machine. |
| Spec 27.2 offline, Playwright network off | 27.2 | partial | See section 3. Structured voice copy and cached audio pass. Local nudges and the safety plan work on an already-open page. Fresh navigations after `setOffline(true)` often fail (`net::ERR_INTERNET_DISCONNECTED`) because the service worker does not reliably serve HTML. Owner: Cursor, make SW cache and serve every Saathi document in 27.2; you rehearse on an iPhone with Wi-Fi and cellular off. |
| Shot list, 1920 by 1080, rubric | 30.3, UI 9 | partial | Frames in `e2e/artifacts/audit/*-1920.png`. Landing, Copilot, Lab, roster, and Architecture are video-usable. Stage splits share one session, so one pane is often a scope error. Drift and one Governance capture were empty or still loading. See section 4. Owner: you record phone and console as two views, or Cursor adds a stage dual-session; wait for iframe load before rolling. |
| Lab, Governance, Landing numbers | 8.9, 32.11 | fail | Landing figures are cited but marked "verify before citation". Governance K1, K3, K10 to K12 are hardcoded strings. Lab precision, recall, and Brier come from a 48-row in-memory fit, not the seed database. Confusion and ablations are hardcoded. Benchmark size was 8,000 `z_score` loops; now 80,000 subjects in memory. Live `POST /api/v1/lab/benchmark` on this stack: `subjects` 80000, `seconds` 1.109. Owner: you verify landing citations; Cursor compute Governance and Lab overlays from the database before the pitch quotes them. |
| `make dev` health-checks data stores first | 05 go-live 8.6 | pass | `make infra-ready` starts `core-db`, `vault-db`, and Redis, waits, then `pg_isready` and `redis-cli ping`. `make dev` runs that before the rest of the stack. |
| Architecture shows healthy | 17.12, 23.6 | pass | Live `GET /api/v1/system/selftest` returned `healthy: true` with core reachable, all five extensions, vault isolated, Zone X held. Architecture copy: "Stack: healthy. Core database reachable." (`e2e/artifacts/audit/architecture-1920.png`). |
| Spec 32 weakness walk | 32 | partial | Prevention is in code for most items. Recorded Stage frames can still show empty panes, loading, labelled cloud fallbacks, and unverified landing statistics. See section 7. Owner steps sit on the failing rows. |
| Spec 23.6 local stack | 23.6 | partial | `make dev` brings the local stack up. Azure from scratch, real voice, and the hosted E2E URL are not done. Owner: Prompt 10 and you. |

## Fixes made during this audit

1. `Makefile`: `infra-ready` health-checks core Postgres, vault Postgres, and Redis before `make dev` starts the engine. Added `make providers-check`.
2. Engine and vault settings load `infra/.env` through the settings loader (still never printed).
3. `POST /lab/benchmark` scores 80,000 generated subjects in memory (`score_generated_subjects` in `services/engine/app/scoring/core.py`). Lab button copy is now "Run 80,000 in-memory benchmark".
4. Architecture self-test shows "Stack: healthy" or "not healthy", plus core database reachable.
5. `scripts/providers-check.py`: one real call per named provider, pass or fail table, exception type only.
6. Engine image installs `libgomp1` so LightGBM can load. Without it, Lab and Governance KPIs returned 500 in Docker (`libgomp.so.1` missing).
7. Web image copies `public/` into the standalone runner. `/sw.js` and `/audio/*.wav` were 404 before this.
8. Regenerated silent pre-rendered WAV files under `apps/web/public/audio/` (gitignored) so the service worker precache list can exist.
9. Playwright: `e2e/tests/audit-offline.spec.ts` and `e2e/scripts/audit-shots.mjs`. Shots saved under `e2e/artifacts/audit/`.

## Ranked remaining risks for the video

1. **Cloud AI is still a labelled fallback.** Foundry, Speech, Translator, Content Safety, ACS, Web PubSub, and Key Vault failed `make providers-check`. Saathi Hindi or Tamil voice, briefs, Copilot generation, and Content Safety will not be real Azure calls. Deepgram listen works on the host. Owner: Prompt 10, you provision; Cursor wires compose so the engine container receives the same settings.
2. **Stage cannot show phone and console as two roles at once.** One `sessionStorage` token is shared with both iframes. Personnel shots blank the Welfare or Command pane ("The session does not have the required scope"). Officer shots blank Saathi. Drift was an empty split. Owner: you record the phone and the console as separate views from Director resets, or Cursor adds a dual-session Stage.
3. **Quoted numbers are not all from the database.** Do not say "4.2 day lead time" or "false-positive 0.11" as measured field facts. Lab T2+ precision 0.917, recall 0.957, Brier 0.056 are from a 48-row in-process fit. Confusion 18 / 3 / 22 / 5 and the ablation deltas are literals. Landing "Over 80%" still says verify before citation. The 80,000 benchmark is real in memory. Live engine: 1.109 s. Owner: you fix citations; Cursor replace hardcoded overlays; pitch quotes only Lab metrics plus the measured 80,000 time.
4. **Offline on a real phone is not proven.** Playwright with the network disabled: structured offline voice copy passed; several 27.2 navigations failed because HTML was not served from the service worker. Owner: Cursor harden SW caching; you film airplane mode on the iPhone.
5. **Empty or loading recorded frames.** Governance was captured while still loading. Medical on the Deepak split was loading. A judge who pauses on those frames sees a hole. Owner: wait for the console pane, or use the non-Stage routes that already E2E green.
6. **Karthik Tamil shot still shows Hindi companion lines** under a Tamil label. Owner: Prompt 10 real Tamil TTS and a Tamil scripted beat; team Tamil review.
7. **Azure URL, passkeys, iPhone Home Screen, and human reviews** are still open (05 sections 5 to 7). Owner: you.

---

## 1. Stub, fallback, and fixture hits on the demo spine

Search: TODO, FIXME, mock, stub, fake, placeholder, hardcoded, fallback, lorem, and fixtures outside tests or `/dev/components`.

No TODO, FIXME, or lorem in application TypeScript or Python.

| File | Line | What it does | Acceptable? |
|---|---|---|---|
| `apps/web/src/app/page.tsx` | 19 to 38, 88 | Landing stats with "verify before citation". Hero ribbon from `landingRibbon` fixture. | Partial. Citation flag is honest. The ribbon is an illustration, not live data. Owner: you verify sources and dates. |
| `packages/contracts/src/ui-fixtures.ts` | 334, 345 | `landingRibbon`, `psMapping` used by landing. | Acceptable for the mapping table (spec 26.2). Ribbon is decorative. |
| `apps/web/src/app/(personnel)/app/me/page.tsx` | 4, 37, 70 | `mePrivacy` fixture statements and receipt seed. | Not acceptable as the only Me copy on a workspace shot. Owner: bind statements to live rights payload. |
| `services/engine/app/providers/foundry.py` | 157 to 244 | `local_handler` when Foundry classes are unset. | Acceptable if labelled. Architecture and Governance do label it. |
| `services/engine/app/voice/tts.py` | 14, 32 | Silent WAV when Speech or Deepgram TTS is unset. | Acceptable and labelled. |
| `services/engine/app/personnel.py` | 679 to 689 | `demo_join` when ACS is unset. | Acceptable and labelled. Talk page shows the demo sentence. |
| `services/engine/app/officers.py` | 674 | Counsellor `demo_join: True`. | Same. |
| `services/engine/app/main.py` | 137, 237 | `oidc_stub: true` on the Entra callback. | Acceptable for demo login. Label the demo login on camera. |
| `services/engine/app/oversight.py` | 325 to 338, 438 to 512, 826 to 843 | Lab worlds trained on 48 random rows. Governance KPIs and fairness ratios are literals. Lab calibration, confusion, and ablations are literals. | Not acceptable if quoted as measured. Owner: compute from the seed or stop quoting. |
| `services/engine/app/realtime.py` | 57 to 71 | Web PubSub connection string is read and then unused. | Not acceptable as a "live Azure PubSub" claim. Local hub works. |
| `apps/web/src/components/stage-view.tsx` | 61 to 68 | `safePath` fallback for unknown Stage URLs. | Acceptable. |
| `apps/web/src/components/demo-login.tsx` | 173 | Device PIN fallback. | Acceptable (spec 30.1). |
| `packages/ui/src/shells.tsx` | 357 | Command search input `placeholder`. | Acceptable (form placeholder, not lorem). |

Gallery `/dev/components` still uses contract fixtures. That is in spec.

Docker note: compose interpolates `infra/.env` but the engine service environment block does not pass Foundry, Deepgram, Speech, or ACS variables into the container. `make providers-check` runs on the host. The running engine can still be on local handlers even when the host check passes Deepgram. Owner: Prompt 10, pass provider settings into the engine container through the settings class, not by pasting secrets into chat.

---

## 2. Providers

| Provider | Real client? | Env vars (names only) | Fallback | UI labels fallback? | This machine |
|---|---|---|---|---|---|
| Foundry main | Yes, Entra chat | `FOUNDRY_ENDPOINT`, `AI_DEPLOYMENT_MAIN` | Local scripted handler; optional OpenAI stand-in (`OPENAI_API_KEY`, `OPENAI_COMPANION_FALLBACK`) | Yes, Architecture and Governance | fail, unconfigured (OpenAI stand-in configured) |
| Foundry fast | Yes | `FOUNDRY_ENDPOINT`, `AI_DEPLOYMENT_FAST` | Same | Yes | fail, unconfigured |
| Foundry open | Yes | `FOUNDRY_ENDPOINT`, `AI_DEPLOYMENT_OPEN` | Same | Yes | fail, unconfigured |
| Foundry embeddings | Yes | `FOUNDRY_ENDPOINT`, `AI_DEPLOYMENT_EMBED` | Hash 1024-d vectors | Yes | fail, unconfigured |
| Deepgram | Yes, listen and speak | `DEEPGRAM_API_KEY`, `DG_STT_MODEL_EN`, `DG_STT_MODEL_HI`, `DG_TTS_VOICE_EN` | Client-final transcript; silent WAV | Voice page demo-mode line | pass, listen 1539 ms |
| Azure Speech | Yes, STT and TTS | `SPEECH_KEY`, `SPEECH_REGION`, `SPEECH_ENDPOINT`, `AZ_TTS_VOICE_HI` | Silent WAV | Architecture: "unset, silent WAV" | fail, unconfigured |
| Translator | Yes | `TRANSLATOR_KEY`, `TRANSLATOR_ENDPOINT`, `TRANSLATOR_REGION` | Local Latin map; English plus badge | Machine-translated badge | fail, unconfigured |
| Content Safety | Yes | `CONTENT_SAFETY_ENDPOINT`, `CONTENT_SAFETY_KEY` | Abstain (lexicon and classifier still run) | Not on every turn; Architecture mode omits a dedicated line | fail, unconfigured |
| ACS | Flag only | `ACS_CONNECTION_STRING` | Labelled demo join | Yes | fail, unconfigured |
| Web PubSub | Not implemented | `WEBPUBSUB_CONNECTION_STRING` | Local realtime hub | Not labelled as Azure vs local | fail, unconfigured |
| Key Vault | Yes, when `KEY_PROVIDER=azure` | `KEYVAULT_URI`, `KEY_PROVIDER`, `KV_KEK_NAME`, `KV_TOKEN_KEY_NAME` | Local wrap file (demo only) | Not on Architecture | fail, local wrap file |

`make providers-check` is the single command. It exits 1 when any row fails, which is the honest gate for Prompt 10.

---

## 3. Spec 27.2, Playwright offline context

Harness: `e2e/tests/audit-offline.spec.ts` against `http://localhost:3000` after `make dev`, using `context.setOffline(true)`.

| # | Capability | Result | Notes |
|---|---|---|---|
| 1 | Daily check-in (tap) | fail | UI can complete; IndexedDB queue count stayed 0 in the run. Owner: Cursor, assert enqueue after Save while offline. |
| 2 | Structured voice check-in | pass | "Listen and tap. Speech recognition is not needed offline." and cached `/audio/grounding.en.wav`. |
| 3 | Assessments | fail | Options not ready after offline navigation. Owner: cache assessment routes in the SW. |
| 4 | Toolkit | fail | Toolkit copy missing after offline navigation. Owner: SW cache `/app/toolkit` and item pages. |
| 5 | Safety screen | fail | `page.goto` after offline: `ERR_INTERNET_DISCONNECTED`. Code has `tel:` and cached audio when the page stays open. Owner: SW serve `/app/safety`. |
| 6 | SOS by SMS | fail | Same navigation miss. `sms:` link exists on the page (`safety/page.tsx`). Owner: same as 5; you confirm on a phone. |
| 7 | Crisis lexicon gate | fail | Same navigation miss. `browserLexiconHit` is in-bundle and does not need the network. Owner: stay on Saathi, then go offline, then type. |
| 8 | Local self-care nudges | pass | Sleep toolkit and "Why this? Three nights of low sleep on this phone." appeared while offline. The assertion was too strict (three matches). |
| 9 | My trends | fail | Me page empty after offline navigation. Snapshot write exists in `use-engine.ts`. Owner: SW cache `/app/me`. |
| 10 | Safety plan, journal, self-only | pass | "Saved on this phone." after Save. Device-only `localStorage`. |
| 11 | Acute packet | fail | Safety navigation failed offline. Retry copy exists when the page is already open. Owner: same as 5. |
| 12 | Resync | fail | Could not finish a clean offline enqueue then drain. Drain helpers exist (`drainQueue`). Owner: Cursor, one passing drain test; you show the edge queue on Architecture after airplane mode. |

Code for the encrypted queue, snapshots, lexicon, SMS, and tel is present. The gap is "open this screen with the network already off", which the spec and the iPhone rehearsal require.

---

## 4. Shot list scores (UI direction 9)

Scale 1 to 5. Target 4 on every line. Files: `e2e/artifacts/audit/<shot>-1920.png`. Stage uses one session, so many splits lose a pane.

| Shot | Focal | MANOBAL | Hierarchy | Copy | Data-viz | Motion | A11y | Video | Notes |
|---|---|---|---|---|---|---|---|---|---|
| Landing ribbon | 5 | 5 | 4 | 5 | 5 | 4 | 5 | 5 | Ribbon, role doors, Support not surveillance. |
| Hindi onboarding | 4 | 4 | 4 | 4 | 3 | 3 | 4 | 3 | Hindi selected on the language grid. Console scope error. |
| Twenty second check-in | 5 | 4 | 5 | 5 | 4 | 4 | 5 | 3 | Face scale, 1 of 3. Console scope error. |
| Hindi voice check-in | 5 | 5 | 4 | 5 | 4 | 4 | 4 | 3 | Hindi turn, Azure hosting caption. Console scope error. |
| Arjun time travel | 1 | 2 | 1 | 1 | 1 | 1 | 2 | 1 | Empty phone and console. Do not use this frame. |
| Case workspace reveal | 4 | 4 | 4 | 5 | 4 | 4 | 4 | 3 | MB-4091, REST_48H, Hindi brief, locked identity. Phone scope error. |
| Imran and Thomas | 4 | 4 | 4 | 5 | 3 | 3 | 4 | 4 | Both sentences present. Reliability chart is a thin line. |
| Formation and hidden tile | 5 | 5 | 4 | 5 | 5 | 4 | 4 | 4 | Post D-7 hatched. Charlie Coy 20 to 30 percent. Phone scope error. |
| Copilot Hindi refusal | 5 | 5 | 4 | 5 | 5 | 4 | 4 | 5 | Refusal on camera. Best Stage frame in this set. |
| Roster balancer | 4 | 4 | 4 | 5 | 4 | 3 | 4 | 4 | Post D-7 locked, under 10. Leave copy is honest. |
| Deepak safety and T4 | 5 | 5 | 5 | 5 | 3 | 4 | 5 | 3 | Safety phone is the hero. Medical pane still loading. |
| Governance chain | 1 | 2 | 1 | 2 | 1 | 1 | 2 | 1 | Loading only. Recapture after self-test and chain render. |
| Validation lab | 4 | 4 | 4 | 5 | 3 | 3 | 4 | 4 | 80,000 button. Honest synthetic note. Confusion is canned. |
| Offline then sync | 4 | 4 | 4 | 4 | 3 | 3 | 4 | 3 | Check-in plus Architecture. Not actually offline in the frame. |
| Zones and self-test | 4 | 4 | 4 | 5 | 3 | 3 | 4 | 4 | Stack healthy. Fallbacks labelled. Zone X blocked. |
| Landing second fold | 4 | 4 | 4 | 5 | 4 | 3 | 5 | 5 | PS mapping table. Stats still "verify before citation". |
| Karthik Tamil voice | 3 | 4 | 4 | 3 | 3 | 3 | 4 | 2 | Tamil chrome, Hindi companion lines. |
| Rajesh grievance | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 2 | First capture; console likely scope-blocked. Confirm before use. |
| Lalit incident | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 2 | Same Stage session limit. |
| Meena leave planner | 4 | 4 | 4 | 5 | 3 | 3 | 4 | 3 | EL 42, CL 8, does not submit leave. Roster pane scope error. |

---

## 5. Numbers on Lab, Governance, and Landing

| Surface | Number | Source | Honest? |
|---|---|---|---|
| Landing | Over 80%, Most on duty, Named stressors | Hardcoded; "Public reporting on CRPF data" / MHA draft; dates "verify before citation" | No, until a person verifies the source and date |
| Landing ribbon | 3.1 to 5.4 | Fixture series | Illustration only |
| Governance K1 4.2 d, K3 0.11, K10 1.4 / 100, K11 3.1 min, K12 0.4% | Literals in `gov_kpis()` | No |
| Governance fairness 0.92, 1.08, 0.97 | Literals in `gov_fairness()` | No |
| Lab precision 0.917, recall 0.957, f1 0.936, brier 0.056, auroc 0.986, auprc 0.98 | `ensure_lab_worlds()` LightGBM on 48 random rows, not `manobal_core` | Partial. Computed, but not from the seed |
| Lab confusion 18, 3, 22, 5 | Literal | No |
| Lab ablations +2.1 d, -0.04 | Literal | No |
| Lab Imran T1, Thomas T0 | Copy, matches spec 29 | Acceptable as story copy |
| Lab benchmark | **80,000 subjects in memory, 1.109 s** on the live engine after the audit fix | Yes, measure and quote this pair |

---

## 6. `make dev` and Architecture healthy

`make infra-ready` output on this machine: core Postgres accepting connections, vault Postgres accepting connections, Redis `PONG`. `make dev` then waits on the remaining healthchecks. After rebuild, `GET /api/v1/system/selftest` was healthy, and the Architecture page said so.

---

## 7. Spec 32, item by item

| # | Weakness | Where prevented | Could a recorded screen still show it? |
|---|---|---|---|
| 1 | Surveillance | Landing line, Trust, consent, hidden tiles, ledger, no location | Copilot and formation stay aggregate. Stage phone errors do not leak names. |
| 2 | Just rules | Lab forecast metrics, change points in engine tests | Lab reliability chart is weak. Do not linger on an empty chart. |
| 3 | Synthetic proves nothing | Honest Lab sentence, shifted world toggle | Good. Keep that sentence in the take. |
| 4 | Too many false alarms | Corroboration, hysteresis, K3 | K3 is hardcoded. Do not quote 0.11 as measured. |
| 5 | Commanders will misuse it | Aggregate APIs, Copilot refusal, no enrolment | Copilot shot proves the refusal. |
| 6 | Welfare officers will snoop | Purpose, contact-note, ledger | Workspace shot shows locked identity and the warning. Phone ledger did not update in the split. |
| 7 | Dangerous chatbot | Gates, output guard, no diagnosis | Real Content Safety is unset. Lexicon still runs. Do not claim Azure Content Safety on camera. |
| 8 | English only | Hindi onboarding and voice; Tamil chrome | Karthik still speaks Hindi lines. Owner: Tamil review. |
| 9 | Needs network | Queue, snapshots, SW, edge toggle | Playwright offline nav failed. Do not claim "works with data off" until the phone rehearsal. |
| 10 | Cloud and sovereignty | Hosting caption, Architecture mode | Caption is on the voice shot. Foundry is unset. |
| 11 | Numbers disagree | One seed | Governance literals disagree with Lab computed metrics. A paused frame can catch that. |
| 12 | Everyone in crisis | Formation majority T0; Imran and Thomas | Formation shows mostly steady cells. |
| 13 | Empty screens | ScreenState | Drift empty; Governance loading; Medical loading. Yes, a judge can see this. |
| 14 | Generic dashboard | Ribbon, formation, Anek | Command still has extra top-bar chrome (UI_NOTES). Recognisable enough on Copilot and formation. |
| 15 | Slow AI | Latency budget, fast class | Local handlers are instant. Real Azure latency is unmeasured. |
| 16 | Legal | Rights, DPO, Trust | Not on the 8-minute spine. Fine as a backup beat. |
| 17 | Weapons, APAR | Zone X on Architecture | Shown. |
| 18 | Only detects | Leave planner, levers, talk | Meena and workspace show help, not only a flag. |
| 19 | No integration | Integration Console | Not in the 8-minute spine. Exists. |
| 20 | Fairness | Fairness bars, excluded attributes | Ratios are literals. Model card copy is correct. |
| 21 | Just a helpline | Landing plus detection story | Landing is strong. |
| 22 | Cost and scale | 80,000 in-memory benchmark now | Quote 80,000 in 1.109 s on this stack, not "8k". |
| 23 | CRPF branding | Banned list, original SVG | None seen on these frames. |
| 24 | Inconsistent tiers | Tokens | Consistent on workspace and formation. |
| 25 | Unsafe model | `alt` blocked on personnel tasks | Grok is not on companion. Keep it that way. |
| 26 | Crash on camera | Reset, resilience, warmup | Engine socket hang-up during a shot reset. Warm up and reset once before the take. Owner: you rehearse; Cursor keep reset under 20 s. |

---

## Owner index

| Owner | Next step |
|---|---|
| You | Prompt 10 Azure resources and keys in `infra/.env` (never paste into chat). Verify landing citations. Rehearse Stage as two views. iPhone airplane-mode segment. Human Hindi, Tamil, safety, copy, and symbols reviews. |
| Cursor, Prompt 10 | Switch the router to real providers, pass settings into compose, regenerate audio and translations, measure voice latency. |
| Cursor, follow-up | SW document cache for 27.2 navigations. Compute Governance and Lab overlay numbers from the seed. Stage dual-session or documented two-device recording. Recapture Governance and Deepak medical after load. |
