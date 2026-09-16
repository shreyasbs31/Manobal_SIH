# MANOBAL UI Direction v3

**Status:** binding for all UI work. Refines and extends section 16 of `02_MANOBAL_MVP_BUILD_SPEC.md`. Where they differ, this document wins.
**Goal:** a judge watching a 1080p video should recognise MANOBAL from a single frame, trust it within ten seconds, and never think "template".

---

## 0. What "brilliant" means for this product

Three tests every screen must pass:
1. **Recognisable:** it could only belong to a welfare system for Indian uniformed forces. Swap the logo and it still does not look like a fintech dashboard or a meditation app.
2. **Calm under pressure:** a tired constable after a night shift and a welfare officer with 30 cases both know what to do within three seconds.
3. **Legible on video:** every important word readable at 1080p without zooming; every key moment has one obvious focal point.

Where the first build most likely falls short (check your screens against this list):
- Default shadcn feel: same radius, same grey shadow, identical cards in grids.
- Everything given equal weight: no single hero per screen.
- Too many chips and badges competing.
- Charts with legends instead of direct labels.
- Generic AI orb for the companion.
- Emoji-font faces for mood.
- Command console that looks like any analytics product.
- Landing hero built from a big number, a small label, and a gradient.

---

## 1. Design concept: Contour

Indian uniformed forces work across terrain: high passes, jungle, river plains, cities. Their shared visual language is the **survey map**: contour lines, grid squares, references, legends. MANOBAL borrows that language and turns it toward care.

- **Contour** is the brand idea. A person's wellbeing is drawn as terrain that stays within its usual contours; change shows up as the lines bunching.
- **Lay** (लय, rhythm) is the personal signature: the baseline ribbon, called "Your usual rhythm" in English and "आपकी सामान्य लय" in Hindi.
- **Field sheet** is the command signature: the formation grid drawn like a map sheet with grid references.

Two skins, one family:
- **Saathi skin, "Contour calm":** light, airy, soft contour texture, rounded, warm, voice-first.
- **Command skin, "Field sheet":** dark slate map sheet by default, fine grid, brass references, dense and exact. Light "survey paper" theme for daytime offices.

Spend boldness in exactly three places: the Lay ribbon, the voice contour, and the formation grid. Everything else is quiet.

---

## 2. Foundations

### 2.1 Colour

**Saathi core**
| Name | Hex | Role |
|---|---|---|
| Neem | #2F5D50 | Primary actions, active tab, ribbon line |
| Neem deep | #1F4238 | Pressed states, safety screen background option |
| Mist | #F4F8F6 | App background |
| Contour | #CFDDD6 | Texture lines, dividers, ribbon band fill (at 60%) |
| Dusk ink | #1B2427 | Body text |
| Dawn | #F2C6A0 | Only for the "today" marker on the Lay ribbon and completion glow |

**Command core**
| Name | Hex | Role |
|---|---|---|
| Monsoon | #131C24 | Background |
| Slate panel | #1B2630 | Panels, rail |
| Map line | #2A3945 | Grid lines, borders |
| Brass | #C8A24A | References, focus rings, active states, selected cell outline |
| Khaki | #BFB28A | Secondary text, axis labels |
| Chalk | #E8ECE9 | Primary text |

**Survey paper (Command light theme):** background #EEF1EB, panel #F8FAF6, map line #CBD3C8, brass #8F6F1E (darkened for contrast), ink #1B2427.

**Tier colours** (unchanged hues, adjusted per surface for contrast): T0 #6E927F, T1 #4D8BAE, T2 #D6A13D (use #9A6F12 for strokes and glyphs on light surfaces), T3 #D06A34, T4 #B83A2E.
Rules:
- Tier text labels are always in ink or chalk, never in the tier colour.
- Tier colour appears as a glyph fill, a 3 px left edge, or a band segment. Never as a full card background, except the T4 banner.
- T4 red appears only for T4 and call buttons. Nothing else in the product is red. Errors use Dusk ink with an outline icon, not red.

**Elevation (both skins):** three levels only.
- Level 0: page.
- Level 1: panels. Saathi: white #FFFFFF with 1 px Contour border, no shadow. Command: Slate panel, 1 px Map line border, no shadow.
- Level 2: floating (sheets, popovers, drawers, T4 banner). Saathi: shadow `0 12px 32px rgba(31,66,56,0.14)`. Command: shadow `0 16px 40px rgba(0,0,0,0.45)` plus a 1 px Brass top edge at 40% opacity.

