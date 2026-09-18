# MANOBAL verification audit (Prompt 9, updated Prompt 10 and 10A-2)

Date: 17 Sep 2026. Machine: Apple Silicon Mac. Env file: `infra/.env` (template `infra/.env.example`). This audit did not open `infra/.env`, `infra/secrets.env`, or `infra/keys/`. Settings load those files through the settings loader and print only pass or fail.

Goal: an honest status before go-live. Prompt 9 recorded labelled fallbacks. Prompt 10 replaced the local AI path with live providers on this Mac. Prompt 10A-2 proved those providers from the engine container and ran the demo spine through the UI. Azure hosting, the iPhone domain, and Key Vault split remain 31.1. Spine evidence lives in `docs/SPINE_STATUS.md`.

## Status table

| Item | Spec | Status | Evidence |
|---|---|---|---|
| Demo spine exists as screens | 2.2, 24, 30.3 | pass | Director table and Stage captions cover the 6.4 tests. Playwright `e2e/tests/spine.spec.ts` 9/9 against Docker `http://localhost:3000`. |
| Stub search on recorded paths | 2.2, 32.13 | partial | No TODO, FIXME, or lorem in app code. Landing ribbon is still a fixture. Lab and Governance now print a `Source:` line from `core.assessment` or `demo_cases_memory`. Live AI fallbacks remain for outages. |
| Foundry main, fast, open, embeddings | 3.2, 3.3, 31.1 | pass | In-container `make providers-check`: Foundry `entra_file`, main 2832 ms, fast 2222 ms, open 2524 ms, embeddings dim 1024 in 1301 ms. File `e2e/artifacts/spine/providers-check.txt`. |
| Deepgram | 13.2, 31.1 | pass | In-container listen nova-3 1869 ms, auth `deepgram_key`. |
| Azure Speech | 13.2, 31.1 | pass | In-container TTS 517 ms, auth `speech_key`. |
| Translator | 3.2, 27.2 i18n | pass | In-container translate en to hi 744 ms. kok, sa, sat HTTP 400 then `main_model`, still `machine_translated`. |
| Content Safety | 12.3, 3.2 | pass | In-container text analyze 1227 ms. |
| ACS | 15.4, 31.1 | partial | In-container identities create 692 ms. Two-browser call across networks was not run. |
| Web PubSub | 18, 31.1 | pass | Local realtime hub (31.1). |
| Key Vault | 14.1, 31.1 | pass | Local wrap file (31.1). |
| `make providers-check` | 05 go-live 8.2 | pass | Must run inside the engine container. Host-only check is not proof. Container: 11 pass, 0 fail. |
| Spec 27.2 offline, Playwright network off | 27.2 | fail | See section 3 and `docs/SPINE_STATUS.md`. Pass 2,3,5,6,9,11,12. Fail 1,4,8,10. Test 7 hung. Fixes are in the tree; web image not rebuilt in this pass. |
| Shot list, 1920 by 1080, rubric | 30.3, UI 9 | partial | Unchanged from Prompt 9 frames. Use the new spine pngs under `e2e/artifacts/spine/` for the 6.4 beats. |
| Lab, Governance, Landing numbers | 8.9, 32.11 | partial | Lab and Governance `Source: core.assessment` on the live stack 17 Sep 2026. Empty assessment table produced zeros (lead n/a, precision 0.00), not 4.2 / 0.11. Overlay now uses `demo_cases_memory` when that table is empty (engine rebuild needed). Landing citations still "verify before citation". |
| `make dev` health-checks data stores first | 05 go-live 8.6 | pass | Unchanged. |
| Architecture shows healthy | 17.12, 23.6 | pass | Unchanged. |
| Spec 32 weakness walk | 32 | partial | Copilot refusal and Deepak T4 are now proven on the live stack. Offline nav and 2.5 s first audio are still misses. |
| Spec 23.6 local stack | 23.6 | partial | Local Docker now reaches Foundry. Azure from scratch still 31.1. |

## Fixes made during Prompt 10A-2

1. `foundry.token` must be a file. `make foundry-token` removes a directory. Compose mounts `infra/.cache` read-only. Auth order: entra file, then `AZURE_OPENAI_API_KEY` plus `AZURE_OPENAI_ENDPOINT`, then DefaultAzureCredential.
2. `make providers-check` execs `python -m app.providers.probe` inside the engine container and prints each auth path.
3. Copilot aggregates call live `main`. Individual questions return `provider=refused` before `gateway.run`.
4. Voice turns stream the first sentence into TTS, run gates in parallel, cache the companion prompt, use `fast` with a short limit.
5. Retrieval uses `embed` (en) and `embed_ml` (hi, hi-Latn, ta) plus rerank. Registry records the choice.
6. Translator HTTP 400 for kok, sa, sat falls back to `main` and stays flagged machine-translated.
7. Lab and Governance overlays compute from `core.assessment` when rows exist, else `demo_cases_memory`. No 4.2 d or 0.11 literals.
8. Service worker v4, offline shells, and crisis send no longer wait on the network. Web image rebuild is still required before 27.2 can be re-proven.

