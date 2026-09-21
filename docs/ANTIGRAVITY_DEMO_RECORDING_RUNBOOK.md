# MANOBAL demo: single-take autonomous recording contract

Version: 4.0
Operator: Antigravity, or any agent with browser control and a terminal
Mode: **one continuous 240.000 second take, no cuts, no clips**
Application: `http://localhost:3000`
Engine health: `http://localhost:8000/api/v1/system/health`
Aligned to: `MANOBAL_SIH_Presentation.pdf` (SIH26186)

This is the complete execution contract. Read all of it before touching anything. Ignore `docs/DEMO_RUNBOOK.md`, `docs/SHOT_LIST.md`, and any earlier version of this file, all of which describe a multi-clip workflow that no longer applies.

All people, cases, units, dates and events shown are synthetic.

---

# PART 0 · WHAT YOU ARE DOING

You will produce one file: a four minute, 1920x1080, constant frame rate H.264 MP4 of the MANOBAL product being explored continuously, with narration and burned-in captions.

You do all of it. You start the screen recorder, you drive the browser, you stop the recorder, you generate the narration, you mux, you burn captions, you verify, you report.

There are **no clips**. There is no cutting. The video is one unbroken screen capture from t=0.000 to t=240.000. The only post-processing permitted is a single filter-and-mux pass that adds audio, captions and labels to that one file. No trimming of the interior. No joins. No transitions.

## 0.1 The three hard constraints of a single take

1. **Timing is absolute, not relative.** You record a monotonic clock reading at capture start and every action fires at `t0 + mark`. Never use relative sleeps between actions; error accumulates and you will be many seconds adrift by the three minute point.
2. **There are no retries inside a take.** A failure at t=220 costs the entire four minutes. Expect to attempt this several times. That is normal and expected, and it is why Part 3's dry run exists.
3. **You cannot go backstage.** No Director resets, no airplane toggles, no scenario buttons, no snapshot restores once capture begins. The world state you start with is the world state you finish with.

## 0.2 Anti-fabrication clause

Never describe an action as performed, an assertion as passed, or a file as produced unless it actually was. If the take failed, say so and say where. A truthful failure report is a successful outcome for you. A plausible completion summary for work you did not do is the worst possible outcome of this task, and it is worse than delivering nothing.

Never simulate, mock, stage or inject any UI state to make a narration line appear true. If a screen does not show what this document expects, that is a stop condition and a report, never a prompt to improvise.

---

# PART 1 · TRUTH AND SAFETY RULES

These override everything else in this file.

- Keep the application's `Demo` and `Synthetic data` labels visible at all times. Never crop or cover them.
- Never imply the system is deployed, piloted or field-tested.
- Never imply synthetic validation is field evidence.
- Never state that Command sees names, personal check-ins, journal content, assessment answers, case IDs or identity tokens.
- Never state that a forecast opens a high or acute case by itself.
- Never state that the system makes a care decision. Humans decide and record.
- Never state that a generated companion response is used on the acute path.
- Never claim the console unit picker proves server-side access control. It is a visual selection.
- Never show a secret, access token, connection string, `.env` file, private key or terminal window in frame.
- Do not open, print or inspect `infra/.env`, `infra/secrets.env`, or anything under `infra/keys/`.
- Never use real personnel details, service numbers, unit numbers, crests, emblems, flags, or political or religious symbols.
- Never deviate from the narration in Part 7. Not a word.
- Never substitute a different or more graphic phrase for the acute test phrase, under any circumstance.

## 1.1 Two hard product-failure stops

If either of these occurs, abandon the take, do not retry, and report it as a product defect:

- **A numeric personal stress score or rank renders anywhere in the console.** The narration and the SIH deck both state there is none.
- **The Copilot answer contains a personal name, case ID, identity token or contact detail.** The narration states it refuses to identify anyone.

Recording around either would make the video assert something false.

---

# PART 2 · PREFLIGHT

## 2.1 Human steps. You verify these, you do not execute them.

A person runs these and tells you they are done. **Do not run `make dev`, `az login` or `make foundry-token` yourself.** Interactive Azure authentication will stall you indefinitely.

```bash
cd "/Volumes/Shreyas Projects/SIH_Manobal_Final"
make dev
make providers-check
```

A person must also have granted screen-recording permission to your terminal application in System Settings, Privacy and Security, Screen Recording. Without it, `ffmpeg` captures a black frame silently and you will record four minutes of nothing.

## 2.2 Your verification

```bash
curl -sS http://localhost:8000/api/v1/system/health
```

Must return exactly:

```json
{"status":"ok","service":"engine"}
```

Then confirm:

- Web responds on port 3000.
- Provider check reported `11 pass, 0 fail`.
- Every required service healthy: web (3000), engine (8000), identity vault (8100), realtime hub (8080), core database, vault database, Redis, local blob storage.

**Stop condition.** Any unhealthy service, or providers not at 11 pass 0 fail. Do not record against a degraded build. Do not attempt repairs.

## 2.3 Capture device discovery

```bash
ffmpeg -f avfoundation -list_devices true -i "" 2>&1 | grep -A20 "video devices"
```

Record the index of the display you will capture. On most Macs this is `1`, `2` or `3`. Note it as `DISPLAY_IDX`.

Determine the physical pixel geometry of the browser viewport. On a Retina display a 1920x1080 CSS viewport occupies 3840x2160 physical pixels. Capture native and downscale, which yields noticeably sharper text than capturing at 1080 directly.

Find the viewport's physical offset from the top-left of the display:

```bash
# take a reference still and inspect it
ffmpeg -f avfoundation -framerate 30 -i "DISPLAY_IDX:none" -frames:v 1 -y /tmp/geom.png
```

View `/tmp/geom.png`, measure the browser content area, and record `CROP_W`, `CROP_H`, `CROP_X`, `CROP_Y` in physical pixels. `CROP_W:CROP_H` must be exactly 16:9.

## 2.4 Branch determination

Determine and record each of these before the dry run.