### 2.2 Typography
- **Anek** (variable width axis): display and numerals.
  - Expanded width (about 112) for the landing hero and Saathi greeting.
  - Normal width (100) for headings.
  - Condensed width (about 75) for KPI numerals, table numerals, SLA timers, grid references.
- **Mukta:** body, labels, buttons, captions.
- Scale (px, ratio 1.25): 12, 14, 16, 20, 25, 31, 39, 49, 61.

| Role | Saathi | Command |
|---|---|---|
| Hero | Anek expanded 39, weight 600 | Anek 31, weight 600 |
| Screen title | Anek 25, 600 | Anek 20, 600 |
| Section title | Mukta 16, 600 | Mukta 14, 600 |
| Body | Mukta 17, 400, line-height 1.55 | Mukta 14, 400, line-height 1.5 |
| Caption | Mukta 14, 400 | Mukta 12, 400 (13 minimum on screens that will be recorded) |
| Numeral large | Anek condensed 49, 600, tabular | Anek condensed 39, 600, tabular |
| Timer | Anek condensed 25, 600, tabular | Anek condensed 20, 600, tabular |

Rules: sentence case everywhere; no all-caps; no eyebrow labels above headings; no single highlighted word in a headline; no monospace anywhere in the UI (code blocks in Governance YAML excepted); Devanagari lines get line-height 1.7.

### 2.3 Space, radius, borders
- 4 px base grid. Spacing tokens: 4, 8, 12, 16, 24, 32, 48, 64.
- Radii encode hierarchy, not decoration:
  - Saathi: 24 for primary cards and sheets, 16 for secondary cards, 999 for chips and circular controls, 12 for inputs.
  - Command: 10 for panels, 6 for controls and rows, 2 for grid cells (map squares stay crisp).
- Borders: 1 px only. No double borders. Dividers inside panels use Map line or Contour at 60%.

### 2.4 Textures
- **Contour texture (Saathi):** generated SVG of 6 to 9 smooth, irregular closed contour lines (Perlin or simplex noise, marching squares), stroke Contour at 45% opacity, 1 px. Used only behind the Lay ribbon hero, the voice contour, onboarding, and the safety screen. Seeded per user so each person's texture is slightly different and stable (a quiet personal touch).
- **Map grid (Command):** 1 px lines every 48 px at 35% Map line, with brass grid references (A to F down, weeks across) only on the formation grid. Faint contour texture at 8% opacity in the rail background only.

### 2.5 Iconography
- Lucide at 1.75 px stroke for general icons, 20 px Saathi, 16 px Command.
- Custom tier glyphs (SVG): T0 circle, T1 drop, T2 triangle, T3 diamond, T4 octagon. Each glyph has a 1.5 px ink stroke plus tier fill.
- Custom icons needed: Lay ribbon, voice contour, hidden tile lock, edge queue, vault key, buddy pair, leave window, shift moon.
- No "AI sparkle" icons. AI-written content is labelled in words: "Written by Saathi AI, check before use".

### 2.6 Illustration kit
One consistent style across the product and the video:
- Flat vector, single-weight 1.5 px Dusk ink line, two fills maximum per scene (Neem at 20%, Mist, Dawn at 30% for light sources).
- People in plain olive-khaki uniforms with no insignia, no badges, no flags, no weapons, no unit numbers. Diverse skin tones, body types, ages, and both women and men.
- Calm, dignified poses. Never distressed faces. Never hospitals or stretchers.