## Ranked remaining risks for the video

1. **First audio is still over 2.5 s.** n=20 from this Mac to eastus2: p50 2914 ms, p95 3429 ms. Streaming helped versus the old 5.2 s combined p50. Do not say under 2.5 s. Show thinking. Owner: you keep a pre-rendered first byte if the take needs instant sound.
2. **Azure URL, Key Vault split, passkeys, and iPhone Home Screen are not done.** `azd env list` is empty. Owner: you, Prompt 10 part 2.
3. **Stage still shares one session across iframes.** Record phone and console as two views.
4. **Lab looks empty until assessment rows exist or the overlay fallback image is rebuilt.** Live UI showed precision 0.00 and "No assessment rows yet." Do not quote those zeros as a trial result. Source line is honest.
5. **Offline 27.2 is not green.** Playwright still failed check-in queue, toolkit, nudges, and plan. Crisis send hung. Fixes are coded. Rebuild web, rerun `audit-offline.spec.ts`, then film airplane mode on the iPhone.
6. **Human review is pending.** TTS, kok/sa/sat catalog, crisis copy.
7. **ACS two-browser call is not proven.**

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

Docker note: engine and engine-acute take `env_file: .env` from `infra/` and mount `infra/.cache` at `/run/manobal/cache`. `FOUNDRY_AD_TOKEN_FILE=/run/manobal/cache/foundry.token`. That path must be a file, not a directory. `make providers-check` runs in the container when engine is up.

---

## 2. Providers

| Provider | Real client? | Env vars (names only) | Fallback | UI labels fallback? | This machine |
|---|---|---|---|---|---|
| Foundry main | Yes, Azure OpenAI v1 + Entra | `FOUNDRY_ENDPOINT`, `AI_DEPLOYMENT_MAIN` | Local scripted handler; circuit breaker | Architecture mode | pass, 4652 ms |
| Foundry fast | Yes | `FOUNDRY_ENDPOINT`, `AI_DEPLOYMENT_FAST` | Same | Yes | pass, 4958 ms |
| Foundry open | Yes | `FOUNDRY_ENDPOINT`, `AI_DEPLOYMENT_OPEN` | Same | Yes | pass, 3345 ms |
| Foundry embeddings | Yes | `FOUNDRY_ENDPOINT`, `AI_DEPLOYMENT_EMBED` | Hash 1024-d vectors | Yes | pass, dim 1024, 4288 ms |
| Deepgram | Yes, listen and speak | `DEEPGRAM_API_KEY`, `DG_STT_MODEL_EN`, `DG_STT_MODEL_HI`, `DG_TTS_VOICE_EN` | Client-final transcript; silent WAV | Voice captions | pass, listen 916 ms |
| Azure Speech | Yes, STT and TTS | `SPEECH_KEY`, `SPEECH_REGION`, `SPEECH_ENDPOINT`, `AZ_TTS_VOICE_HI` | Silent WAV | Architecture mode | pass, tts 505 ms |
| Translator | Yes | `TRANSLATOR_KEY`, `TRANSLATOR_ENDPOINT`, `TRANSLATOR_REGION` | Local Latin map; English plus badge | Machine-translated badge | pass, 402 ms |
| Content Safety | Yes | `CONTENT_SAFETY_ENDPOINT`, `CONTENT_SAFETY_KEY` | Abstain (lexicon and classifier still run) | Architecture mode | pass, 1175 ms |
| ACS | Yes, identities and voip token | `ACS_CONNECTION_STRING` | Labelled demo join | Yes | pass identities, two-browser call not run |
| Web PubSub | Yes when connection string set | `WEBPUBSUB_CONNECTION_STRING` | Local realtime hub | Architecture uses local hub copy | pass, local hub 31.1 |
| Key Vault | Yes when `KEY_PROVIDER=azure` | `KEYVAULT_URI`, `KEY_PROVIDER`, `KV_KEK_NAME`, `KV_TOKEN_KEY_NAME` | Local wrap file (demo only) | Not on Architecture | pass, local wrap 31.1 |

`make providers-check` is the single command. It exits 1 when any row fails. Prompt 10 local run: 11 pass, 0 fail.

---

## 3. Spec 27.2, Playwright offline context

Harness: `e2e/tests/audit-offline.spec.ts` against `http://localhost:3000` after `make dev`, using `context.setOffline(true)`. Latest run 17 Sep 2026, four workers.