| Branch | Question | Effect |
|---|---|---|
| **B1 acute causality** | Does typing the acute phrase actually create the acute case, or is case `MB-6604` pre-seeded in the reset world? | Decides which S7 narration variant is used and whether the seeded-case notice is burned in. |
| **B2 Medical Acknowledge** | Does the Medical page's detailed status update correctly when Acknowledge is clicked? (API stores `acknowledged`, page historically checked for `ack`.) | If unfixed, the Acknowledge control is shown but never clicked. This take does not click it either way. |
| **B3 Validation Lab disclaimer** | Does a synthetic-validation disclaimer render anywhere on `/lab`? | If nothing renders, **stop and report**. Do not record a metrics screen with no disclaimer. |
| **B4 seven domains** | Does the console render the seven ingestion domains by name anywhere? | If not, the `DESIGN TARGET` label covers the S3 domain list. |
| **B5 oversight body** | Is the Welfare Data Ethics Cell or equivalent named on any governance screen? | If not, the `DESIGN TARGET` label covers the S8 oversight line. |

## 2.5 Deck alignment check

The video and the SIH deck must show one synthetic world. Record observed values. Mismatches are not stop conditions but every one goes in your report.

| Item | Deck value | Observed |
|---|---|---|
| Welfare case ID | `MB-4091` | |
| Case tier | Tier 3, High Fatigue | |
| Contributing domains string | `Roster Overtime + Sleep Loss` | |
| Recommended action string | `Sanction 48-Hour Rest Cycle` | |
| Alpha Coy posture | 92% normal | |
| Charlie Coy posture | 32% high fatigue | |
| Small-group suppression threshold | under 10 | |
| Acute SLA | 15 minutes | |

---

# PART 3 · THE DRY RUN. DO NOT SKIP THIS.

A single take has no retries, so every selector, every label and every render latency must be known before the first frame is captured. Run the entire Part 6 sequence at least twice with no recorder running.

## 3.1 What the dry run must produce

**A selector map.** For every action in Part 6, the resolved element reference and its visible text. The console navigation rail labels in particular are marked **[VERIFY]** throughout this document because they have not been confirmed. Map them now:

| Part 6 refers to | Actual rail label | Element ref |
|---|---|---|
| Command | | |
| Acute board | | |
| Governance | | |
| Validation Lab | | |
| Architecture | | |

And the phone bottom navigation:

| Part 6 refers to | Actual label | Element ref |
|---|---|---|
| Me | | |
| Saathi | | |

**A latency table.** Measure, three times each, and record the worst case:

| Transition | Worst observed |
|---|---|
| Stage initial load, both frames rendered | |
| Console queue to case workspace | |
| Console rail to Command | |
| Copilot preset to answer rendered | |
| Phone nav to Me | |
| Phone nav to Saathi | |
| Acute send to `/app/safety` | |
| Console rail to Medical | |
| Console rail to Governance | |
| Tamper click to tampered state | |
| Restore click to intact state | |
| Console rail to Lab | |
| Console rail to Architecture | |
| Self-test click to results | |

**A scroll map.** Several segments require scrolling a frame to bring a proof point into view. For each, record the exact scroll amount in wheel ticks that puts the target element fully in frame without overshooting. Overshoot is highly visible and unrecoverable in a single take.

## 3.2 The Copilot latency gate

Part 6 gives the Copilot answer a fixed nine second budget, from t=113 to t=122. This is the single most likely cause of a failed take.

Measure it five times in the dry run. If the worst case exceeds eight seconds, **stop and report before attempting a take**. A person must warm the providers and re-measure. Do not attempt a take you already know will probably fail on a fixed timeline.

## 3.3 Persona continuity

This take never changes persona. Whichever personnel session Stage mints at t=20 is the person for the whole four minutes: they complete the check-in, they view their own access ledger, and they type the acute phrase.

**[VERIFY during dry run]** that the minted persona can do all three, and that their seeded language renders on the phone throughout. The earlier multi-clip runbook used Deepak (Hinglish) specifically for the acute path. If the Stage URL in Part 5 mints a different persona and the acute path does not fire for them, report it before recording; the fixture parameter needs changing, and that is a person's decision, not yours.

## 3.4 Dry run exit criteria

Do not proceed to Part 4 until:

- Two consecutive dry runs completed the full Part 6 sequence with every assertion passing.
- Every **[VERIFY]** item in this document is resolved and written down.
- Every latency has a worst case, and the Copilot worst case is at or under eight seconds.
- Every scroll amount is known.
- Branches B1 to B5 are determined.
- The deck alignment table is filled in.

Report all of this before you record anything.

---

# PART 4 · ENVIRONMENT SETUP

## 4.1 Browser

- Current Chrome, clean profile dedicated to this demo.
- Viewport exactly 1920 x 1080 CSS pixels. Zoom exactly 100 percent.
- Bookmarks bar hidden. Downloads bar hidden. DevTools closed and never opened.
- Notifications, password-manager popups and translation prompts disabled.
- Browser find never used.
- Console theme **Parchment**. Console language **English**. Never changed on camera.
- Phone language stays as seeded. This is a proof point, not a defect.

## 4.2 Desktop

- Do Not Disturb on.
- No dock, menu bar, terminal, editor, chat application or notification banner anywhere in the crop region.
- Nothing in frame that is not the application.

## 4.3 Starting state

Before capture, a person performs the backstage sequence once. You verify it, you do not repeat it during the take.

1. `http://localhost:3000/login?role=director`, choose `Demo director`, `Continue`.
2. Click `Reset snapshot`, wait for completion.
3. Confirm the airplane control reads `Airplane off`.
4. Confirm `Resilience Off`.
5. Click `Speech restored`.
6. Click `Warm-up`, wait for completion.
7. Close the Director tab entirely. It must not exist during the take.

Then open one tab, and only one, at `http://localhost:3000/`. Let it fully load. Confirm no popup, no menu, and that the ribbon animation has not yet played. If it has played, hard refresh and wait.

## 4.4 Pointer policy

Your clicks are dispatched events and may not move the host operating system cursor. The capture may therefore show clicks landing with no visible pointer.

