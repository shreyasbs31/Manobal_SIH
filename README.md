# MANOBAL

MANOBAL is a welfare support prototype for CAPF personnel: Saathi on the phone, officer consoles for welfare, medical, command, and governance, plus a Director desk for demos. The public line is **Support, not surveillance**. All seeded people and cases are synthetic.

The app you use is the Next.js web client on **port 3000**. The FastAPI engine on **port 8000** is the API. Do not treat `http://localhost:8000` as the product UI.

## What you need

- Docker Desktop running, with enough RAM for Postgres, Redis, the engine, and the web image (about 12 GB if you can spare it)
- Make, Git, and a browser (Chrome or Edge work well for microphone + Stage)
- Node 20 or newer and pnpm 12 only if you run host-side tests, not required for `make dev`
- Python 3.12 and `uv` only for host-side engine tests and evals
- Azure CLI (`az`) if you want live Foundry chat, Speech, and Translator. `make dev` refreshes a short-lived Foundry token into `infra/.cache/foundry.token`

Never paste API keys, tokens, or connection strings into chat logs or tickets.

## First-time setup

1. Clone this repository and open a terminal in the repo root.
2. Copy `infra/.env.example` to `infra/.env`. Fill provider endpoints and keys locally. Leave a value empty to use the labelled local fallback for that service.
3. Confirm Docker Desktop is running: `docker info`.
4. Sign in to Azure if you want live models: `az login`.
5. Create databases, run migrations, build images, and load synthetic data:

```bash
make reset
```

`make reset` wipes local Docker volumes, starts the stack, and seeds personas and cases. Use it on a fresh machine, or when the demo data is dirty.

Later starts, when volumes already exist:

```bash
make dev
```

`make dev` rebuilds images, waits for health checks, and publishes the web app on port 3000. The first build can take several minutes.

Optional live-provider check (prints pass or fail names only, no secrets):

```bash
make providers-check
```

## How to open the product

| What | URL |
| --- | --- |
| Landing | http://localhost:3000 |
| Sign in | http://localhost:3000/login |
| Saathi (personnel) | http://localhost:3000/app |
| Companion / Hold to talk | http://localhost:3000/app/saathi |
| Split demo stage | http://localhost:3000/stage |
| Demo director | http://localhost:3000/director |
| Engine health (API, not the UI) | http://localhost:8000/api/v1/system/health |
| Engine OpenAPI | http://localhost:8000/docs |

Wait until `docker compose -f infra/docker-compose.yml ps` shows `web` and `engine` as healthy before you sign in.

### Demo sign-in (no Entra, no passkey)

1. Open http://localhost:3000/login
2. Pick a role. For personnel also pick a persona (Arjun, Meena, Karthik, Deepak, and the others).
3. Click the demo continue button.

That call is `POST /api/v1/auth/demo-login`. The response includes a short-lived **access token** (JWT). The browser stores it in `sessionStorage` as `manobal.access_token`. Every `/api/v1/...` request sends `Authorization: Bearer <token>`. Voice uses the same token inside the WebSocket `start` message, not in the URL.

In Docker the token lasts **8 hours**. You should not paste it into Swagger unless you are debugging the API. You do not type it into the web app.

Production-shaped paths still exist on the login page: personnel passkey or PIN, officer Entra. The local demo mints the same scopes those roles would get.

### Roles and where they land

| Role | After login | What it can load |
| --- | --- | --- |
| Personnel | `/app` | Home, Saathi, check-in, toolkit, Me, safety |
| Welfare officer | `/welfare` | Queue and case workspace |
| Counsellor | `/counsel` | Counsellor desk |
| Medical officer | `/medical` | Acute board |
| Commander | `/command` | Unit posture, copilot, roster |
| Force HQ | `/hq` | HQ aggregates |
| Governance | `/governance` | Governance chain, plus `/lab` |
| DPO | `/dpo` | DPO centre |
| HRMS integrator | `/integrations` | Integration console |
| System admin | `/admin` | Admin |
| Demo director | `/director` | Clock, reset, warm-up, shot presets, airplane |

A personnel session cannot open Command. That is why a logged-in jawan who then opens `/command` (or used to open `/stage`) saw **The session does not have the required scope**. Sign in as Commander for `/command`, or use Stage (below), which mints a phone session and a console session separately.

## Stage (`/stage`)

http://localhost:3000/stage is the recording layout: Saathi in a phone frame, an officer console beside it.

You do **not** need to sign in first. Stage asks the engine for two demo sessions and sends each iframe its own token:

- Phone pane: personnel (default persona Arjun, or the shot/fixture persona)
- Console pane: the role that matches the console path (`/command` → commander, `/welfare` → welfare officer, `/medical` → medical officer, `/governance` or `/lab` → governance, and so on)

