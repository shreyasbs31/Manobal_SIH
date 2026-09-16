# MANOBAL: Master Walkthrough (Mac, iPhone, Azure)

**Replaces** the earlier Android-based walkthrough. Follow it top to bottom. Every phase lists what **you** do, what you **give Cursor**, and a **checkpoint**. Do not move on until the checkpoint passes.

---

## Part A: Decisions already made for you

| Topic | Decision | Why |
|---|---|---|
| Your computer | Mac (Apple Silicon assumed; Intel works the same except where noted) | What you have |
| Phone | iPhone, with Saathi installed as a **Home Screen web app** | iOS supports installed web apps with push notifications (iOS 16.4 and later) and, since iOS 26, every site added to the Home Screen opens as a web app by default. Apple does not accept pure web wrappers in the App Store, so this is the right iPhone path. |
| Android | Optional only (Phase 14, Android emulator on the Mac) | Not needed for the video |
| Azure | Your paid subscription (about ₹9 lakh credits) | Student region restrictions do not apply to a paid subscription, but quotas still do |
| App and data region | Central India | Data residency story; check each service is offered there |
| AI region | Where your chosen models are offered; prefer an Indian region, otherwise a global deployment, recorded on the Architecture page | Model availability varies by region |
| AI provider | Microsoft Foundry for every language model, embedding, reranking, evaluation, and image model, billed to your Azure credits | One bill, one security boundary |
| Speech | Deepgram (your $15,000 credit) for English and Hindi speech-to-text and English voice; Azure AI Speech for Hindi, Tamil, and other Indian voices and Tamil speech-to-text | Deepgram has no Hindi voice |
| OpenAI direct API and other keys | Not used on any path that touches personnel data; OpenAI direct is only an emergency fallback for officer-side generation if Foundry is down | Keeps the "everything inside Azure" story true |
| Domain | Buy a neutral custom domain (for example `manobal.app` or `manobal-saathi.in`; never anything that looks like a government domain) | Passkeys and the iPhone install are tied to the domain, and it looks professional on video |
| Deployment | Azure Container Apps with `azd`, images built in Azure Container Registry | Apple Silicon builds ARM images by default; Azure Container Apps needs linux/amd64 |

### Does the iPhone change anything?
Yes, in specific, manageable ways. All of these are handled in Prompt 10A:

| iPhone behaviour | What we do |
|---|---|
| Push notifications only work after "Add to Home Screen"; a Safari tab cannot receive them | Install from the Home Screen; ask for notification permission from a button inside the installed app |
| Background Sync is not supported | Resync on app open, when the network returns, when the app becomes visible, and on a retry loop while open |
| Sound cannot autoplay without a tap | Unlock audio on the first tap in the app so the safety screen and voice replies can play later |
| Vibration (haptics) API is not available | Visual feedback instead; haptics stay on Android and desktop only |
| Web Bluetooth is not available | Simulated wearable on iPhone |
| Notch, Dynamic Island, home indicator | Safe-area padding everywhere |
| Inputs under 16 px cause auto-zoom | Minimum 16 px input text |
| `100vh` is unreliable | Use dynamic viewport units |
| Microphone and service worker need HTTPS | Test through an HTTPS tunnel locally, then on the real domain |
| Push subscriptions can go stale if a push arrives without a visible notification | Always show a notification for every push; re-check the subscription on each app open |
| Passkeys | Work through iCloud Keychain, but only on the final domain |

---

## Part B: Golden rules

1. Never paste API keys, passwords, connection strings, or private keys into a Cursor chat.
2. Your secrets file is `infra/.env` (template `infra/.env.example`). Other secret material lives in `infra/secrets.env` and `infra/keys/`. Keep all of them out of git (already done) and out of Cursor's context (Phase 1).
3. Turn on **Privacy Mode** in Cursor settings.
4. Run each Cursor prompt in a fresh Agent chat with the execution protocol from `03_CURSOR_PROMPTS.md` on top.
5. When something fails, give Cursor the exact command, the full error, and the phase number (template in Phase 15).
6. Commit, push, and tag at the end of every phase (`git tag phase-N-done && git push --tags`).

---

## Phase 0: Set up the Mac from zero (1 to 2 hours)