**This is acceptable and preferable.** Do not attempt to simulate smooth human cursor motion, do not perform decorative sweeps or hovers, and do not use hover states as emphasis. Emphasis in this video comes from stillness and from the narration, not from a pointer.

---

# PART 5 · THE MASTER TIMELINE

240.000 seconds. Eleven segments. One page load at t=20. Everything after that is navigation inside the Stage frames.

| Mark | End | Dur | Segment | Screen | Reached by |
|---|---|---|---|---|---|
| 0 | 20 | 20 | S1 The problem | Public landing | initial load |
| 20 | 23 | 3 | Transition | Stage loading | navigate, the only page load |
| 23 | 45 | 22 | S2 Twenty seconds | phone check-in, console queue | Stage opens here |
| 45 | 74 | 29 | S3 The signal | console case `MB-4091` | click the case card |
| 74 | 102 | 28 | S4 Purpose-bound reveal | phone `Me`, console reveal | phone bottom nav |
| 102 | 126 | 24 | S5 Rule of 10 | console Command | console rail |
| 126 | 150 | 24 | S6 Acute to Safety | phone Saathi then Safety | phone bottom nav |
| 150 | 165 | 15 | S7 Fifteen minutes | console Medical | console rail |
| 165 | 185 | 20 | S8 Adversarial oversight | console Governance | console rail |
| 185 | 207 | 22 | S9 What it refuses to do | console Validation Lab | console rail |
| 207 | 240 | 33 | S10 Four zones, and close | console Architecture | console rail |

The single Stage URL, opened once at t=20:

```
http://localhost:3000/stage?phone=/app/check-in&console=/welfare&shot=checkin
```

## 5.1 What a single take costs you, and what it buys

**Lost:** the offline save beat. It requires a backstage airplane toggle and you cannot go backstage mid-take. The thirty-day buffer therefore becomes a spoken design claim with no on-screen evidence, carried by the `DESIGN TARGET` label. Also lost: the landing role-map ending, which is replaced by a close on the zone diagram, bookending the opening promise.

**Bought:** the video is verifiably one continuous session of a real running product. For a judging panel that is worth considerably more than the two beats you gave up, because it is not something a mock-up can fake.

---

# PART 6 · THE SEQUENCE

## 6.0 How to execute this

Immediately after starting capture, take a monotonic clock reading and call it `t0`. Every action below fires at absolute time `t0 + mark`. Before each action, sleep until that absolute time, recomputing the remaining interval from the current clock reading each time. Never chain relative sleeps.

Reference implementation:

```python
import time, datetime
t0 = time.monotonic()

def at(mark):
    """Block until t0+mark seconds. Never sleep relative to the previous action."""
    while True:
        remaining = (t0 + mark) - time.monotonic()
        if remaining <= 0:
            drift = -remaining
            if drift > 0.35:
                log(f"DRIFT {drift:.3f}s at mark {mark}")
            return
        time.sleep(min(remaining, 0.02))
```

Assertions are read from the DOM, never inferred from a screenshot. Log every assertion with its absolute timestamp and result. **Assertions never block the timeline.** If an assertion fails, log it and continue to the next scheduled action; you evaluate the take as a whole afterwards. Stopping mid-take to investigate guarantees a ruined recording, and the log tells you afterwards whether the take is usable.

The two hard product-failure stops in section 1.1 are the exception. Those abort the take immediately.

---

## S1 · The problem · t=0 to t=20

Screen: `http://localhost:3000/`, already loaded, ribbon not yet animated.

| t | Action | Assert |
|---|---|---|
| 0.0 | None. The page is already loaded and still. | Headline rendered. `Support, not surveillance` present in DOM. |
| 2.0 | None. Let the baseline ribbon animate. | Ribbon element present. Synthetic-data label present. **[VERIFY exact label text]** |
| 8.0 | One slow scroll down to the sourced public context block. Use the dry-run scroll amount. | The MHA-sourced figures block is rendered. **[VERIFY the landing page carries the 730 and 55,555 figures and a visible source line. The narration opens on them. If it does not carry them, report before recording; a person must decide whether to add them or change the opening.]** |
| 14.0 | One slow scroll back up to the promise. | `Support, not surveillance` in view. |
| 17.0 | None. Absolute stillness. | Role doors for Personnel, Welfare, Command and Ethics all present. |
| 20.0 | Navigate to the Stage URL in Part 5. | Navigation initiated. |

The ribbon is one person's pattern over time, their usual range as a band, and a marker when the line leaves the band. It is never a score and never a peer rank.

---

## Transition · t=20 to t=23

Three seconds of Stage loading, on camera, in silence. This is the only page load in the video and it is deliberate; it reads as entering the product.

| t | Action | Assert |
|---|---|---|
| 22.5 | None. | Both phone and console frames rendered. `Preparing` absent. `The session does not have the required scope` absent. Director drawer hidden. |

If the drawer is visible at 22.5, press `D` once with focus outside any input. If it is still visible, the take is ruined; abandon and restart.

---

## S2 · Twenty seconds · t=23 to t=45

Phone: `/app/check-in`, question 1 of 3. Console: `/welfare` queue.

| t | Action | Assert |
|---|---|---|
| 23.0 | None. Hold the full split. | Queue shows T4, T3 and T2 groupings with due-time labels. |
| 25.0 | Phone: click the centre face, mood. | Advances to energy. |
| 27.0 | Phone: click the centre face, energy. | Advances to sleep quality. |
| 29.0 | Phone: click the centre face, sleep quality. | Advances to tags. |
| 31.0 | Phone: select tag `Duty`. | Selected state. |
| 32.5 | Phone: select tag `Family`. | Selected state. |
| 34.0 | Phone: click `Continue`. | Sleep-hours control visible. |
| 36.0 | None. Leave sleep hours at 6. Do not adjust. | Value reads 6. |
| 37.0 | Phone: click `Save`. | Saved state within 2s. **[VERIFY exact string]** Updated personal ribbon renders. |
| 40.0 | None. Hold on the saved ribbon. | New point visible on the ribbon. |
| 44.0 | None. Console frame must be still and legible. | **No numeric personal score anywhere in the console frame.** |

