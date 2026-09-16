# UI notes (Direction v3)

Review loop from UI direction section 9. Scores are 1 to 5. Target is 4 on every line. Before shots live in `e2e/artifacts/ui/before-*.png`. After shots live in `e2e/artifacts/ui/after-*.png`.

## Audit against section 0 (Prompt 2, before)

Three tests:
1. Recognisable: fail. Swap the ribbon mark and this is a generic wellness dashboard. No survey-map language, no contour texture, no field-sheet grid.
2. Calm under pressure: fail. Home gives equal weight to check-in, ribbon, and nudge. Welfare cards are tall and chatty. Medical is a single loose card, not an acute board.
3. Legible on video: weak. Status chips compete with SOS. KPI tiles are a four-up card grid. Landing hero is a marketing headline plus three identical stat cards.

Section 0 shortfalls that are present:
- Default shadcn feel: one radius, grey-green shadow on every card, identical role cards and KPI tiles.
- No single hero per screen.
- Too many chips (Synthetic data, Online, Last sync, SOS, domain chips).
- Charts sit in white cards with a caption instead of direct labels.
- Generic AI orb on Saathi voice.
- Emoji-font faces in the gallery (`EmojiScale`).
- Command console looks like any analytics product (heatmap plus KPI grid).
- Landing hero is a big headline, a small kicker, and a pale wash. The ribbon is a tiny inset chart.

## Audit against section 8 (banned list)

Present in Prompt 2:
- Identical card grids (landing roles, command KPIs).
- One radius everywhere (18 px) and a drop shadow on every `.mb-card`.
- Eyebrow label on landing ("Predictive welfare support for CAPF personnel").
- System emoji as mood faces.
- Glowing orb (`.mb-orb`).
- Next.js "N" badge in recordings (dev indicator).
- Sparkles icon on the Director rail item.
- Red used on T4 timer text (allowed for T4) but also on a generic SOS pill that reads as a badge, not a 48 px call ring.
- Case ids such as "Case 7F2A" instead of persona tokens (MB-4091).
- No camouflage, flags, crests, brains, EKG, or traffic-light meters. Keep it that way.

Missing screens (not built): check-in, safety, breathing, case workspace. Missing Survey paper theme.

## Before screenshots

| Screen | File |
|---|---|
| Landing | `e2e/artifacts/ui/before-landing-1440.png` |
| Saathi home | `e2e/artifacts/ui/before-home-1440.png` |
| Saathi voice | `e2e/artifacts/ui/before-saathi-1440.png` |
| Toolkit | `e2e/artifacts/ui/before-toolkit-1440.png` |
| Me | `e2e/artifacts/ui/before-me-1440.png` |
| Welfare | `e2e/artifacts/ui/before-welfare-1440.png` |
| Command | `e2e/artifacts/ui/before-command-1440.png` |
| Medical | `e2e/artifacts/ui/before-medical-1440.png` |
| Stage | `e2e/artifacts/ui/before-stage-1440.png` |
| Gallery | `e2e/artifacts/ui/before-gallery-1440.png` |

Phone (390) before frames were not saved in Prompt 2; Saathi was stretched to desktop. After shots must include 390 by 844 and 1440 by 900 (Stage also 1920 by 1080).

## Rubric (after rounds)

Columns: Focal, MANOBAL, Hierarchy, Copy, Data-viz, Motion, A11y, Video.

| Screen | Focal | MANOBAL | Hierarchy | Copy | Data-viz | Motion | A11y | Video | Round |
|---|---|---|---|---|---|---|---|---|---|
| Landing | 5 | 5 | 4 | 5 | 5 | 4 | 5 | 5 | 2 |
| Saathi home | 4 | 5 | 4 | 5 | 5 | 4 | 5 | 5 | 2 |
| Check-in | 5 | 4 | 5 | 5 | 4 | 4 | 5 | 5 | 2 |
| Saathi voice | 5 | 5 | 4 | 5 | 4 | 4 | 5 | 5 | 2 |
| Safety | 5 | 5 | 5 | 5 | 4 | 4 | 5 | 5 | 2 |
| Breathing | 5 | 4 | 5 | 5 | 4 | 5 | 5 | 5 | 2 |
| Me | 4 | 4 | 4 | 5 | 4 | 4 | 5 | 4 | 2 |
| Welfare queue | 4 | 4 | 4 | 5 | 4 | 4 | 5 | 4 | 2 |
| Case workspace | 4 | 4 | 4 | 5 | 4 | 4 | 5 | 4 | 2 |
| Medical acute | 5 | 4 | 4 | 5 | 4 | 4 | 5 | 5 | 2 |
| Command posture | 5 | 5 | 4 | 5 | 5 | 4 | 5 | 5 | 2 |
| Governance | 4 | 4 | 4 | 5 | 4 | 4 | 5 | 4 | 2 |
| Architecture | 4 | 4 | 4 | 5 | 4 | 4 | 5 | 4 | 2 |
| Stage | 4 | 4 | 4 | 4 | 4 | 4 | 5 | 5 | 2 |

