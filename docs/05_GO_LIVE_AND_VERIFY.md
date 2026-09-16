# MANOBAL: Verify, Go Live, Record

The build is finished against local fallbacks. This document takes it from "passes locally" to "real, deployed, recorded".

---

## 1. What the final report actually means

| Item | Status | Impact on the video |
|---|---|---|
| Judge-facing surfaces, Director, shot presets | Built, E2E green twice | Good |
| Foundry, Speech, ACS, Translator, Content Safety | **Labelled local fallbacks** | **Biggest gap.** Saathi's conversation, Hindi and Tamil voice, officer briefs, Copilot, translations, and the Content Safety gate are not yet running on real services. The E2E passing proves the flows, not the AI. |
| Deepgram | Not mentioned | Check whether it is wired to the real API or also on a fallback |
| Azure deployment | Not run (no subscription in Cursor's environment) | Needed for a hosted link, HTTPS, passkeys, and installing on the iPhone |
| Phone | Not verified on a real device | Needed for the phone shots (iPhone Home Screen web app) |
| Architecture `healthy: false` when core Postgres is down | Expected behaviour, but core Postgres should never be down during recording | Make `make dev` start and health-check Postgres first |
| "8k benchmark" | Spec 8.9 asks for 80,000 | Confirm which number the Lab shows; the pitch must quote the measured figure |

Treat the agent's summary as a claim, not a fact. Step A verifies it.

---

## 2. Order of operations

| Step | What | Who | Rough time |
|---|---|---|---|
| A | Verification audit (Prompt 9) | Cursor | Half a day |
| B | Create Azure resources and keys; wire real providers locally first (Prompt 10, part 1) | You, then Cursor | 1 day |
| C | Deploy to Azure with a real HTTPS domain (Prompt 10, part 2) | You and Cursor | Half a day to 1 day |
| D | iPhone on the deployed domain | You | Half a day |
| E | Human reviews: Hindi, Tamil, safety content, copy | Team | 1 day, in parallel with C and D |
| F | Freeze, rehearse, record, edit | Team | 2 days |

Order matters: local real providers before Azure (faster debugging, microphone works on localhost), Azure before the iPhone install (passkeys and Home Screen install need the final HTTPS domain).

---

## 3. Azure setup checklist (you, in the portal or CLI)

1. `az login` and `azd auth login` on your own machine with the credit subscription.
2. Pick one region for everything that supports it (Central India or South India). Note any service that is unavailable there.
3. Create a Foundry resource and a **Foundry project** (gpt-oss-120b requires a project).
4. Deploy models, using the names your config expects:
   - `main`: a GPT-5.x chat model
   - `fast`: a GPT-5.x mini or nano model
   - `open`: gpt-oss-120b
   - embeddings: text-embedding-3-large
   Prefer regional or data zone deployment types where offered; otherwise global, and record it for the Architecture page.
5. Check tokens-per-minute quota on each deployment. Credit subscriptions often start low; request increases now. Keep resilience mode ready in case quota is still low on recording day.
6. Create: Azure AI Speech, Azure AI Translator, Azure AI Content Safety, Azure Communication Services, Key Vault (Premium), Web PubSub, Blob Storage, two PostgreSQL Flexible Servers (PostgreSQL 16; allow-list `timescaledb`, `vector`, `ltree`, `pgcrypto` in server parameters), Managed Redis, Container Registry, Container Apps environment. `azd up` with the repo's Bicep should create most of this; create by hand only what fails.
7. Entra ID: register the officer app in a tenant you control; create app roles; assign your team's test users. If registration is blocked, keep the labelled demo login.
8. Deepgram: create an API key with only the permissions the app needs.
9. Put every secret in Key Vault; nothing in the repo.
10. Domain: use a custom domain or the Front Door or Container Apps default HTTPS hostname. Decide now; passkeys and the iPhone install depend on it.

---

## 4. Provider smoke tests (run locally first, then on Azure)

| Test | Pass condition |
|---|---|
| `main`, `fast`, `open` each answer a hello prompt via managed identity or key | Response under 3 s, provider recorded in `provider_call` |
| Model routing gate (Hindi, Hinglish, English) | Decision written to model registry; crisis handoff 100% for both models |
| Deepgram English streaming with end-of-turn | Final transcript and end-of-turn event |
| Deepgram Hindi (`hi`) and Hinglish (`multi`) | Transcript in the expected script after transliteration |
| Azure STT Tamil | Correct transcript on Karthik's fixture |
| Azure TTS Hindi, Tamil, English (India); Deepgram Flux English | Audio plays in the app; voice names from config |
| Voice turn latency | End of speech to first audio under 1.8 s on your network |
| Content Safety self-harm and Prompt Shields | Red-team fixtures produce expected hits |
| Translator | Hindi and Tamil catalog strings regenerate and are flagged machine-translated |
| ACS | Voice and video call between two browsers on two different networks |
| Web PubSub | T4 alert appears on Welfare and Medical within 2 s |
| Key Vault | Vault identity can wrap and unwrap; engine identity is refused |
| Pre-rendered audio | Safety and toolkit clips regenerated with real voices and reviewed |

---

## 5. iPhone checklist (after Azure is live)

The full iPhone procedure, including the code hardening Cursor must do, is in `06_MANOBAL_WALKTHROUGH.md` (Phases 6 and 9). Summary:
1. Open the final HTTPS domain in Safari, Share, Add to Home Screen, open it from the icon.
2. Verify passkeys, Web Push, microphone, a Hindi voice turn, and the offline segment (Wi-Fi off and Cellular Data off, voice calls still available).
3. Mirror to the Mac with QuickTime Player for recording.

## 6. Human reviews (cannot be delegated to the agent)

- **Hindi:** a native speaker reviews every Hindi string, the Hindi corpus, and the pre-rendered Hindi audio.
- **Tamil:** same for Karthik's path.
- **Safety content:** the crisis lexicon, safety screen, safety plan prompts, PFA content, and Deepak's scripted message are reviewed by someone with mental health training (a college counsellor or psychology faculty member). Deepak's message must be non-graphic and contain no method details.
- **Copy pass:** read every screen in the shot list aloud; cut words.
- **Symbols pass:** check every illustration and icon against the banned list.
- **Numbers pass:** every statistic on the landing page and in narration has a verified source and date.

---

## 7. Pre-recording gate (all must be true)

- [ ] Prompt 9 audit shows no unexplained stubs in any recorded path
- [ ] All provider smoke tests pass on the deployed environment
- [ ] E2E demo spine passes twice on the Azure URL with real providers (resilience mode off)
- [ ] Resilience mode tested as a backup with cached outputs for every scripted beat
- [ ] iPhone Home Screen web app verified: full screen, passkeys, push, microphone, offline
- [ ] Offline segment rehearsed on the phone with data genuinely off
- [ ] Hindi, Tamil, safety, copy, symbols, numbers reviews done
- [ ] Build and seed snapshot frozen and tagged
- [ ] Lab benchmark figure and all Lab metrics noted for the script
- [ ] Captions ready: prototype hosting, synthetic data
- [ ] Two full rehearsals of the 8-minute script from Director resets

---

## 8. Prompt 9: Verification audit

Paste the execution protocol from `03_CURSOR_PROMPTS.md` above it, in a fresh chat.

```
Goal: an honest status of the build before we go live. Do not add features.

Read: docs/02_MANOBAL_MVP_BUILD_SPEC.md sections 2.2, 23.6, 24, 27.2, 29, 30.3, 31.1, 32; docs/04_MANOBAL_UI_DIRECTION.md sections 0, 8, 9; docs/PROGRESS.md; docs/SHOT_LIST.md.

Do:
1. Search the codebase for TODO, FIXME, mock, stub, fake, placeholder, hardcoded, fallback, lorem, and any fixture used outside tests or the gallery. For each hit in a path used by the demo spine or a shot, list file, line, what it does, and whether it is acceptable.
2. For every provider (Foundry main, fast, open, embeddings; Deepgram; Azure Speech; Translator; Content Safety; ACS; Web PubSub; Key Vault), report: is the real client implemented, which env vars it needs, what the fallback does, and whether the UI labels the fallback. Add a single `make providers-check` command that calls each real provider once and prints a pass or fail table.
3. For every numbered item in spec 27.2, verify it works with the network disabled in Playwright (offline context) and report pass or fail.
4. For every shot in SHOT_LIST.md, run the preset from a reset, take a 1920 by 1080 screenshot, and score it with the UI review rubric. Save to e2e/artifacts/audit/.
5. Check every number shown in Lab, Governance, and Landing is computed from the database or a cited source. Report the benchmark size actually run and change it to 80,000 in memory if it is not.
6. Make `make dev` start and health-check core Postgres, vault Postgres, and Redis before the engine; the Architecture page must show healthy when the stack is up.
7. Walk spec 32 item by item and report, per item, where it is prevented and whether any recorded screen could still show it.
8. Write docs/AUDIT.md with: a status table (item, spec reference, status pass, partial, or fail, evidence), a list of every fix you made during the audit, and a ranked list of remaining risks for the video.

Done when: docs/AUDIT.md exists, every partial or fail has a named owner step, and make providers-check exists.
```

---

## 9. Prompt 10: Go live with real providers

> Superseded for the Mac and iPhone setup by Prompts 10A and 10B in `06_MANOBAL_WALKTHROUGH.md` Part C. Use those.

Run part 1 after you have created the Azure resources and put keys in a local `.env` (never committed). Run part 2 after part 1 passes.

```
Goal: replace every local fallback with the real provider, first locally, then on Azure.

Read: spec 3.2, 3.3, 12, 13, 15.4, 18, 20, 21, 23.3, 27.5, 31; docs/AUDIT.md; docs/05_GO_LIVE_AND_VERIFY.md sections 3 to 5.

Part 1, local with real providers:
1. Load provider settings from .env locally and from Key Vault on Azure through the same settings class. Fail fast with a clear message listing any missing variable.
2. Switch the router to real providers for main, fast, open, embeddings, Deepgram, Azure Speech, Translator, Content Safety, ACS, while keeping fallbacks for outages and resilience mode.
3. Run make providers-check and every test in section 4 of docs/05_GO_LIVE_AND_VERIFY.md that can run locally. Record results in docs/AUDIT.md.
4. Run the eval suite live (not recorded) including the model routing gate; commit the routing decision.
5. Regenerate pre-rendered audio with real voices for English, Hindi, and Tamil; regenerate machine translations with Translator; flag both for human review.
6. Refresh recorded fixtures and resilience-mode caches from real outputs for every scripted beat.
7. Tune voice latency to the budget in spec 13.3; report measured percentiles.
8. Make sure the prototype hosting caption (spec 27.5) appears wherever real cloud AI output appears.

Part 2, Azure:
9. Run azd up with the repo's Bicep; fix any resource or permission failure; confirm managed identities and the Key Vault access split (vault identity can wrap and unwrap; engine identity is refused).
10. Enable PostgreSQL extensions through server parameters, run migrations, seed, and snapshot on Azure; confirm restore under 20 s or document the measured time.
11. Configure the final HTTPS domain; set the passkey relying party ID to the domain; complete the iPhone hardening list in 06_MANOBAL_WALKTHROUGH.md.
12. Run make providers-check and the full E2E demo spine against the Azure URL twice with a reset between, resilience mode off. Then run it once with resilience mode on and one provider forced down.
13. Update the Architecture page with the actual regions and deployment types in use.
14. Update DEMO_RUNBOOK.md with Azure-specific steps: warm-up, quota check, reset, fallback switches.

Done when: every provider test passes live, the Azure E2E is green twice, the iPhone Home Screen install works on the deployed domain, and docs/AUDIT.md shows no fail items on recorded paths.
```