**Retry rule, the only one permitted inside a take:** if the phone does not advance within 300 ms of a face selection, click the same centre face exactly once more. Never double-click. Never click a different face.

---

## S3 · The signal · t=45 to t=74

Console navigates from the queue to the case workspace. This is the segment that answers "where is the AI" and it did not exist in earlier versions of this runbook.

| t | Action | Assert |
|---|---|---|
| 45.0 | Console: click the `MB-4091` case card in the queue. | Navigation initiated. |
| 47.5 | None. | Case workspace rendered. Case shows Tier 3 / High Fatigue. **[VERIFY against deck]** |
| 50.0 | None. Hold on `What changed`. | Section rendered. |
| 57.0 | Console: one small scroll to bring contributing domains fully into view. | Contributing-domain string rendered. Deck expects `Roster Overtime + Sleep Loss`. **[VERIFY and log exactly what renders.]** |
| 62.0 | Console: one small scroll to ranked support options. | Recommended action rendered. Deck expects `Sanction 48-Hour Rest Cycle`. **[VERIFY]** |
| 68.0 | Console: one small scroll to the case brief and identity area. | Checked case brief and conversation openers rendered. Identity area shows `Locked`. **[VERIFY exact string]** |
| 72.0 | None. Absolute stillness. | **Scan the entire console frame: no numeric stress score and no rank anywhere. This is a hard product-failure stop.** |

Do not click any support action here. S3 shows the signal; S4 shows the human decision.

The scroll positions matter: at t=74 the identity area must be in view, because S4 begins by typing into the justification field.

---

## S4 · Purpose-bound reveal and person-visible ledger · t=74 to t=102

The strongest sequence in the video. Improvise nothing.

| t | Action | Assert |
|---|---|---|
| 74.0 | Phone: tap `Me` in the bottom navigation. | Navigation initiated. |
| 77.0 | None. | `Me` screen rendered. |
| 79.0 | Phone: scroll to the `Who viewed my information` section. | Section in view. **No new access row yet.** |
| 82.0 | None. Console: confirm Purpose reads `Care contact`. Do not change it. | Field reads `Care contact`. |
| 84.0 | Console: click into `Why you need to reach them`. | Field focused. |
| 85.0 | Console: type exactly `Care contact after sustained sleep and workload drift.` Type at a natural rate, roughly 4 seconds. | Field contains the exact string. No typos. No autocorrect artifacts. |
| 90.0 | Console: click `Reveal to contact`. | Request in flight. |
| 92.5 | None. | Synthetic contact card rendered. Contact-note due time visible. |
| 96.0 | None. Hold, both frames in view. | **A new access-ledger row is present on the phone**, in the seeded language, showing role and purpose. |
| 100.0 | None. Absolute stillness. | Row still present. |

**If the ledger row has not appeared by t=96, the take is ruined.** The causal link between the console action and the phone ledger is the entire point of this segment and the narration asserts it. Log it, complete the take for practice if you wish, but mark the take as failed and restart.

---

## S5 · Rule of 10 and the Copilot refusal · t=102 to t=126

| t | Action | Assert |
|---|---|---|
| 102.0 | Console: click `Command` in the navigation rail. **[VERIFY rail label]** | Navigation initiated. |
| 105.0 | None. | Unit posture rendered. KPI strip shows duty hours, rest denials, night load, leave backlog. |
| 108.0 | None. Hold on the 12-week formation grid. | Alpha Coy and Charlie Coy postures rendered. Deck expects 92% and 32%. **[VERIFY and log both]** |
| 111.0 | None. Hold on the suppressed row. | `Post D-7` fully hatched. **[VERIFY whether the UI states the suppression threshold and whether it is 10. The narration says "any group under ten".]** |
| 113.0 | Console: click `Ask copilot`. | Panel opens. |
| 115.0 | Console: click the preset `Who is under strain?`. | Request in flight. |
| 115 to 124 | None. Nine second budget. Do not act. | Answer renders by 124.0. |
| 124.0 | None. | Answer contains a refusal to identify individuals, and aggregate context only. |
| 125.0 | None. Absolute stillness. | **Hard product-failure stop: if the answer contains any personal name, case ID, token or contact detail, abort the take immediately and report a product defect. Do not retry.** |

Never substitute your own question. The preset is the tested prompt and the narration describes its behaviour.

If no answer has rendered by t=124, the take has failed. Continue the sequence to completion for timing practice, mark the take failed, and report the observed latency. A person then warms the providers before the next attempt.

---

## S6 · Five gates, then a human · t=126 to t=150

| t | Action | Assert |
|---|---|---|
| 126.0 | Phone: tap `Saathi` in the bottom navigation. | Navigation initiated. |
| 129.0 | None. | Saathi screen rendered in the persona's seeded language. |
| 130.0 | Phone: click `Keyboard`, or the localised equivalent such as `कीबोर्ड`. | Text input focused. |
| 132.0 | Phone: type exactly `main jeena nahi chahta`. Roughly 2 seconds. | Input contains exactly that string, character for character. |
| 135.0 | Phone: click `Send`. | Request in flight. |
| 137.0 | None. | Phone route is `/app/safety`. Fixed Safety screen rendered. **No generated companion reply appeared at any point.** |
| 139.0 | None. Hold on the Safety screen. | Tele-MANAS `14416` visible. |
| 143.0 | Phone: one small scroll to bring the remaining safety actions into view. | Welfare callback, SMS or SOS, and safety-plan controls all present. |
| 147.0 | None. Absolute stillness. | All safety actions in frame. |

**Never substitute a different or more graphic phrase.** If the Safety screen does not open by t=137, the take has failed. Verify the exact phrase was typed, report, and a person decides whether to attempt another take.

---

## S7 · Fifteen minutes · t=150 to t=165

| t | Action | Assert |
|---|---|---|
| 150.0 | Console: click `Acute board` in the navigation rail. **[VERIFY rail label]** | Navigation initiated. |
| 153.0 | None. | Medical board rendered. 15-minute response clock visible and running. Current human owner shown. |
| 156.0 | None. Hold on the context panel. | Minimum necessary context shown. `No journal or assessment answers are shown here` present. **[VERIFY exact string]** |
| 160.0 | None. Hold on the protocol panel. | Immediate human protocol and "who has been asked" rendered. |
| 163.0 | None. Absolute stillness. | Acknowledge control in frame. |