| # | Capability | Result | Notes |
|---|---|---|---|
| 1 | Daily check-in (tap) | fail | UI can complete; IndexedDB queue count stayed 0. Save still reached the engine. Fix in tree: enqueue when airplane or fetch fails. |
| 2 | Structured voice check-in | pass | Cached copy and `/audio/grounding.en.wav`. |
| 3 | Assessments | pass | Options rendered after offline navigation. |
| 4 | Toolkit | fail | Toolkit copy missing after offline navigation. Fix in tree: static toolkit shell plus SW v4. |
| 5 | Safety screen | pass | `tel:` visible after offline goto. |
| 6 | SOS by SMS | pass | `sms:` link visible. |
| 7 | Crisis lexicon gate | fail | Hung on `postAcute` while offline. Fix in tree: navigate to safety without awaiting the network. |
| 8 | Local self-care nudges | fail | Home empty or server cards hid Sleep toolkit. Fix in tree: always show local nudges when offline. |
| 9 | My trends | pass | Me page snapshot. |
| 10 | Safety plan, journal, self-only | fail | Save button missing after offline goto (wrong document). Fix in tree: cache `/app/plan` after SW controls. |
| 11 | Acute packet | pass | Retry copy and Tele-MANAS. |
| 12 | Resync | pass | Token still present after network returns. |

Code for the encrypted queue, snapshots, lexicon, SMS, and tel is present. Rebuild the web image and rerun before claiming 27.2.

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
| Governance K1, K3, K10 to K12 | Computed in `compute_overlays()` from `core.assessment` or `demo_cases_memory`. Live 17 Sep 2026: source core.assessment, lead n/a, FP 0.00 because assessment rows were empty. | Partial. Honest source. Do not quote 4.2 d or 0.11. |
| Lab precision, recall, Brier | Same overlay. Live: 0.00 / 0.00 / 0.00 with "No assessment rows yet." | Partial until fallback image is rebuilt or seed writes assessments |
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
| 7 | Dangerous chatbot | Gates, output guard, no diagnosis | Content Safety analyze passed live. Lexicon still runs first. Classifier errors still fail safe to crisis. |
| 8 | English only | Hindi onboarding and voice; Tamil chrome | Karthik still speaks Hindi lines. Owner: Tamil review. |
| 9 | Needs network | Queue, snapshots, SW, edge toggle | Playwright offline nav failed. Do not claim "works with data off" until the phone rehearsal. |
| 10 | Cloud and sovereignty | Hosting caption, Architecture mode | Caption is on Saathi, briefs, Copilot, Architecture, and Trust. Foundry is live on this Mac. |
| 11 | Numbers disagree | One seed | Governance literals disagree with Lab computed metrics. A paused frame can catch that. |
| 12 | Everyone in crisis | Formation majority T0; Imran and Thomas | Formation shows mostly steady cells. |
| 13 | Empty screens | ScreenState | Drift empty; Governance loading; Medical loading. Yes, a judge can see this. |
| 14 | Generic dashboard | Ribbon, formation, Anek | Command still has extra top-bar chrome (UI_NOTES). Recognisable enough on Copilot and formation. |
| 15 | Slow AI | Latency budget, fast class | Combined voice p50 5184 ms vs 1800 ms. Show thinking. Do not claim the budget. |
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
| You | Create an azd environment and finish Prompt 10 part 2 (Key Vault split, HTTPS domain, iPhone Home Screen). Verify landing citations. Rehearse Stage as two views. Human Hindi, Tamil, safety, copy, and symbols reviews. Two-browser ACS call. |
| Cursor, Prompt 10 | Local live providers are wired. Remaining: stream voice first audio under 1.8 s; Azure E2E once azd exists. |
| Cursor, follow-up | SW document cache for 27.2 navigations. Compute Governance and Lab overlay numbers from the seed. Stage dual-session or documented two-device recording. Recapture Governance and Deepak medical after load. |

---

## 8. Prompt 10 local live run (17 Sep 2026)

Chat and embeddings use `https://manobal-ai-resource.openai.azure.com/openai/v1` with Entra (`https://cognitiveservices.azure.com/.default`). `FOUNDRY_ENDPOINT` stays the project URL. A different Azure OpenAI resource in `secrets.env` is ignored. `infra/.env` wins. gpt-5 family calls use `max_completion_tokens` (minimum 128). Alt deployment name is `alt`, never personnel or safety.

Routing gate (live): en open, hi main, hi-Latn main, ta main, crisis recall 1.0.

Voice latency (n=5, Hindi TTS after a fast chat): llm p50 4808 ms p95 6459 ms; tts p50 375 ms p95 430 ms; combined p50 5184 ms p95 6837 ms; budget 1800 ms.

Pre-rendered audio: `live_tts` true, `review` pending. Machine catalog: review pending. Translator 400: kok, sa, sat.

Azure part 2: `azd env list` empty. No `azd up`, no Key Vault identity split, no HTTPS domain, no Azure E2E, no iPhone Home Screen on a deployed host.