### 0.1 Base tools
Open Terminal and run these one by one.
```
xcode-select --install
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
Homebrew prints two "Next steps" commands to add `brew` to your PATH. Run them, then close and reopen Terminal.

```
brew install git gh jq fnm uv azure-cli libpq ffmpeg cloudflared
brew link --force libpq
brew tap azure/azd && brew install azd
brew install --cask docker google-chrome obs
```
Install DaVinci Resolve from the Blackmagic website (or use any editor you prefer).

### 0.2 Node and pnpm
Ask Cursor (in any chat): "Which Node.js and pnpm versions does this repo require? Print only the versions." Then:
```
echo 'eval "$(fnm env --use-on-cd)"' >> ~/.zshrc && source ~/.zshrc
fnm install <NODE_VERSION> && fnm default <NODE_VERSION>
corepack enable
corepack prepare pnpm@<PNPM_VERSION> --activate
node -v && pnpm -v
```

### 0.3 Python
```
uv python install 3.12
uv --version
```

### 0.4 Docker Desktop
1. Open Docker Desktop and finish setup.
2. Settings, **General**: turn on "Use Rosetta for x86_64/amd64 emulation on Apple Silicon".
3. Settings, **Resources**: at least 6 CPUs and 12 GB memory if your Mac allows it (the seed and engine are heavy).
4. Check: `docker run --rm hello-world`.

### 0.5 GitHub and git
```
git config --global user.name "<your name>"
git config --global user.email "<your email>"
gh auth login
```

### 0.6 Playwright browsers
From the repo root:
```
pnpm install
pnpm exec playwright install chromium webkit
```
WebKit is the engine Safari uses; it lets Cursor test iPhone layouts on the Mac.

### 0.7 macOS permissions (needed later for recording)
System Settings, **Privacy & Security**:
- **Screen & System Audio Recording**: allow OBS and QuickTime Player.
- **Microphone**: allow Chrome, OBS, QuickTime Player.
- **Camera**: allow QuickTime Player (the iPhone appears as a camera source).

**Checkpoint 0:** `git`, `gh`, `node`, `pnpm`, `uv`, `az`, `azd`, `docker`, `cloudflared`, `ffmpeg` all print versions.

---

## Phase 1: Repo hygiene and first local run (1 hour)

### 1.1 Create `.cursorignore` at the repo root
```
cat > .cursorignore << 'EOF'
infra/.env
infra/.env.*
!infra/.env.example
infra/secrets.env
infra/keys/
**/*.pem
**/*.p12
**/*.p8
**/*.keystore
**/*.jks
EOF
git add .cursorignore && git commit -m "Keep secrets out of agent context"
```

### 1.2 Add two lines to the Cursor rules file
Open `.cursor/rules/manobal.mdc` and add:
```
- Secrets live in infra/.env, infra/secrets.env and infra/keys/. Never open, print, or echo them; use the settings loader and masked checks. Never ask the user to paste a secret into chat.
- The primary phone is an iPhone (Home Screen web app). The development machine is an Apple Silicon Mac; images for Azure must be built for linux/amd64 (remote build in Azure Container Registry).
```

### 1.3 Copy the latest docs into the repo
Put the newest versions of `02_MANOBAL_MVP_BUILD_SPEC.md`, `03_CURSOR_PROMPTS.md`, `04_MANOBAL_UI_DIRECTION.md`, `05_GO_LIVE_AND_VERIFY.md`, and this file into `docs/`, replacing older copies. Commit.

### 1.4 First local run
```
make dev
```
Open `http://localhost:3000`, then `/app` and `/stage`. If `make dev` fails, give Cursor the full output (Phase 15 template). A common Apple Silicon issue is an image without an ARM build; ask Cursor to switch to a multi-arch image or set `platform: linux/amd64` for that one service.

**Checkpoint 1:** the app runs locally on port 3000, `.cursorignore` exists, rules and docs updated.

---

## Phase 2: Verification audit (half a day)

### You give Cursor
Fresh chat, execution protocol, then **Prompt 9** from `05_GO_LIVE_AND_VERIFY.md` section 8, plus this line at the end:
```
Environment note: the env file is infra/.env (template infra/.env.example). Do not open infra/.env, infra/secrets.env, or infra/keys/.
```

### You do after
1. Read `docs/AUDIT.md`.
2. Look at every image in `e2e/artifacts/audit/` yourself and note screens you don't love.
3. Send Cursor the follow-up:
```
These screens need work before recording: [shot ids and what bothers you in plain words].
Fix them using docs/04_MANOBAL_UI_DIRECTION.md, re-run the review loop, update docs/AUDIT.md.
```

**Checkpoint 2:** `docs/AUDIT.md` exists, `make providers-check` exists, you have looked at every screenshot.

---

## Phase 3: Azure foundation (2 hours)

### 3.1 Sign in and select the subscription
```
az login
az account list -o table
az account set --subscription "<SUBSCRIPTION_ID>"
azd auth login
```

### 3.2 Confirm there are no blocking policies
```
az policy assignment list --query "[].{name:displayName}" -o table
```
A paid subscription normally shows none that restrict regions. If you see "Allowed locations" or similar, read its parameters in the portal (Policy, Assignments) and tell Cursor the allowed list.

### 3.3 Register resource providers
```
for ns in Microsoft.CognitiveServices Microsoft.App Microsoft.DBforPostgreSQL Microsoft.KeyVault \
  Microsoft.SignalRService Microsoft.Communication Microsoft.Cache Microsoft.ContainerRegistry \
  Microsoft.OperationalInsights Microsoft.Insights Microsoft.Storage Microsoft.ManagedIdentity \
  Microsoft.Cdn Microsoft.Network; do az provider register --namespace $ns; done
```

### 3.4 Budget alert (still worth it)
Portal, **Cost Management**, **Budgets**: create a monthly budget (for example ₹1.5 lakh) with alerts at 50%, 80%, 100%. This catches runaway usage, not normal use.

### 3.5 Buy the domain
1. Buy a neutral domain from any registrar.
2. Optional but tidy: create an **Azure DNS zone** for it and point the registrar's nameservers to Azure's, so all records live in Azure.

### 3.6 Start approvals early
Some frontier models are limited access and need a request form, and every deployment starts with a tokens-per-minute quota. Do Phase 4.1 and 4.2 today so any approval clock starts now.

**Checkpoint 3:** subscription selected, providers registered, budget set, domain bought.

---

## Phase 4: AI and speech resources (half a day)

### 4.1 Foundry project
1. Open the Foundry portal (ai.azure.com), **Create project**. Pick the region where the models below are offered; if an Indian region offers them, use it.
2. gpt-oss-120b needs a Foundry project, so always create the project, not only a resource.

### 4.2 Deploy models (the full map)
First ask Cursor: "Print the model class names and the deployment-name variables the app expects from infra/.env.example. Names only." Name each deployment to match.

| Class | Model to deploy | Used for | Notes |
|---|---|---|---|
| `main` | Latest generally available GPT-5.x chat model | Officer briefs, Copilot, HQ brief, transparency report, Hindi companion fallback | High quota |
| `fast` | GPT-5.x mini | Crisis classifier, output guard, extraction, brief verification, voice turns | Highest quota; latency critical |
| `open` | gpt-oss-120b | Saathi companion (if it passes the Hindi gate) | The "same model can run on force hardware" story |
| `embed` | text-embedding-3-large | Corpus search | |
| `embed_ml` | Cohere embed v4 (multilingual) | Corpus search in Hindi and Tamil | The eval picks `embed` or `embed_ml` per language |
| `rerank` | Cohere rerank v4 | Sharper retrieval for ask mode | |
| `judge` | A different model family, for example DeepSeek-V3.2 or Mistral Large | Grades eval answers so the companion is never graded by its own family | Eval-time only |
| `image` | FLUX.2 pro (or an Azure OpenAI image model) | Regenerating the illustration kit | Review every image against the banned list |
| `stt_fallback` | An Azure OpenAI transcription model, if offered in your region | Hindi speech-to-text fallback | Optional |
| `alt` | Grok 4.1 fast | Optional fallback for officer-side text only | Never personnel-facing |

For each deployment:
- Choose a regional deployment type in an Indian region if listed; otherwise global. Write down what you chose.
- Set tokens-per-minute to the maximum the portal allows; if it is low, open **Quotas** and request more.
- Keep the default content filters on.

### 4.3 Other Azure AI services (create in Central India unless unavailable)
| Resource | Notes |
|---|---|
| Azure AI Speech | In **Speech Studio, Voice Gallery**, confirm and write down: `hi-IN-SwaraNeural`; one bilingual Hindi-English voice (for example `hi-IN-AaravNeural` or `hi-IN-AnanyaNeural`); a Tamil voice; an English (India) voice |
| Azure AI Translator | Covers most scheduled languages; the app uses `main` for the rest |
| Azure AI Content Safety | Self-harm category and Prompt Shields |
| Azure Communication Services | Choose India as the data location if offered |

### 4.4 Deepgram
1. Deepgram console, your project, **API Keys**, create a key with the Member role.
2. In the playground, test Nova-3 English and Nova-3 with language `hi` on short clips.
3. Pick a Flux Indian-accent English voice (for example `flux-meena-en`) and write it down.

### 4.5 Fill `infra/.env`
Open `infra/.env` in a plain editor outside Cursor (`nano infra/.env` in Terminal), fill every value from 4.1 to 4.4, save.

**Checkpoint 4:** every deployment exists with adequate quota, voices confirmed, `infra/.env` filled.

---

## Phase 5: Real providers locally, full model map, iPhone hardening (1 to 2 days)

### You do
```
make dev
make providers-check
```
Save the printed table.

### You give Cursor
Fresh chat, execution protocol, then **Prompt 10A** (Part C of this document), followed by:
```
Environment facts:
- App region: centralindia. AI region: [region]. Speech region: [region].
- Deployments (class, deployment name, type): [list]
- Voices: Hindi [name], Hinglish [name], Tamil [name], English India [name], Deepgram English [name]
- providers-check output: [paste the table, no secrets]
```

### You do after
1. On the Mac in Chrome, open `/stage` and personally test: Arjun Hindi voice check-in, Karthik Tamil voice check-in, Deepak's typed and spoken distress (no AI reply, T4 fires), the Hindi case brief, a Hindi Copilot question, and a Copilot question that should be refused.
2. Review the illustration candidates Cursor generated; tell it which to adopt.
3. Note anything wrong, slow, or off and send fix-ups (Phase 15).

**Checkpoint 5:** providers-check all pass, live evals pass, routing decisions recorded, you have heard Hindi and Tamil voice.

---

## Phase 6: First iPhone test through an HTTPS tunnel (1 to 2 hours)

The iPhone needs HTTPS for the microphone and service worker, so use a temporary tunnel before deploying.

1. Run `make tunnel` (added by Prompt 10A). It prints an `https://...trycloudflare.com` address.
2. On the iPhone, open that address in **Safari**.
3. Tap **Share**, **Add to Home Screen**, keep "Open as Web App" on, **Add**.
4. Open MANOBAL from the Home Screen icon. It should open full screen with no Safari bars.
5. Test: sign in with the demo persona (PIN, since passkeys are disabled in tunnel mode), a check-in, a Hindi voice turn (allow the microphone), the toolkit, the safety screen audio, enabling notifications from the in-app button.
6. Offline test: turn off Wi-Fi in Control Center, then **Settings, Mobile Service (or Cellular), Mobile Data** off. Normal phone calls still work. In the app: check-in, structured voice check-in, toolkit, safety screen, helpline call button, SMS SOS, queued count. Turn data back on and watch the sync drain.
7. Delete the tunnel icon from the Home Screen afterwards (the real one comes in Phase 9).

Report any failure with the Phase 15 template, including your iPhone model and iOS version (Settings, General, About).

**Checkpoint 6:** everything above works on the iPhone through the tunnel.

---

## Phase 7: Deploy to Azure (1 day)

### 7.1 You give Cursor
Fresh chat, execution protocol, **Prompt 10B** (Part C), plus:
```
Azure facts:
- Subscription: [id]. App region: centralindia. AI region: [region].
- Existing AI resources created in the portal (reference, do not recreate): Foundry [resource and project names], Speech [name], Translator [name], Content Safety [name], ACS [name].
- Domain: [domain]. DNS: [Azure DNS zone name, or registrar].
Before running anything, print the list of azd environment variables I must set and the exact commands.
```

### 7.2 You run what Cursor prints (in your own Terminal)
Typically:
```
azd env new manobal-demo
azd env set AZURE_SUBSCRIPTION_ID "<id>"
azd env set AZURE_LOCATION centralindia
# plus any variables Cursor lists
azd up
```
If it fails, send the full error with the Phase 15 template.

### 7.3 Give yourself Key Vault access, then add secrets
Portal: the Key Vault, **Access control (IAM)**, **Add role assignment**, **Key Vault Secrets Officer**, your account.
Then, in your Terminal (never in Cursor), for each secret name Cursor lists:
```
az keyvault secret set --vault-name "<KV_NAME>" --name "<SECRET-NAME>" --value "<value>"
```

### 7.4 PostgreSQL extensions (verify on both servers)
```
az postgres flexible-server parameter show -g <RG> -s <SERVER> --name azure.extensions
az postgres flexible-server parameter show -g <RG> -s <SERVER> --name shared_preload_libraries
```
If `timescaledb`, `vector`, `ltree`, or `pgcrypto` are missing, ask Cursor to fix the Bicep, or run:
```
az postgres flexible-server parameter set -g <RG> -s <SERVER> --name azure.extensions --value "TIMESCALEDB,VECTOR,LTREE,PGCRYPTO,UUID-OSSP"
az postgres flexible-server parameter set -g <RG> -s <SERVER> --name shared_preload_libraries --value "<existing values>,timescaledb"
az postgres flexible-server restart -g <RG> -n <SERVER>
```
The set command replaces the whole value, so keep the existing entries.

### 7.5 Migrate, seed, snapshot
Run the Container Apps job or command Cursor gives you. Confirm the seed finishes and the snapshot exists.

### 7.6 Custom domain
Portal: the **web** Container App, **Custom domains**, **Add custom domain**, **Managed certificate**. Add the CNAME and TXT records it shows (in Azure DNS or at your registrar), click **Validate**, then **Add**. Repeat for any other public hostname Cursor names. Wait until the certificate shows as issued.

### 7.7 Tell Cursor the domain is live
```
The custom domain https://[domain] is bound with a managed certificate. Continue Prompt 10B from step 8: passkey relying party ID, CSP, push, E2E runs.
```

**Checkpoint 7:** the domain loads over HTTPS, providers-check passes on Azure, the E2E demo spine is green twice on the domain with resilience mode off.

---

## Phase 8: Officer sign-in with Entra ID (1 to 2 hours, recommended)

1. Portal, **Microsoft Entra ID**, **App registrations**, **New registration**, name `MANOBAL Consoles`. Add the redirect URIs Cursor prints (ask: "print the exact Entra redirect URIs for local and production").
2. **App roles**: `uwo`, `counsellor`, `mo`, `commander`, `hq`, `wdec`, `dpo`, `admin`, `hrms_integrator`.
3. **Users**: create test officers (for example `sunita.rawat@<your tenant>`), require MFA; set up Microsoft Authenticator on your iPhone for them.
4. **Enterprise applications**, the app, **Users and groups**: assign one role per test user.
5. Store the tenant ID and client ID (and a client secret only if Cursor's implementation needs it) in Key Vault.
6. Tell Cursor: "Entra app registered. Secret names in Key Vault: [names]. Roles: [list]. Wire and test sign-in per role on production."

**Checkpoint 8:** each test officer signs in with MFA and lands in the right console, or you have chosen the labelled demo login.

---

## Phase 9: iPhone on the real domain (1 to 2 hours)

1. iPhone Settings, your name, **iCloud**, **Passwords** (Keychain) on. This is where passkeys are stored.
2. Safari, open `https://[domain]/app`, **Share**, **Add to Home Screen**, **Add**.
3. Open from the icon and test:
   - [ ] Full screen, no Safari bars, correct icon and status bar colour
   - [ ] Content clear of the notch or Dynamic Island and the home indicator
   - [ ] Passkey creation and sign-in (Face ID prompt)
   - [ ] Notification permission from the in-app button; a T1 nudge arrives with the fixed short text
   - [ ] Microphone and a Hindi voice turn; Tamil voice turn as Karthik
   - [ ] Safety screen audio plays after the distress message
   - [ ] Offline segment exactly as Phase 6 step 6
   - [ ] Close and reopen the app: data still there, queued items sync
4. Report failures with the Phase 15 template plus iPhone model and iOS version.

**Checkpoint 9:** every box ticked.

---

## Phase 10: Human reviews (1 day, alongside Phases 7 to 9)

Ask Cursor:
```
Export for human review, without changing code:
1. docs/review/hindi.csv (key, English, Hindi) for every UI string, corpus title, and pre-rendered audio script.
2. docs/review/tamil.csv for Karthik's path.
3. docs/review/safety.md with the crisis lexicon, safety screen copy, safety plan prompts, psychological first aid content, the one-exception text, and Deepak's scripted message.
4. docs/review/numbers.md with every statistic shown anywhere, its source and date.
5. docs/review/illustrations.md with every illustration file and thumbnail path.
```

| Review | Reviewer | Output |
|---|---|---|
| Hindi | Native speaker | Corrected `hindi.csv` |
| Tamil | Native speaker | Corrected `tamil.csv` |
| Safety | Someone with mental health training (college counsellor or psychology faculty) | Comments in `safety.md`; Deepak's message non-graphic, no method details |
| Numbers | Teammate | Each figure checked against its source |
| Symbols | Teammate | Illustrations checked against UI direction section 8 |
| Copy | Whole team | Read every recorded screen aloud |

Then give Cursor:
```
Apply the human review results in docs/review/. Update catalogs, corpus, lexicon, safety copy, and pre-rendered audio; regenerate audio for changed lines; replace or remove flagged illustrations; mark reviewed strings as reviewed. Re-run copy-lint, evals, and the UI review loop for affected screens. Redeploy.
```

**Checkpoint 10:** all reviews applied, redeployed, re-tested.

---

## Phase 11: Freeze and rehearse (1 day)

1. Ask Cursor: "Prepare the recording freeze: bump versions, snapshot on Azure, set minimum replicas to 1 on all apps, and print the exact warm-up, reset, and quota-check commands."
2. `git tag recording-freeze && git push --tags`. After this, only fix recording blockers.
3. Rehearse the 8-minute script twice from Director resets with a stopwatch.
4. Test resilience once: force one provider down in the Director and run the spine.
5. Write and time the narration against `docs/SHOT_LIST.md`.

**Checkpoint 11:** two clean rehearsals, resilience tested, narration timed.

---

## Phase 12: Record on the Mac with the iPhone (1 to 2 days)

### 12.1 Mirror the iPhone
1. Connect the iPhone to the Mac with a cable; tap **Trust** on the phone.
2. Open **QuickTime Player**, **File**, **New Movie Recording**.
3. Click the small arrow next to the record button; choose your **iPhone** as both Camera and Microphone. The iPhone screen appears live, with its audio.
4. On the iPhone: turn on a **Focus** (Do Not Disturb), set brightness high, set Auto-Lock to Never during takes (Settings, Display & Brightness), and restore it afterwards.

### 12.2 OBS scenes
1. **Phone only**: Window Capture of the QuickTime window, cropped to the phone.
2. **Desktop only**: Window Capture of Chrome at 1920 by 1080, browser zoom 110 to 125%.
3. **Split**: both captures side by side, for the continuous crisis take (S11) and the reveal and ledger shot (S08).
4. Audio: add application audio capture for QuickTime (phone audio) and Chrome (console chimes).
5. Output: 1920 by 1080, 60 fps, high-quality recording.

### 12.3 Take routine (every take)
Director reset, warm-up, quota check, notifications off on the Mac, Focus on the iPhone, then record the shot from `docs/SHOT_LIST.md`. Keep S11 and one voice turn as single uninterrupted takes. Record the offline segment with Wi-Fi and Mobile Data genuinely off.

### 12.4 Narration and captions
1. Record narration in a quiet room (QuickTime **New Audio Recording**, or a USB microphone).
2. Normalise loudness:
```
ffmpeg -i narration.wav -af loudnorm=I=-16:TP=-1.5:LRA=11 narration_norm.wav
```
3. Generate English captions with `make captions FILE=narration_norm.wav` (added in Prompt 10A); review and fix the SRT by hand. Add reviewed Hindi subtitles for Hindi segments.

### 12.5 Edit and export
Short cut and full cut per spec section 30; captions for "Prototype: open-weight model hosted on Azure. Deployable on force servers." and "Synthetic data"; export 1080p60 H.264; watch once on the iPhone and once on the Mac before submitting.

**Checkpoint 12:** both cuts exported, watched end to end, captions correct.

---

## Phase 13: Submit and keep it running

- [ ] Video (both cuts if allowed) and link
- [ ] Hosted demo link on your domain with role cards (if the rules allow)
- [ ] Repository link with README, architecture diagram, synthetic generator, eval results, model card
- [ ] One-page PDF mapping every problem statement item to a screen and a video timestamp
- [ ] PPT updated so every claim matches the build (Lab numbers, real models and regions, offline wording from spec 27.1)
- [ ] Keep minimum replicas at 1 during the evaluation window so judges never hit a cold start; check the Azure dashboard daily
- [ ] After results: scale to zero and stop the PostgreSQL servers

---

## Phase 14: Optional Android package (half a day)

Only if you want an Android package for completeness.
1. Install Android Studio on the Mac; create an emulator (Pixel, recent Android, ARM image).
2. `npm i -g @bubblewrap/cli`, then `bubblewrap init --manifest https://[domain]/<manifest path>` and `bubblewrap build`.
3. Get the SHA-256 with `keytool -list -v -keystore ./android.keystore -alias android`, then `bubblewrap fingerprint add <SHA256>` and `bubblewrap fingerprint generateAssetLinks`; check the file is not empty.
4. Ask Cursor to serve it at `/.well-known/assetlinks.json` and redeploy.
5. `adb install app-release-signed.apk` into the emulator and check it opens without an address bar.
6. Keep the keystore and its passwords safe and out of the repo.

---

## Phase 15: Fix-up template (use any time)

```
Phase: [number and name]
Device: [Mac model / iPhone model and iOS version / browser]
What I did: [exact steps or command]
What I expected: [one sentence]
What happened: [one sentence]
Evidence: [full error text, screenshot path, or shot id]
Constraints: follow docs/02 and docs/04; change nothing outside this problem; add a test that would have caught it; update docs/AUDIT.md.
```

---

## Part C: Updated prompts for this setup

Use these instead of Prompt 10 in `05_GO_LIVE_AND_VERIFY.md` (Prompt 9 there is unchanged). Paste the execution protocol above each.

### Prompt 10A: Real providers, full model map, iPhone hardening, tunnel

```
Goal: every provider real and locally verified, the full Foundry model map in use, and Saathi hardened for iPhone Home Screen use.

Read: docs/02 sections 3.2, 3.3, 12, 13, 17.1, 23.3, 27; docs/04 section 9; docs/05 section 4; docs/06_MANOBAL_WALKTHROUGH.md Parts A and C; docs/AUDIT.md.

Secrets: settings load from infra/.env locally and from Key Vault on Azure through one settings class. Never open or print infra/.env, infra/secrets.env, or infra/keys/. Fail fast listing missing variable names only. providers-check masks all values.

Do:
1. Model classes: extend the router and config to main, fast, open, embed, embed_ml, rerank, judge, image, stt_fallback, alt, each mapped to a Foundry deployment name from env. alt is restricted to officer-side text tasks. OpenAI direct is an optional emergency fallback for officer-side generation only, off by default.
2. Retrieval: use embed or embed_ml per language (decided by eval), then rerank; ask mode still cites chunk ids.
3. Evals: run live, including the routing gate (open vs main per language) and the embedding choice per language; grade with the judge model; add Foundry safety evaluators if available in the region; write decisions to the model registry.
4. Content filters: an Azure content-filter error on any personnel-facing call is a safety event: no error shown, route to the acute path if the input came from Saathi, count it in agent-safety metrics.
5. Speech: Deepgram Nova-3 English with end-of-turn; Nova-3 hi and multi with keyterms and transliteration; Azure Speech for Tamil and other Indian locales; stt_fallback if configured. TTS: Deepgram Flux Indian-accent English; Azure Hindi, Hinglish, and Tamil voices from config.
6. Regenerate pre-rendered audio (English, Hindi, Tamil) and machine translations; mark them for human review.
7. Generate illustration candidates with the image deployment using docs/04 section 2.6 into a review folder; do not replace existing art until I approve.
8. Refresh resilience-mode caches from real outputs for every scripted beat.
9. Tune voice latency to spec 13.3 and report p50 and p95.
10. Captions tool: `make captions FILE=...` transcribes an audio file with Deepgram and writes SRT and VTT.
11. iPhone hardening for the Saathi PWA:
    - Manifest display standalone; apple-touch-icon (180 px) and full icon set; theme and status bar colours per skin; launch background colour.
    - viewport-fit=cover and safe-area padding on every screen and fixed element; dynamic viewport units instead of 100vh.
    - Minimum 16 px text in all inputs.
    - Audio unlock on the first user tap (resume a shared AudioContext); all later playback (voice replies, safety audio, toolkit) uses it; a visible play button as fallback.
    - AudioWorklet capture that resamples the device rate (often 48 kHz) to 16 kHz.
    - No Background Sync dependency: resync on app open, online event, visibilitychange, and a foreground retry loop; keep idempotency.
    - navigator.storage.persist() request after install; handle refusal gracefully.
    - Web Push per iOS rules: permission requested only from a button in the installed app; the service worker always shows a notification for every push; the subscription is re-checked and renewed on every app open.
    - Feature-detect vibration and Web Bluetooth; visual feedback and the simulated wearable when missing.
    - tel: and sms: links on the safety screen.
    - An install guide screen for iPhone (Share, Add to Home Screen) shown in Safari when not installed.
    - Playwright WebKit tests with an iPhone device profile for layout and offline behaviour.
12. Tunnel mode: `make tunnel` starts cloudflared for the web port; the web app proxies API and WebSocket traffic so one HTTPS origin serves everything; passkeys are disabled in tunnel mode with the PIN fallback shown; the tunnel URL is printed.
13. Apple Silicon: make sure every local image runs on ARM (multi-arch images or an explicit platform per service) and opensmile works in the engine container; document any service that runs under emulation.
14. Update docs/AUDIT.md.

Done when: providers-check passes locally for every configured class and service; live evals pass with routing and embedding decisions recorded; the Playwright WebKit iPhone profile passes the Saathi layout and offline tests; make tunnel works; latency p95 is reported.
```

### Prompt 10B: Azure deployment on the custom domain

```
Goal: the full system running on Azure in Central India on my custom domain, reproducible with azd.

Read: docs/02 sections 14.1, 18, 20, 21, 22, 23.4 to 23.6; docs/06_MANOBAL_WALKTHROUGH.md Phase 7 and Part A; docs/AUDIT.md.

Do:
1. Before changing anything, print the azd environment variables I must set and the exact commands; wait for me to run them if they are needed first.
2. azure.yaml: build all images remotely in Azure Container Registry for linux/amd64 (my machine is Apple Silicon).
3. Bicep: an app region parameter (centralindia) and a separate AI region parameter; reference my existing Foundry, Speech, Translator, Content Safety, and ACS resources by name instead of creating them.
4. Identities and roles: one managed identity per app; engine gets Cognitive Services OpenAI User on Foundry and user roles on Speech, Translator, and Content Safety; the vault identity alone gets wrap and unwrap on the KEK; the engine alone gets sign on the grant key; each gets only the secrets it needs; ACR pull; Blob data roles; Web PubSub roles. Add an automated check that each forbidden operation is refused.
5. Container Apps: web, engine, vault (internal ingress only), jobs (migrate, seed, snapshot, nightly scoring, purge, anchors). Minimum replicas 1 for web, engine, vault; session affinity for WebSocket traffic; health probes; enough CPU and memory for voice and scoring.
6. PostgreSQL Flexible Server x2 (General Purpose tier), PostgreSQL 16, extensions and shared_preload_libraries set by Bicep (keeping existing preload values), private networking or a tightly scoped firewall; migrations, seed, and snapshot as jobs; measure restore time.
7. Redis, Web PubSub, Blob Storage (immutability policy on the audit anchor container), Key Vault Premium, Application Insights and Log Analytics with alerts on errors, latency, and provider fallbacks.
8. Custom domain: output the exact DNS records needed; after I confirm binding, set the passkey relying party ID to the domain, update CSP and CORS, HSTS, and VAPID keys from Key Vault.
9. Front Door with WAF only if WebSocket traffic works through it in this configuration; otherwise route web and WebSocket directly to Container Apps and note it.
10. Architecture page and Trust Centre show the actual regions and deployment types.
11. Run make providers-check against production, then the Playwright demo spine twice on the domain with resilience mode off, then once with a provider forced down.
12. Write docs/DEPLOYMENT.md: every resource, region, SKU, URL, identity and role, job, and the exact warm-up, reset, scale-to-zero, and restart commands.
13. Update docs/AUDIT.md and docs/DEMO_RUNBOOK.md.

Done when: the custom domain serves the app over HTTPS, providers-check passes in production, the production E2E is green twice plus the outage run, and docs/DEPLOYMENT.md is complete.
```

---

## Quick reference: what Cursor needs, by phase

| Phase | Prompt | Facts you provide | Never provide |
|---|---|---|---|
| 1 | Rules additions | none | secrets |
| 2 | Prompt 9 plus env note | Screens you dislike | secrets |
| 5 | Prompt 10A | Regions, deployment names and types, voice names, providers-check table | secrets |
| 6 | Fix-ups | iPhone model, iOS version, what failed | secrets |
| 7 | Prompt 10B | Subscription ID, regions, existing resource names, domain, DNS host, azd errors | secrets |
| 8 | Short instruction | Secret names in Key Vault, roles | secret values |
| 9 | Fix-ups | Failed checklist items | secrets |
| 10 | Review export and apply | Corrected review files | secrets |
| 11 | Freeze instruction | none | secrets |
| 14 | Short instruction | assetlinks.json content | keystore or passwords |