Those tokens must stay different. A jawan token cannot load Command, and a commander token cannot load Saathi. Sync is not a shared JWT. Both panes talk to the same engine world:

- Acute / T4, check-ins, clock jumps, reset, and reveal write to one in-memory demo store
- Each pane subscribes to the local realtime hub on port 8080 with **its own** ticket
- The engine publishes T4 to welfare, medical, and counsellor groups (not commander or HQ as named cases)
- Stage also forwards a same-origin refresh, and the console refetches every few seconds if a hub frame is missed

Useful URLs:

- Default: http://localhost:3000/stage
- Companion plus welfare queue: http://localhost:3000/stage?phone=/app/saathi&console=/welfare&shot=voice
- Command: http://localhost:3000/stage?phone=/app&console=/command&shot=formation
- Deepak safety plus medical: http://localhost:3000/stage?phone=/app/safety&console=/medical&shot=deepak

Press **D** (not in a text field) to toggle the hidden Director drawer. Allow the microphone if you use Hold to talk inside the phone frame.

## Saathi voice

On http://localhost:3000/app/saathi after a personnel sign-in:

1. Allow the microphone when the browser asks.
2. **Hold to talk**: press and hold while you speak, then release. Short taps and silence are rejected on purpose.
3. **Keyboard**: type a message and Send. The spoken reply plays in full, sentence by sentence, without cutting the previous clip.
4. **Play recorded check-in** appears only when the URL has `?fixture=...` (Director shots). It is not a second copy of Hold to talk.

The voice WebSocket is `ws://localhost:8000/api/v1/voice/session`. HTTP still goes through the web app (`/api/v1/...` on port 3000), which proxies to the engine.

If Foundry, Speech, or Deepgram are unset, captions and TTS fall back to labelled local scripts. The hosting caption on the page stays honest about that.

## Director

http://localhost:3000/director (Demo director role):

- **Reset snapshot**: restore the synthetic world between takes (prefer this over `make reset` during a recording day)
- **Warm-up**: ping live model classes so the first on-camera turn is not a cold start
- Clock jump, airplane mode, drain the offline queue, shot presets

Recording order and click-by-click beats: `docs/DEMO_RUNBOOK.md`.

## Ports (local Docker)

| Port | Service |
| --- | --- |
| 3000 | Web app (use this) |
| 8000 | Engine API and voice WebSocket |
| 8080 | Local realtime hub |
| 8100 | Identity vault API |
| 10000 | Azurite blob (audit anchors) |

## Common problems

**The session does not have the required scope**  
The current access token is the wrong role for that screen. Sign in as the matching role, or open the screen inside `/stage` so each pane gets its own session. Refresh after a role change.

**localhost:8000 looks broken**  
That host is the API. Open http://localhost:3000 instead. `GET http://localhost:8000/` returns a short JSON pointer, not the product.

**Voice connects, then TTS stops mid-reply**  
Hard-refresh once after a web rebuild so the service worker (`manobal-saathi-v11`) drops stale Saathi HTML. Hold the button for the whole utterance. If Foundry chat is cold, wait for the first sentence; later sentences should keep playing.

**Microphone blocked**  
Allow mic for `http://localhost:3000`. Stage needs the phone iframe permission as well. Safari often needs a prior tap to unlock audio.

**Chat or TTS is empty / falls back**  
Run `az login`, then `make foundry-token` (also part of `make dev`). Confirm `make providers-check`. Empty values in `infra/.env` mean that provider is not live.

**401 after leaving the laptop overnight**  
Demo tokens expire. Sign in again from `/login`. Docker tokens last 8 hours.

**Stale UI after `make dev`**  
The web image is built at compose time. Restart with `make dev` after app code changes, then hard-refresh the browser.

## Commands worth knowing

```bash
make dev                 # start or rebuild the stack on :3000
make logs                # follow container logs
make down                # stop containers, keep volumes
make reset               # wipe volumes, start, seed
make seed                # reload synthetic data (stack must be up)
make providers-check     # live provider probe, names only
make test                # unit tests, typecheck, evals
make e2e                 # Playwright (stack must be up)
```

## Deeper docs

| File | Use |
| --- | --- |
| `docs/DEMO_RUNBOOK.md` | Eight-minute recording script |
| `docs/06_MANOBAL_WALKTHROUGH.md` | Mac, iPhone, Azure go-live |
| `docs/05_GO_LIVE_AND_VERIFY.md` | Provider and deploy checks |
| `docs/02_MANOBAL_MVP_BUILD_SPEC.md` | Product spec |
| `infra/.env.example` | Provider settings template (no secrets in git) |
