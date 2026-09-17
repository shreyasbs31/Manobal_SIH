# Demo runbook

Eight minutes. One operator. Reset from Director before every take. All data is synthetic.

## Before recording

1. `make dev` so web is on port 3000 and the engine is up.
2. Sign in as Demo director. Open `/director`.
3. Click Reset snapshot. Wait until the status says it finished (under 20 s).
4. Click Warm-up. If Foundry is unset, the status still returns; captions stay honest.
5. Hide the Director drawer on `/stage` (press D only if you need it). Top bar stays 44 px.

Fallbacks (spec 31.1): if a live provider is down, circuit breakers open after three failures and the signed local scripts plus resilience cache take over. ACS identities can still fail; the labelled demo join remains. Azure URL unset means this local stack is the recording environment. Web PubSub and Key Vault are local until azd creates those resources.

## Azure warm-up

1. `az login` so Entra can reach Foundry. On this Mac the engine container reads a short-lived token from `infra/.cache/foundry.token` (`make foundry-token`, also run by `make dev`). Refresh it if chat starts failing after about an hour.
2. `make providers-check` must print 11 pass before a take. Names only, no secrets.
3. Director Warm-up. Wait until main, fast, and open report ok, or until fallback is labelled.
4. Play one Hindi TTS clip and one English Deepgram turn so the first on-camera turn is not a cold start.

## Azure quota check

1. In Foundry (eastus2, resource manobal-ai-resource, project manobal-ai) confirm TPM on main (gpt-5.6-sol, priority), fast (gpt-5-mini), open (gpt-5.6-terra), and embed (text-embedding-3-large).
2. If a class starts returning 429, turn Director resilience on. Scripted beats then use `infra/evals/fixtures/resilience.json`.
3. Alt (grok-4.6) is officer-side text only. Never warm it on Saathi, crisis, or safety.

## Azure reset

Director Reset snapshot is still the 20-second path. Do not `make reset` during a recording day unless the database is dirty. After azd exists, run seed and snapshot on Azure once, then use the same Director reset. Restore time is unmeasured on Azure (31.1, no azd env in this environment).

## Azure fallback switches

| Switch | When | What the audience should hear |
|---|---|---|
| Resilience mode on | Quota, timeout, or a forced-down provider | Cached companion lines for scripted beats. Caption still says Azure-hosted prototype. |
| Circuit open | Three live failures in 60 s | Local signed scripts. Architecture mode still shows the provider as configured if the env is set. |
| ACS down | Calling 401 or timeout | Labelled demo join. Booking still works. |
| Speech or Deepgram down | Empty audio | Silent reviewed WAV plus captions. |
| Web PubSub unset | Local demo | Local realtime hub (31.1). T4 alerts still move on the local hub. |
| Key Vault unset | Local demo | Local wrap file (31.1). Vault identity split waits on azd. |

## Timing and clicks

| Time | Beat | Clicks |
|---|---|---|
| 0:00 | Landing | Open `/`. Wait for the ribbon. Say Support, not surveillance. Point at sourced numbers. |
| 0:30 | Hindi onboarding | `/stage?phone=/app/onboarding&console=/welfare&shot=onboarding`. Language Hindi. Accept the one exception. Finish the receipt. |
| 1:20 | Check-in then voice | `/stage?phone=/app/check-in&console=/welfare&shot=checkin`. Face scale, save. Then `/stage?phone=/app/saathi&console=/welfare&shot=voice`. Captions. Audio-cleared chip. |
| 2:10 | Arjun time travel | Director: +1 week, Run nightly scoring now. Phone `/app`, console `/welfare`. Case MB-4091 is under High. |
| 3:10 | Reveal and ledger | `/stage?phone=/app/me&console=/welfare/cases/MB-4091&shot=workspace`. Purpose care contact. Justify. Reveal. Phone ledger updates. |
| 4:00 | Imran and Thomas | Console `/lab`. Read the two sentences. Do not open Command. |
| 4:25 | Command | `/stage?phone=/app&console=/command&shot=formation`. Post D-7 is hatched. Open Copilot. Ask Charlie Coy mein kaun pareshan hai? Then roster. |
| 5:15 | Deepak T4 | `/stage?phone=/app/safety&console=/medical&shot=deepak`. Audio, call buttons, acknowledge. |
| 6:05 | Governance | `/stage?phone=/app&console=/governance&shot=governance`. Verify, Tamper, Restore. Acute stays Always on. |
| 6:50 | Lab | Console `/lab`. Shifted world. Read the synthetic-data note. |
| 7:20 | Offline and architecture | Airplane on. Check-in, toolkit, SMS. Airplane off. Director Drain queue. Console `/architecture`. Zones, self-test, mode. |
| 7:45 | Close | `/#ps-map`. |

Backup if time allows: Karthik Tamil voice, Rajesh on Welfare, Lalit talk request, Meena leave planner. Presets are on Director.

## Reset between takes

Director Reset snapshot. Do not use `make reset` during a recording day unless the database is dirty. In-memory reset is the 20-second path.

## Q&A from spec 26 (screen for each answer)

| Question | Screen | What to show |
|---|---|---|
| How do you avoid false alarms? | Governance and Lab | K3, corroboration copy, ablation rows |
| What if a commander wants names? | Command | Hidden Post D-7, Copilot refusal, Architecture self-test |
| What stops a welfare officer from snooping? | Case workspace and Me | Purpose, contact note, ledger row |
| What if someone opts out? | Lab | Zero-penalty excluded attributes |
| Is this AI or rules? | Lab and Welfare | Forecast never places T3 or T4. Humans pick levers. |
| Does it work without network? | Stage phone plus Architecture | Airplane check-in, toolkit, SMS, edge queue |
| Which AI models? | Architecture mode panel and Trust | Hosting caption. Alt never serves personnel. |
| Why would a jawan use it? | Home, rest, talk, safety | Leave planner, counsellor request, safety plan, buddy |
| Which laws? | DPO Centre and Trust | Notices, erasure due dates, rights table. Verify clauses before quoting. |

## Limitations to say before a judge asks (26.1)

State these on Lab or Trust, not on Command: synthetic data; shifted world does not prove a field trial; voice weight is low and opt-in; prototype models are Azure-hosted and designed to move on-prem; HQ levers are observational; crisis content needs clinician review before real use.