**Do not click `Acknowledge`**, on either branch B2. In a single take there is no opportunity to verify the resulting state before the timeline moves on, so the control is shown and never operated.

**Branch B1.** If the acute case is pre-seeded rather than created by the phrase in S6, the S7 narration uses the seeded variant in Part 7 and the burned-in notice in Part 9.2 becomes mandatory. State which applies in your report.

---

## S8 · Adversarial oversight · t=165 to t=185

| t | Action | Assert |
|---|---|---|
| 165.0 | Console: click `Governance` in the navigation rail. **[VERIFY rail label]** | Navigation initiated. |
| 168.0 | None. | Assurance snapshot and fairness band rendered. `Audit chain intact` present. |
| 171.0 | Console: click `Tamper`. | Request in flight. |
| 173.0 | None. | `Audit chain tampered` present, and the break sequence is identified. **[VERIFY whether the sequence number is deterministic. The narration says "names its sequence" and never states a number, so variation is safe. Log the observed value.]** |
| 176.0 | Console: click `Restore`. | Request in flight. |
| 178.0 | None. | `Audit chain intact` has returned. |
| 181.0 | Console: one small scroll to the capability controls. | Optional capabilities listed. `Acute path` shows `Always on`. |
| 184.0 | None. Absolute stillness. | `Always on` in frame. |

**Do not toggle any optional capability.** Showing that they can be paused is the point; pausing one leaves state you cannot reset mid-take.

If governance loads already tampered at t=168, the starting world was wrong. Abandon the take and have a person reset before the next attempt.

---

## S9 · What it refuses to do · t=185 to t=207

The most important twenty-two seconds in the video. It is where the deck's rejection of suicide-risk scoring and its K1, K3 and K12 KPIs become visible.

| t | Action | Assert |
|---|---|---|
| 185.0 | Console: click `Validation Lab` in the navigation rail. **[VERIFY rail label]** | Navigation initiated. |
| 188.0 | None. | Metrics panel rendered. Precision, recall, F1 and calibration error present for the primary world. |
| 191.0 | None. Hold on the primary versus shifted comparison. | Shifted-world metrics rendered alongside primary. |
| 195.0 | Console: one small scroll to the lead-time panel. | Lead time rendered with its unit visible. |
| 199.0 | Console: one small scroll to excluded attributes. | Excluded-attributes list rendered. |
| 203.0 | None. | A synthetic-validation disclaimer is visible somewhere on screen. |
| 205.0 | None. Absolute stillness. | Disclaimer in frame. |

**Do not run the 80,000-subject benchmark.** Its runtime is unpredictable and it would destroy the timeline.

**Branch B3.** If no disclaimer renders anywhere on `/lab`, do not record. Stop and report. This is the one screen where a missing disclaimer does real damage, because the narration explicitly says synthetic validation is not field evidence.

Log every observed number here. The narration names no figure precisely so that the screen carries all of them, and no spoken or burned-in number may ever differ from what is on screen.

---

## S10 · Four zones, and close · t=207 to t=240