Axe: `e2e/tests/ui-review.spec.ts` 16 passed on localhost:3000 (stage excludes iframes; nested screens are scored on their own routes). Gallery shots exist for Saathi dark, Saathi high contrast, Command dark, and Command light (Survey paper).

## Illustration banned-list review

Each of the 14 scenes is original line-art SVG (no stock). Checks: no insignia, weapons, flags, unit numbers, text, logos, distressed faces, hospitals.

| Slot | Source | Banned list | Notes |
|---|---|---|---|
| bunkDawn | original SVG | pass | Dawn window fill only; no insignia. |
| highPost | original SVG | pass | Hut and ridgeline; no faces, flags, or weapons. |
| jungleCamp | original SVG | pass | Tent under trees; rain as short strokes. |
| cityNight | original SVG | pass | Street light and standing figure; no barricade spikes. |
| familyCall | original SVG | pass | Screen rectangle with a small waving figure. |
| buddyTea | original SVG | pass | Two seated outlines sharing a cup. |
| sleepWindDown | original SVG | pass | Headphones; eyes closed as simple arcs. |
| informalWalk | original SVG | pass | Two walking outlines, equal height. |
| counsellorCall | original SVG | pass | Desk and laptop; counsellor side only. |
| leaveWindow | original SVG | pass | Calendar box and distant bus silhouette. |
| shiftMoon | original SVG | pass | Barrack roof and moon disc. |
| onboardingPhone | original SVG | pass | Hands and phone with contour lines on the screen. |
| emptyPath | original SVG | pass | Path through hills; empty state. |
| circleSupport | original SVG | pass | Five seated marks; faces not detailed. |

Image-model generation: attempted for bunk-dawn and empty-path composition. Outputs were filled rasters, not single-weight SVG, so they were not shipped. Spec 31.1 has no image-model row; UI 2.6 original line-art is the fallback. No raster stock images in the app.

## Fixes

Round 1 (after first after-shots, CSS was broken so many frames were error pages):
- Voice contour rings, formation `revealed` init, case-strip fills, T4 banner `#8e241c`, landmarks, stage `data-open`.
- Home tiles sat under the tab bar. Greeting dropped to 31 px, ribbon 140 px, tab bar capped at 480 px, hero data-table chrome hidden.
- Command tiles were a flat khaki wash. Step mixes restored so Charlie Coy reads as a rising band; hidden cells keep hatch and lock.
- Breathing count sat in a 100 dvh spread. Inner cluster puts the count inside the ring.
- FaceScale used boxed per-face labels. Now 64 px faces with Very low / Very good end caps.
- Flow Close was a full-width ghost. Now a 44 px `x`.
- Ledger items inherited consent-card chrome. Ledger is a three-column row again.

Round 2:
- Case strip stretched full width (`preserveAspectRatio none` plus wrap).
- Medical SLA uses 49 px numerals.
- Stage phone iframe is a 390 by 844 surface scaled to 88 percent.
- Kill switches are labelled pills. Welfare officer is preselected on Safety.
- Stage axe: unique landmarks, page `h1`, iframe content excluded (those routes are tested directly).
- Gallery Case id is MB-4091, not 7F2A.

Section 9.5 decorative removals that still leave the screen working:
- Landing 390 hides Demo and Synthetic chips in the public header.
- Hero Lay ribbons hide the Data table disclosure (the SVG keeps an accessible name).
- Director sparkles were already replaced by Clapperboard.

## Remaining for human review

- Command top bar still carries Night panel, language, bell, and search. Spec 4.7 names SimClock, Mode, and unit scope. Extra chrome is from Prompt 2 console tools.
- Architecture layers are same-height cards with a travelling packet; a judge may want drawn pipes between zones.
- Me ledger on a 390 full-page shot is crossed by the fixed tab bar. In use the tabs stay at the bottom while the page scrolls.
- Illustration kit is original line-art SVG. Image-model rasters failed the 2.6 single-weight rule (31.1 has no image-model row).
- Review screenshots were taken against local `next dev` on port 3000. `make dev` is `compose --build` publishing 3000. The compose web container was stuck earlier in this session.

## Prompt 4 live-data review

Touched screens were walked with a signed-in session against a local engine on 8000. Layout, copy, and Direction v3 components are unchanged from Prompt 3. Scores stay at 4 or above. No new after-shots; the visual language did not change.