Scenes (generate with an image model, then trace or clean to SVG; review every output for insignia, weapons, text, and symbols before use):
1. A constable sitting on a bunk after night duty, tea in hand, dawn window.
2. A high-altitude post at dusk with mountains and a small hut (no people's faces visible).
3. A jungle camp with a tent under trees and soft rain.
4. A city barricade at night with street lights, a jawan standing, a thermos nearby.
5. A jawan on a video call with family, a child waving on the screen.
6. Two colleagues sharing tea and talking (buddy).
7. A person listening on headphones, eyes closed (sleep wind-down).
8. A welfare officer and a jawan walking side by side (informal chat).
9. A counsellor on a laptop call (only the counsellor's side visible).
10. A calendar with a leave window circled and a bus in the distance (leave planner).
11. A barracks at night with a moon (shift planner).
12. Hands holding a phone with a contour pattern on screen (onboarding).
13. An empty-state scene: a quiet path through hills.
14. A group sitting in a circle outdoors (post-incident support), faces not detailed.

Base prompt for generation (adapt per scene):
"Flat vector illustration, single weight thin dark slate line art, limited palette of muted neem green and pale mist with a soft peach light source, calm and dignified mood, Indian setting, people in plain olive uniforms with no insignia, no badges, no flags, no weapons, no text, no logos, generous negative space, minimal detail, consistent line weight, white background."

### 2.7 Motion
| Token | Duration | Easing | Use |
|---|---|---|---|
| `instant` | 120 ms | ease-out | Press states, toggles |
| `quick` | 200 ms | cubic-bezier(0.2, 0.8, 0.2, 1) | Sheets, popovers, tab changes |
| `settle` | 320 ms | cubic-bezier(0.16, 1, 0.3, 1) | New case insertion, card expand |
| `draw` | 900 ms | cubic-bezier(0.65, 0, 0.35, 1) | Lay ribbon draw-in, stepped band draw |
| `breath` | 4 s loop | sine in-out | Breathing guides, safety screen ring |

Orchestrated moments (only these):
- Saathi home: Lay ribbon draws left to right, today marker settles with a soft Dawn glow.
- Check-in completion: the new point joins the ribbon.
- Voice: contour lines ripple outward with input amplitude; while Saathi speaks, lines tighten and relax with output amplitude.
- Welfare queue: a new case slides into its tier group with a single brass pulse on its left edge.
- T4: full-width banner drops from the top with the timer; no shaking, no flashing.
- Formation grid: cells resolve row by row once on first load.
- Architecture: packets travel along zone paths; the key icon travels to Zone 3 on identity resolve.
- Governance: tamper turns one chain link red and the chain line breaks.

Everything else: no entrance animations. Respect `prefers-reduced-motion` by replacing motion with opacity changes.

### 2.8 Sound and haptics
- Saathi: haptic tick on each check-in answer (`navigator.vibrate(8)`), soft double tick on completion, long gentle pulse pattern on the breathing guide inhale. Sound off by default.
- Consoles: a single soft two-tone chime for T3; a distinct, non-alarming three-tone for T4, repeating every 60 s until acknowledged. Volume control in the top bar.

### 2.9 Data-visualisation grammar
- Direct labels on lines and bands; legends only when more than three series.
- No pie or donut charts. No gauges or speedometers for stress.
- Stepped bands for tiers over time; ribbons for personal baselines; bars for comparisons; hatched cells for suppression.
- Axis text in Khaki (Command) or Dusk ink at 60% (Saathi). Gridlines at 35% opacity or none.
- Every chart has a one-sentence takeaway above it in plain words ("Charlie Coy's workload has risen for three weeks").
- Tabular numerals everywhere numbers align.
- Numbers on commander views are banded ("10 to 20%") below 10% granularity where the spec requires.

---

## 3. Signature components

### 3.1 Lay ribbon (`BaselineRibbonChart`)
- Band: median plus or minus 1.4826 x MAD, filled Contour at 60%, edges drawn as two thin contour-style lines.
- Line: Neem 2.5 px, smoothed (monotone cubic).
- Out-of-band points: small open circles in the direction of change; never red.
- Today: Dawn filled circle with a 12 px soft glow.
- Hero variant (Saathi home): 14 days, 180 px tall, no axes; below it one sentence: "You are within your usual rhythm" or "Your sleep has been below your usual rhythm for 3 nights".
- Detail variant (Me, case trend share): 30 or 90 days, weekday ticks, direct label "Your usual range".
- Empty state: a single dotted contour with "Your rhythm appears after a week of check-ins".

### 3.2 Voice contour (`VoiceContour`, replaces the orb)
- 7 concentric irregular contour rings on a canvas, generated from the user's seeded noise.
- Listening: rings expand with input RMS; outer rings lag slightly (spring).
- Thinking: rings slowly rotate phase, low amplitude.
- Speaking: rings breathe with output RMS.
- Crisis handoff: rings settle into perfect circles and fade to the safety screen.
- Captions below in 20 px (Saathi), user lines left-aligned in Dusk ink, Saathi lines in Neem.

### 3.3 Formation grid (`FormationGrid`)
- Map-sheet look: rows are companies (expandable to platoons and posts), columns are the last 12 weeks. Brass references on the top and left edges (W-11 to W0, A to F).
- Cell: 2 px radius, fill encodes banded share at T2+ on a single-hue scale derived from T2 to T3 (5 steps), never T4 red.
- Hidden cell: 45 degree hatch in Map line, small lock glyph, tooltip "Hidden to protect individuals. Fewer than 10 people or recent large changes."
- Selected cell: 2 px brass outline; the side panel shows the aggregate breakdown.
- Row header shows the company name and a tiny workload sparkline.

### 3.4 Case card (`CaseCard`) and case strip
- Card: 3 px left edge in tier colour, tier glyph plus label, case id in Anek condensed, trajectory arrow, one line of driver chips (maximum three, the rest as "+1"), "Drift began about 20 days ago", SLA timer right-aligned. Height 88 px in list.
- Case strip (top of workspace): full-width stepped tier band over 120 days with an onset flag, incident markers (small triangle), action markers (small brass squares), and today at the right edge.

### 3.5 SLA timer and escalation ladder
- Timer: Anek condensed; calm (Khaki) above 50% remaining, Brass under 50%, T3 marigold under 20%, T4 red only for T4 cases.
- Ladder: vertical steps (UWO, Company welfare deputy, Battalion MO, Sector counsellor), each with status (waiting, notified, acknowledged) and time.

### 3.6 Mood faces (`FaceScale`, replaces emoji)
- Five custom illustrated faces in the illustration style, gender-neutral, simple line work, no exaggerated sadness.
- 64 px targets with labels under each ("Very low" to "Very good", localised).
- Selected face scales to 1.1 with a Neem ring; haptic tick.

### 3.7 Consent card, receipt, ledger
- Consent card: illustration thumbnail left, title, "What leaves your phone" and "Who can ever see this" as two short lines, large toggle right. Expand for details.
- Receipt: a paper-slip style card with a perforated top edge drawn in SVG, hash shown in two short groups, "Download" button.
- Ledger item: role icon, "Welfare Officer, your unit, viewed your identity", reason in plain words, date. Grouped by month.

### 3.8 Chain status
- Horizontal chain of the last 12 audit blocks as small linked rectangles; verify runs a brass scan line across; tamper shows one block in T4 red with the link broken; restore heals the link.

### 3.9 Status chips
- Only three chip types in Saathi's status strip: Offline (with queued count), Syncing, Demo. Small, 24 px tall, muted.
- Command top bar: SimClock (Anek condensed), Mode (Demo or Sovereign), unit scope.

---

## 4. Screen compositions

Wireframes use 390 px wide phones and 1440 px wide desktops. Left alignment by default; centre alignment only for the safety screen and single-question check-in steps.

### 4.1 Saathi home
```
+--------------------------------------------+
| Suprabhat, Arjun                  ( SOS )  |  Anek expanded 31; SOS 48 px ring, T4 icon
| Night duty ended at 06:00                  |  Mukta 14, 60% ink
|                                            |
|  .-~~~~~~-.   contour texture   .-~~~-.    |
|  ======= Lay ribbon, 14 days =======  o    |  180 px hero; o = today (Dawn)
|  Your sleep has been below your usual      |  Mukta 17
|  rhythm for 3 nights.                      |
|                                            |
| +----------------------------------------+ |
| |  How are you after duty?               | |  Primary card, Neem fill, radius 24
| |  20 seconds              [ Start ]     | |  white text
| +----------------------------------------+ |
|                                            |
| For you now                                |  Mukta 16 600
| +----------------------------------------+ |
| | [illus] Sleep before tonight's duty    | |  one context card, radius 16
| |         A 20-minute nap plan  Why this?| |
| +----------------------------------------+ |
|                                            |
| [ Talk ] [ Breathe ] [ Counsellor ] [Leave]|  4 tiles, icon over label, 72 px
|                                            |
|--------------------------------------------|
|  Home     Saathi     Toolkit     Me        |  64 px, active tab Neem pill
+--------------------------------------------+
```
Offline: a slim bar under the greeting "Offline. 3 check-ins saved on this phone." No other layout change.

### 4.2 Check-in (one question per screen)
```
+--------------------------------------------+
| (x)                         1 of 3         |
|                                            |
|        How is your mood right now?         |  Anek 25, centred
|                                            |
|    ( :( ) ( :/ ) ( :| ) ( :) ) ( :D )      |  FaceScale, 64 px
|   Very low                     Very good   |
|                                            |
|   ~~~~~ contour progress line ~~~~~        |  fills as questions advance
|                                            |
|  [ Say it instead ]                        |  secondary, mic icon
+--------------------------------------------+
```
Completion: the ribbon appears with the new point joining; one sentence: "Saved. Thank you for checking in."; button "Done".

### 4.3 Saathi voice
```
+--------------------------------------------+
| Saathi            Hindi v        (x)       |
| [ Check in | Ask | Talk it through ]       |  segmented control
|                                            |
|          ((( voice contour )))             |  260 px canvas
|                                            |
|  You: Aaj neend poori nahi hui             |  captions, 20 px
|  Saathi: Raat ki duty ke baad aisa ho      |
|  sakta hai. Kya aaj thoda aaram mil paaya? |
|                                            |
|  Audio cleared in 84 ms                    |  small chip
|  Prototype: open-weight model on Azure     |  caption, 12 px
|                                            |
|        ( hold to talk )    [ keyboard ]    |  80 px primary round button
+--------------------------------------------+
```

### 4.4 Safety screen
```
+--------------------------------------------+
|                                            |  background Neem deep, contour texture 20%
|        You are not alone.                  |  Anek 31, white, centred
|   Someone is being asked to reach you.     |  Mukta 17
|                                            |
|            ( breathing ring )              |  breath motion
|           Breathe in with the ring         |
|                                            |
| [ Call Tele-MANAS 14416        ]           |  T4 red button, white text, 56 px
| [ Ask my welfare officer to call me  (v) ] |  white outline, preselected
| [ Send SOS by SMS              ]           |  white outline
| [ Open my safety plan          ]           |  text button
|                                            |
|  Reaching your unit ... connected          |  status line
+--------------------------------------------+
```
Audio plays automatically at low volume with a visible mute button.

### 4.5 Toolkit breathing
Full-screen, contour ring in the centre expands and contracts; count in Anek 61; phase word ("Breathe in") under it; haptic on phase change; exit top left; no other UI.

### 4.6 Me: privacy and access ledger
Top: three plain statements with icons: "Your commander never sees you", "You choose what is shared", "You can see every access". Then consent cards, then "Who viewed my information" ledger grouped by month, then Rights actions as a simple list with chevrons (no arrow text).

### 4.7 Welfare queue (master-detail)
```
+------+--------------------------------------------------------------------------+
| rail | Bn C-02 welfare                 Open 14   Overdue 1   My load 14 of 25   |
|      |--------------------------------------------------------------------------|
|      | [T4] Urgent (1)                         | Case preview                   |
|      |  |MB-6604  Acute  ...   Timer 11:42    | MB-4091  High  Rising          |
|      | [T3] High (2)                           | Drift began about 20 days ago  |
|      |  |MB-4091  Roster overtime, Sleep  Rising   46:10 | case strip           |
|      |  |MB-3021  Leave denial, Stress    Stable   30:02 | What changed         |
|      | [T2] Elevated (11)                      | Recommended: 48-hour rest      |
|      |  |MB-2217 ...                     5d 04h | [ Open case ]                 |
+------+-----------------------------------------+--------------------------------+
```
T4 banner spans the full width above this when active. Keyboard: J and K to move, Enter to open.

### 4.8 Case workspace
```
+-----------------------------------------------------------------------------------+
| < Queue   MB-4091   [T3 High]  Rising   SLA 46:10                      [Actions v]|
| ================ case strip: 120-day stepped band, onset flag, markers ========== |
+-------------------------------+---------------------------+-----------------------+
| What changed                  | Recommended actions       | Identity               |
|  Roster overtime              |  1 Sanction 48-hour rest  |  Locked                |
|   19 days without a rest day  |    Often helpful in ...   |  [ Reveal to contact ] |
|  Sleep loss                   |  2 Rotate off night duty  |  This person will see  |
|   Less sleep than usual       |  3 Informal conversation  |  that you viewed it.   |
|                               |  No action needed         |-----------------------|
| Trend sharing                 |---------------------------| Log                    |
|  Sleep  [ Request ] Pending   | Saathi AI brief  (Hindi v)|  Contacted  Decision   |
|                               |  4 sentences with field   |  Follow-up  Refer      |
|                               |  reference underlines     |  [ Close case ]        |
|                               |  Openers: 1, 2, 3         |                        |
+-------------------------------+---------------------------+-----------------------+
```
Numbered list is correct here because levers are a ranked sequence.

### 4.9 Medical acute board
Large timers, one card per T4 case, escalation ladder visible on each card, acknowledge button 48 px in brass. Nothing else on the page.

### 4.10 Command posture (field sheet)
```
+------+---------------------------------------------------------------------------+
| rail | Bn C-02   Week 38                           Scope v   Copilot [open]      |
|      | Duty hrs 61   Rest denials 14   Night load 38%   Leave backlog 22 days    |  condensed numerals strip
|      |---------------------------------------------------------------------------|
|      | Charlie Coy's workload has risen for three weeks.                          |  takeaway sentence
|      |      W-11 W-10 W-9 ... W-1  W0      | Charlie Coy, W0                    |
|      |  A   [ ][ ][ ] ...  [ ][ ]           |  Share at T2 or above: 20 to 30%   |
|      |  B   [ ][ ][ ] ...  [ ][ ]           |  Top drivers: Roster overtime,     |
|      |  C   [ ][ ][#] ...  [#][#]           |  Night load                        |
|      |    Post D-7  [////][////] locked     |  [ Open roster balancer ]          |
|      |  D ...                               |                                    |
+------+--------------------------------------+------------------------------------+
```
Copilot opens as a right drawer (480 px) with suggested questions in Hindi and English and inline charts.

### 4.11 Roster balancer
Left: company list with sliders (duty hours, rest days, night share, quick-return cap, leave release). Right: two small multiples, "Projected posture in 14 days" and "Operational coverage", each with before and after bands. Bottom: "Create draft order". Groups under 10 show a locked slider with an explanation.

### 4.12 Governance overview
Top row: five KPI tiles with condensed numerals and a one-line definition. Middle: fairness bars with the 0.8 to 1.25 band shaded. Bottom: chain status component and kill switches as large labelled switches (the acute path shown as "Always on" with a lock, not a switch).

### 4.13 Validation Lab
Scientific restraint: white or survey-paper background even in dark mode is allowed here for charts. World toggle (Primary, Shifted). Lead-time histogram with median line directly labelled. Ablation table with deltas.

### 4.14 Architecture
Four columns as physical layers (Device, Unit server, Analytics, Identity vault) with Zone X to the far right as a dashed, crossed card labelled "Appraisal, promotion, posting, discipline: no connection". Packets as small Neem dots moving along paths; the identity key as a brass dot. Self-test results as a checklist under the diagram. Mode panel at the bottom.

### 4.15 Landing
```
+-----------------------------------------------------------------------------------+
| MANOBAL                                                   Trust centre   Sign in  |
|                                                                                   |
|  Every jawan has a usual rhythm.                                                  |  Anek expanded 61
|  MANOBAL notices when it changes,                                                 |
|  and makes sure the right person helps.                                           |
|                                                                                   |
|  ======== animated Lay ribbon across the full width, contour texture ==========  |
|  (the line drifts out of its band, a quiet marker appears, then it returns)       |
|                                                                                   |
|  Support, not surveillance.                                                       |  Mukta 20
|                                                                                   |
|  [ Personnel ]  [ Welfare officer ]  [ Commander ]  [ Ethics cell ]  [ More ]     |  role doors with illustrations
|                                                                                   |
|  Figures cited: source and date in small text under each                          |
+-----------------------------------------------------------------------------------+
| Second fold: problem statement components mapped to screens, as a clean table     |
+-----------------------------------------------------------------------------------+
```

### 4.16 Stage (for recording)
- 1920 by 1080 canvas; phone frame at left with a realistic but unbranded device outline, 390 by 844 screen scaled to 88%; console at right.
- A 44 px top bar: MANOBAL mark, simulated date chip, beat name (from Director preset), mode chip.
- The Director drawer is hidden during recording (toggle with a key).

---

## 5. Copy system

### 5.1 Voice
- Personnel: warm, short, respectful, "aap" in Hindi. No exclamation marks.
- Officers: factual, neutral, specific.
- AI content: always labelled, never presented as a decision.

### 5.2 Key strings (English and Hindi; have a native speaker review)
| Key | English | Hindi |
|---|---|---|
| home.checkin.title | How are you after duty? | ड्यूटी के बाद आप कैसा महसूस कर रहे हैं? |
| home.lay.within | You are within your usual rhythm. | आप अपनी सामान्य लय में हैं। |
| home.lay.sleepLow | Your sleep has been below your usual rhythm for {n} nights. | पिछली {n} रातों से आपकी नींद सामान्य से कम रही है। |
| safety.title | You are not alone. | आप अकेले नहीं हैं। |
| safety.reaching | Someone is being asked to reach you. | किसी को आपसे संपर्क करने के लिए कहा जा रहा है। |
| privacy.commander | Your commander never sees you. | आपके कमांडर आपको कभी व्यक्तिगत रूप से नहीं देखते। |
| checkin.saved | Saved. Thank you for checking in. | सहेज लिया गया। चेक-इन करने के लिए धन्यवाद। |
| offline.bar | Offline. {n} check-ins saved on this phone. | ऑफ़लाइन। {n} चेक-इन इस फ़ोन पर सहेजे गए हैं। |

### 5.3 Naming
Use one name per thing everywhere: "Check-in", "Saathi", "Your usual rhythm", "Welfare Officer", "Counsellor", "Case", "Reveal identity", "Access record", "Hidden to protect individuals".

---

## 6. Responsive and recording rules
- Breakpoints: 360, 390, 412 (phones), 768 (tablet), 1280, 1440, 1920.
- Saathi max content width 480 px on larger screens, centred in the viewport with contour texture outside.
- Consoles: rail collapses at 1280; master-detail becomes list then detail at 1024.
- Recording: consoles at 1920 by 1080 with browser zoom 110 to 125%; no text under 13 px after zoom; key numbers at least 20 px.
- Test every screen at 200% text zoom and in right-to-left (Urdu).

---

## 7. Accessibility
- WCAG 2.2 AA contrast for text, 3:1 for glyphs and focus rings.
- Focus ring: 2 px Brass (Command) or Neem (Saathi) with 2 px offset.
- Targets 48 px minimum in Saathi, 32 px in consoles.
- Every chart has a text alternative (the takeaway sentence plus a data table toggle).
- Screen-reader labels for tier glyphs ("Tier 3, High").
- Captions always available for voice.

---

## 8. Banned list
- Camouflage patterns, stencil fonts, dog tags, crosshairs, radar sweeps, rifles, helmets as icons.
- National emblem, force crests, flags, tricolour gradients.
- Political or religious symbols or colour pairings (for example lotus, hand, broom, diya as a brand mark, saffron-and-green schemes).
- Brains, EKG heartbeat lines, speedometers, traffic-light stress meters.
- System emoji as mood faces.
- AI sparkles, glowing orbs, glassmorphism, gradient washes, neon on black.
- Identical card grids, one radius everywhere, grey drop shadows on every card.
- All-caps labels, eyebrow labels, middle-dot meta strings, arrows appended to button text, monospace data labels.
- Red for anything except T4 and call buttons.
- Lorem ipsum, "John Doe", placeholder avatars.

---

## 9. Review loop (mandatory for every UI task)
1. Screenshot each touched screen at 390 by 844 and 1440 by 900 (and 1920 by 1080 for Stage) in both themes using Playwright; save to `e2e/artifacts/ui/`.
2. Score each screen 1 to 5 on: single clear focal point; recognisably MANOBAL (Contour language present where specified, nowhere else); hierarchy and spacing on the 4 px grid; copy quality (plain, sentence case, localised); data-viz grammar; motion restraint; accessibility (axe clean, focus visible, contrast); video legibility.
3. Any score below 4: write the problem and fix in `docs/UI_NOTES.md`, fix it, re-screenshot.
4. Maximum three rounds per screen; then note remaining issues for human review.
5. Before finishing, remove one decorative element from each screen if the screen still works without it.