| t | Action | Assert |
|---|---|---|
| 207.0 | Console: click `Architecture` in the navigation rail. **[VERIFY rail label]** | Navigation initiated. |
| 210.0 | None. | Zone 0 Phone, Zone 1 Unit, Zone 2 Patterns and Zone 3 Names all rendered. |
| 213.0 | None. Hold on the zone diagram. | All four zones in frame. |
| 216.0 | Console: click `Zone X`. | Blocked state renders. `Appraisal, promotion, posting, and discipline have no path in` present. **[VERIFY exact string]** |
| 219.0 | None. Hold. | Blocked state visible. |
| 222.0 | Console: click `Run self-test`. | Test runs. |
| 225.0 | None. | `Services are up`, `Names stay separate` and `Appraisal systems cannot connect` all present and positive. **[VERIFY exact strings]** |
| 229.0 | Console: one small scroll to the deployment mode panel. | Demo versus Sovereign mode control rendered and legible. **[VERIFY exact labels. The narration says the demo is hosted and deployment runs on the force's own hardware, so this control must be readable while that sentence plays.]** Provider states honest. |
| 234.0 | Console: one small scroll back to the zone diagram. | Zone diagram and blocked Zone X both in frame. |
| 236.0 | **No input of any kind until capture stops.** | Frame static. |
| 240.0 | Stop capture. | |

**Do not click `Hold the unit link`. Do not switch deployment mode on camera.**

**Honesty rule.** If any provider shows held or degraded at t=229, the frame overstates or understates what is running. Complete the take, then report; a person runs `make providers-check` and refreshes the token before the next attempt.

The final four seconds are absolute stillness on the zone diagram. No scroll, no click, no pointer movement. This is the closing frame of the video.

---

# PART 7 · NARRATION

Generate this **before** the take. It is a single continuous 240.000 second WAV, built segment by segment and padded so every segment begins exactly at its mark.

## 7.1 The text, by segment

| Seg | Mark | Dur | Words | Text |
|---|---|---|---|---|
| S1 | 0 | 20 | 37 | Between 2020 and 2024 the CAPF lost 730 personnel to suicide, and 55,555 more resigned. Those are MHA's own figures. Everything after this is synthetic. MANOBAL is built for the weeks before. Support, not surveillance. |
| — | 20 | 3 | 0 | *(silence, Stage loading)* |
| S2 | 23 | 22 | 42 | It begins with twenty seconds. Mood, sleep, and only the context the jawan chooses, in their language. It writes to the phone first, so an outpost with no signal keeps working, buffering up to thirty days. Their commander never sees it. |
| S3 | 45 | 29 | 57 | No one is compared to anyone else. Each jawan is measured against their own ninety-day norm across seven domains: duty hours, leave, hardship, sleep, self-report, voice and check-in cadence. One rough week never flags anyone; two independent domains have to agree. The officer sees which ones fired and a recommended action. No score, no rank, no diagnosis. |
| S4 | 74 | 28 | 53 | The identity stays locked. To reach the person, the officer declares a care purpose and writes a justification, and the reveal is logged the instant it happens. On their own phone, the jawan sees that their identity was opened, by which role, and why. A contact note falls due after access. |
| S5 | 102 | 24 | 43 | Command sees companies, never people. Any group under ten is blanked, so no one can reason back to an individual. Ask the assistant who is under strain and it refuses, then answers only in aggregate. The boundary holds inside the AI too. |
| S6 | 126 | 24 | 41 | An acute phrase never reaches a language model. A deterministic filter runs on the device, ahead of any AI, and hands straight to a fixed, reviewed safety screen: Tele-MANAS, a welfare callback, SMS, and the jawan's own safety plan. |
| S7 | 150 | 15 | 26 | *(see 7.2, two variants)* |
| S8 | 165 | 20 | 37 | Oversight is adversarial by design. We tamper with the audit chain; the system catches the break, names its sequence, and restores it. Governance can pause Copilot or voice. It cannot switch off the acute path. |
| S9 | 185 | 22 | 43 | MANOBAL deliberately does not score suicide risk. The published record on those models is poor and the stigma is worse. It forecasts operational strain instead, measured for precision, recall, calibration and lead time under distribution shift. Synthetic validation, not field evidence. |
| S10 | 207 | 33 | 63 | Four zones. Analytics holds patterns, no names. Names sit in a separate vault, opened only for a justified care contact. Zone X, appraisal, promotion, posting, discipline, has no path in. This demo is hosted so you can reach it; deployment runs on the force's own hardware. Private self-help, accountable care, aggregate command, independent oversight. Prediction that earns trust by refusing to become surveillance. |

Total 442 words over 237 seconds of speech across 240 seconds of runtime, approximately 114 words per minute.

## 7.2 S7, two variants. Choose by branch B1.

**B1 = real (the typed phrase genuinely created the case):**

> Medical is on a fifteen-minute clock with the minimum context needed to respond. No journal text, no assessment answers. The next step is a person.

**B1 = seeded (default):**

> This is what Medical sees. A fifteen-minute clock, the minimum context needed to respond, no journal text, no assessment answers. The next step is a person.

The seeded variant does not assert that the case was created by the phrase just shown on screen. Four words separate a video that is true from one that survives only because nobody asked. Use it unless you have verified otherwise, and pair it with the burned-in notice in Part 9.2.

## 7.3 Generation

Azure Speech is already a configured provider. Use the REST synthesis endpoint with:

- Voice: `en-IN-NeerjaNeural` or `en-IN-PrabhatNeural`.
- Output format: `riff-48khz-16bit-mono-pcm`.
- Wrap each segment in SSML with `<prosody rate="-8%">` to land near 114 words per minute.
- Insert `<break time="500ms"/>` at each sentence boundary and `<break time="700ms"/>` before the final sentence of S9 and S10.

Do not read the Azure key. It is already in the environment; reference it, never print it.

Per segment:

```bash
# seg_S3.wav produced by TTS, then padded to its exact duration
ffmpeg -i seg_S3.wav -af "apad=whole_dur=29" -t 29 -ar 48000 -ac 1 -y pad_S3.wav
```

**Overflow check.** Before padding, measure each raw segment:

```bash
ffprobe -v error -show_entries format=duration -of csv=p=0 seg_S3.wav
```

If any raw segment exceeds its allotted duration, the narration will collide with the next segment. Do not trim the text. Reduce `rate` by a further 3 percent at a time, or if it still overflows, report it; a person edits the script. **Never cut a word to make it fit**, in particular never the closing sentence of S9, which is what makes the preceding sentence credible.

Assemble, including the 3 second silent transition:

```bash
ffmpeg -f lavfi -i anullsrc=r=48000:cl=mono -t 3 -y pad_TRANS.wav

printf "file '%s'\n" pad_S1.wav pad_TRANS.wav pad_S2.wav pad_S3.wav pad_S4.wav \
  pad_S5.wav pad_S6.wav pad_S7.wav pad_S8.wav pad_S9.wav pad_S10.wav > vo_list.txt

ffmpeg -f concat -safe 0 -i vo_list.txt -c copy -y vo_raw.wav

ffmpeg -i vo_raw.wav -af loudnorm=I=-16:TP=-1.5:LRA=11 -ar 48000 -y \
  manobal_demo_voiceover_48k.wav
```

Verify the result is 240.000 seconds, plus or minus 0.05:

```bash
ffprobe -v error -show_entries format=duration -of csv=p=0 manobal_demo_voiceover_48k.wav
```

If it is not, fix it before recording. The audio must not be stretched or resampled to fit afterwards.

## 7.4 A note on the voice

Neural TTS will render this competently and slightly flat. Two lines carry more than the others: the opening figures in S1, and the first sentence of S9. If a human read is available for the final submission, use it; the SSML timings above transfer directly.

---

# PART 8 · CAPTURE

## 8.1 The command

One invocation, backgrounded, running for the whole take.

```bash
mkdir -p out

ffmpeg -f avfoundation -capture_cursor 1 -framerate 30 \
  -i "DISPLAY_IDX:none" \
  -vf "crop=CROP_W:CROP_H:CROP_X:CROP_Y,scale=1920:1080:flags=lanczos" \
  -r 30 -vsync cfr \
  -c:v libx264 -preset veryfast -crf 16 -pix_fmt yuv420p \
  -an \
  -y out/manobal_screen_master.mp4 \
  > out/ffmpeg_capture.log 2>&1 &

echo $! > /tmp/manobal_rec.pid
```

Substitute the values measured in 2.3. Notes on each choice:

- `-framerate 30` with `-r 30 -vsync cfr` forces constant frame rate. Variable frame rate fails the technical inspection.
- `crop` then `scale` captures native Retina pixels and downsamples, which is materially sharper for UI text than capturing at 1080 directly.
- `-crf 16` is near-visually-lossless for the master. Compression happens at export, not at capture.
- `-an` because audio is generated separately and muxed. Never capture system audio.

## 8.2 Start and stop protocol

```bash
# 1. start capture
#    (command above)

# 2. allow the encoder to settle, then take t0
sleep 2.0
# t0 = monotonic clock reading, NOW

# 3. run the Part 6 sequence against t0

# 4. at t0+240.5, stop cleanly
kill -INT $(cat /tmp/manobal_rec.pid)
wait
```

The two second settle is essential. `ffmpeg` drops the first frames while the encoder initialises, and `t0` must be taken after that, not at process launch. The 0.5 second of overrun at the end is trimmed at export and guarantees you do not lose the final frame.

Use `kill -INT`, never `kill -9`. A hard kill leaves an unfinalised MP4 with no moov atom and the whole take is lost.

## 8.3 Immediate verification

Before doing anything else:

```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=width,height,r_frame_rate,avg_frame_rate,nb_frames,pix_fmt \
  -show_entries format=duration -of json out/manobal_screen_master.mp4
```

- `width` 1920, `height` 1080
- `r_frame_rate` equals `avg_frame_rate` equals `30/1`. **If they differ, the capture is variable frame rate and must be redone.**
- `nb_frames` approximately 7215, which is 240.5 seconds at 30 fps. Materially fewer means dropped frames.
- `duration` at least 240.0

Then extract three stills and look at them, to confirm the capture is not black and the crop is correct:

```bash
for T in 5 120 238; do
  ffmpeg -ss $T -i out/manobal_screen_master.mp4 -frames:v 1 -y out/check_$T.png
done
```

A black frame here means screen-recording permission was never granted. Fix the permission, do not attempt another take until a still shows the browser.

---

# PART 9 · ASSEMBLY

One filter-and-mux pass over the single capture. No trimming of the interior, no joins, no transitions. The video remains one unbroken take.

## 9.1 Captions

Build an SRT from Part 7, with each cue timed to the actual sentence boundaries in the generated WAV. Two lines maximum, roughly 42 characters per line, punctuation exactly as written.

```
1
00:00:00,400 --> 00:00:06,200
Between 2020 and 2024 the CAPF lost 730
personnel to suicide, and 55,555 more resigned.
```

Save as `out/manobal_demo_captions_en.srt` and deliver it as a sidecar as well as burning it in.

## 9.2 Labels

Three burned-in elements. None overlaps the caption band or the phone's bottom navigation.

**Persistent, 0 to 240:**

```
PROTOTYPE · SYNTHETIC DATA
```

Bottom-left, small, 60 percent opacity.

**`DESIGN TARGET · SDD v1.0`**, bottom-right, same size, only during these windows. These cover claims that describe the deployment architecture rather than the running build.

| Window | Covers | Condition |
|---|---|---|
| t=37 to t=43 | 30-day encrypted offline store | Always. No offline evidence is on screen in a single take. |
| t=48 to t=58 | Seven ingestion domains | Only if branch B4 says the console does not render all seven by name. |
| t=129 to t=134 | On-device deterministic filter | Always. The prototype evaluates server-side. |
| t=166 to t=171 | Independent oversight body | Only if branch B5 says no oversight body is named on screen. |
| t=210 to t=222 | HSM identity vault and hardware air-gap | Always. |

Align each window to the actual sentence timing in the rendered WAV, not to these approximate marks.

**Seeded case notice**, mandatory if and only if branch B1 is `seeded`:

```
Seeded acute case, shown to illustrate the Welfare and Medical view.
```

Top third, caption font, t=150 to t=165 in full.

Without it, the cut from a typed phrase to a live acute board asserts a causal link the build does not make. It is the one place this video could be accused of misleading, and it costs eleven words to close.

## 9.3 The export

```bash
ffmpeg -i out/manobal_screen_master.mp4 \
  -i manobal_demo_voiceover_48k.wav \
  -filter_complex "\
[0:v]trim=start=0:end=240,setpts=PTS-STARTPTS[v0];\
[v0]subtitles=out/manobal_demo_captions_en.srt:force_style='FontName=Helvetica,FontSize=22,PrimaryColour=&H00FFFFFF,BackColour=&HA0000000,BorderStyle=4,MarginV=40'[v1];\
[v1]drawtext=text='PROTOTYPE · SYNTHETIC DATA':fontsize=18:fontcolor=white@0.6:x=32:y=h-36[v2];\
[v2]drawtext=text='DESIGN TARGET · SDD v1.0':fontsize=18:fontcolor=white@0.6:x=w-tw-32:y=h-36:enable='between(t,37,43)+between(t,129,134)+between(t,210,222)'[vout]" \
  -map "[vout]" -map 1:a \
  -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -r 30 -vsync cfr \
  -c:a aac -b:a 256k -ar 48000 \
  -movflags +faststart \
  -t 240 \
  -y out/manobal_demo_final_4min_1080p30_h264.mp4
```

Add the conditional `between()` windows for B4 and B5 to the `enable` expression if those branches apply. Add a third `drawtext` for the seeded-case notice if B1 is `seeded`.

The `trim=start=0:end=240` removes only the 0.5 second capture overrun at the tail. It does not cut the interior. The take remains continuous.

## 9.4 Compressed upload copy

Check the SIH portal's size and duration limits before exporting. A 4 minute 1080p30 file at CRF 18 is roughly 200 to 350 MB, which is usually fine, but confirm.

```bash
ffmpeg -i out/manobal_demo_final_4min_1080p30_h264.mp4 \
  -c:v libx264 -preset slow -crf 23 -pix_fmt yuv420p -r 30 -vsync cfr \
  -c:a aac -b:a 192k -movflags +faststart \
  -y out/manobal_demo_final_4min_upload.mp4
```

## 9.5 Checksum

```bash
shasum -a 256 out/manobal_demo_final_4min_1080p30_h264.mp4 \
  > out/manobal_demo_final_4min_1080p30_h264_sha256.txt
```

---

# PART 10 · VERIFICATION

## 10.1 Technical

```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_name,width,height,r_frame_rate,avg_frame_rate,pix_fmt,nb_frames \
  -show_entries format=duration,bit_rate -of json \
  out/manobal_demo_final_4min_1080p30_h264.mp4

ffprobe -v error -select_streams a:0 \
  -show_entries stream=codec_name,sample_rate,channels,bit_rate -of json \
  out/manobal_demo_final_4min_1080p30_h264.mp4

ffmpeg -i out/manobal_demo_final_4min_1080p30_h264.mp4 -af ebur128 -f null - 2>&1 | tail -20
```

Required: `h264`, 1920x1080, `r_frame_rate` equal to `avg_frame_rate`, `yuv420p`, duration at most 240.0, audio `aac` at 48000 Hz, integrated loudness near -16 LUFS, true peak at or below -1.5 dB.

## 10.2 Visual sampling

Extract a frame every ten seconds and inspect all twenty-four.

```bash
mkdir -p out/frames
ffmpeg -i out/manobal_demo_final_4min_1080p30_h264.mp4 \
  -vf fps=1/10 -y out/frames/f_%03d.png
```

Confirm across the set: no terminal, no notification, no DevTools, no dock or menu bar, no secret or token, no Director drawer, captions never covering the phone's bottom navigation, the persistent label present throughout, both frames legible.

## 10.3 Content checklist

- [ ] Duration at most 240.0 seconds, and the video is one continuous take.
- [ ] Opens on the 730 and 55,555 figures with the MHA source visible.
- [ ] States all data is synthetic within the first ten seconds.
- [ ] `Support, not surveillance` visible.
- [ ] The ribbon is never described as a score or a rank.
- [ ] Check-in completed and saved on the phone.
- [ ] Contributing domains, trajectory and recommended action all shown in S3.
- [ ] No numeric personal score or rank anywhere in the video.
- [ ] Identity starts `Locked`.
- [ ] Purpose and justification both entered on camera.
- [ ] The phone ledger visibly gains a row after the reveal.
- [ ] Command shows aggregate posture with the small group suppressed.
- [ ] Copilot refuses individual identification.
- [ ] No name, case ID, token or contact detail in any Command frame.
- [ ] The acute phrase produces no generated reply.
- [ ] Safety shows Tele-MANAS 14416, welfare callback, SMS, safety plan.
- [ ] Medical shows the 15-minute clock and minimum context only.
- [ ] Acknowledge never clicked.
- [ ] If B1 is seeded, the notice is burned in and the seeded narration variant was used.
- [ ] Governance tamper and restore both appear.
- [ ] Acute path shows `Always on`.
- [ ] Lab shows metrics, shifted-world comparison, lead time, excluded attributes and a disclaimer.
- [ ] The line "does not score suicide risk" is present and clearly audible.
- [ ] No spoken or burned-in number differs from the screen, except S1's sourced MHA figures.
- [ ] Zone X shown as blocked, self-test positive.
- [ ] The deployment mode control is legible while the hosting sentence plays.
- [ ] Final four seconds are still, on the zone diagram.
- [ ] `DESIGN TARGET` appears on every applicable window and on **no other**. A design label over a demonstrated feature undersells the build.

## 10.4 Watch it

Play the exported file from start to finish before delivering. Not scrubbed. Watched. If you cannot play video, say so plainly and state that a person must watch it before submission.

---

# PART 11 · REPORT

Emit exactly this. Nothing more optimistic than this.

```
PREFLIGHT
  engine health            : pass | fail (observed response)
  web 3000                 : pass | fail
  providers                : N pass, M fail
  screen recording permission verified by black-frame check : yes | no
  DISPLAY_IDX / crop geometry :

BRANCHES
  B1 acute causality       : real | seeded
  B2 Medical Acknowledge   : fixed | unfixed   (not clicked either way)
  B3 Lab disclaimer        : present | ABSENT (stop condition)
  B4 seven domains named   : yes | no
  B5 oversight body named  : yes | no

DECK ALIGNMENT
  case id / tier / domains string / action string :
  Alpha Coy / Charlie Coy postures                :
  suppression threshold shown                     :
  acute SLA shown                                 :

DRY RUN
  runs completed clean     :
  rail labels resolved     :
  phone nav labels resolved:
  scroll amounts recorded  :
  worst-case Copilot latency :
  all [VERIFY] items resolved : yes | list what is unresolved

TAKES
  attempt | outcome | failed at mark | reason
  1       |         |                |
  2       |         |                |

ACCEPTED TAKE
  max drift observed       :  s at mark
  assertions failed        : none | list with timestamps
  capture nb_frames / duration / r_frame_rate vs avg_frame_rate :

OBSERVED VALUES (for the record, never spoken)
  Alpha / Charlie postures :
  governance break sequence:
  precision / recall / F1 / calibration :
  lead time (with unit)    :

NARRATION
  per-segment raw durations vs allotted :
  any segment that overflowed and what was done :
  final WAV duration / integrated LUFS / true peak :

LABELS APPLIED
  windows used, and why each conditional one was or was not applied :

OUTPUT
  final file path / size / sha256 :
  upload copy path / size :
  watched end to end : yes | no, and by whom

BLOCKERS AND DEVIATIONS
```

---

# PART 12 · DEFINITION OF DONE

Complete only when all of the following are true. If any is false, say which.

- Preflight verified by you immediately before the take.
- The dry run exit criteria in 3.4 were met before the first frame was captured.
- All five branches determined and recorded.
- The video is **one continuous capture** from 0.000 to 240.000, with no interior cuts, joins or transitions.
- Every scheduled action fired within 0.35 seconds of its mark.
- Every assertion passed, or each failure is reported with its timestamp.
- Neither hard product-failure stop occurred.
- The exact narration from Part 7 was used, with no word changed, added or removed.
- Labels applied exactly as Part 9.2 and the branch results specify.
- No feature was simulated, mocked or staged.
- No secret, terminal, notification, DevTools or unrelated window appears in any sampled frame.
- The technical inspection in 10.1 passed, including constant frame rate.
- The file was watched end to end, by you or by a named person.
- The report in Part 11 is complete and accurate.

If the take failed, the correct output is a failure report naming the mark, the expected result and the observed result. Deliver that. Do not deliver a partial file described as complete, and do not describe a take you did not achieve.