| Screen | Live check | Notes |
|---|---|---|
| Saathi home | Arjun greeting and nudge from `GET /me/home` | Same ribbon and tiles. |
| Check-in | Questions from `GET /me/check-in`; FaceScale advances | Live questions match the old three-step flow. |
| Me | Consents from `GET /me/consents` | Ledger empty until an access row exists. |
| Welfare queue | Unit-scoped `GET /welfare/queue` | Bn C-02 shows MB-4091 T3 only, not the old four-persona fixture mix. |
| Case workspace | `GET /welfare/cases/MB-4091` | REST_48H still ranks first. |
| Command | `GET /command/posture` | Takeaway and hidden cells unchanged; no case ids. |
| Medical | `GET /medical/acute` | MB-6604 T4 after `POST /acute`. |
| Governance | `GET /gov/kpis` | Same KPI copy. |
| Gallery | fixtures | `/dev/components` still uses `@manobal/contracts` fixtures. |

Welfare queue is thinner than the Prompt 3 fixture board because UWO Sunita only sees Bn C-02. That is the spec, not a Direction v3 miss.

## Prompt 5 companion and voice review

Touched screens: Saathi voice, Architecture, Trust centre. Shots in `e2e/artifacts/ui/p5-*.png` at 390 by 844 and 1440 by 900, light and dark. Axe clean on `/app/saathi` and `/architecture`. Typed Hindi turn on Arjun returned a live companion reply and captions.

| Screen | Focal | MANOBAL | Hierarchy | Copy | Data-viz | Motion | A11y | Video | Round |
|---|---|---|---|---|---|---|---|---|---|
| Saathi voice | 4 | 5 | 4 | 5 | 4 | 4 | 5 | 4 | 2 |
| Architecture | 4 | 4 | 4 | 5 | 4 | 4 | 5 | 4 | 1 |
| Trust centre | 4 | 4 | 4 | 5 | 4 | 4 | 5 | 4 | 1 |

Round 1: two Close controls (shell plus page); captions used Dusk ink and Neem tokens that washed out in dark; keyboard mode had no visible field.

Round 2: dropped the extra Close; captions use `--mb-ink` and `--mb-primary`; keyboard field is 44 px with a theme border.

Section 9.5: the extra in-page Close was removed. The shell Close remains.

Remaining for human review:
- Spec 13.1 demo banner and spec 27.5 hosting caption both show, so the 390 frame is tall.
- On-device preview label appears only after WebGPU. Whisper and WebLLM weights are not vendored; English offline reflect uses the local template.
- Foundry, Deepgram, and Azure Speech were unset. Voice first audio is the silent-WAV fallback. Typed and fixture voice paths are real.

## Prompt 6 personnel surfaces

Touched screens: onboarding, home (Arjun, Meena, Karthik), check-in, Saathi, safety, toolkit, assessments, rest, talk, buddy, plan, family, Me. Shots in `e2e/artifacts/ui/p6-*.png` at 360, 390, and 412.

| Screen | Focal | MANOBAL | Hierarchy | Copy | Data-viz | Motion | A11y | Video | Round |
|---|---|---|---|---|---|---|---|---|---|
| Onboarding | 4 | 5 | 4 | 5 | 4 | 4 | 4 | 4 | 1 |
| Home Arjun | 5 | 5 | 5 | 5 | 5 | 4 | 4 | 5 | 1 |
| Home Meena | 4 | 5 | 4 | 5 | 4 | 4 | 4 | 4 | 1 |
| Home Karthik | 5 | 5 | 5 | 5 | 4 | 4 | 4 | 5 | 1 |
| Check-in | 5 | 5 | 5 | 5 | 4 | 4 | 4 | 5 | 1 |
| Saathi | 4 | 5 | 4 | 5 | 4 | 4 | 4 | 4 | 1 |
| Safety | 5 | 5 | 5 | 5 | 4 | 4 | 4 | 5 | 1 |
| Toolkit | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 1 |
| Assessments | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 1 |
| Rest | 4 | 4 | 4 | 5 | 4 | 4 | 4 | 4 | 1 |
| Talk | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 1 |
| Buddy | 4 | 5 | 4 | 5 | 4 | 4 | 4 | 4 | 1 |
| Plan | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 1 |
| Family | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 1 |
| Me | 4 | 5 | 4 | 5 | 4 | 4 | 4 | 4 | 1 |

Round 1: ScreenState no longer blanks Saathi when a snapshot exists. Safety uses `sms:` and T4 red only on the Tele-MANAS call button. Homes differ by shift, leave window, and Tamil settling-back with Why this? on each context card. Meena home is one leave card so tiles stay on the first screen.

Remaining for human review:
- Me is a long scroll at 360. Simple mode enlarges targets.
- Azure Translator, Speech, ACS, and Content Safety remain unset. Other scheduled languages ship English with a machine-translated flag. Calls show a labelled demo join.
- Toolkit list is long; ranking puts music and sleep first for Arjun.
- Lighthouse 12.8 on the landing page in `next dev`: accessibility 100, performance 41. PWA is no longer a scored category in this Lighthouse version. Production TWA numbers were not taken.

