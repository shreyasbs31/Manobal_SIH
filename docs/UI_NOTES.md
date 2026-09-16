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
| Landing |  |  |  |  |  |  |  |  |  |
| Saathi home |  |  |  |  |  |  |  |  |  |
| Check-in |  |  |  |  |  |  |  |  |  |
| Saathi voice |  |  |  |  |  |  |  |  |  |
| Safety |  |  |  |  |  |  |  |  |  |
| Breathing |  |  |  |  |  |  |  |  |  |
| Me |  |  |  |  |  |  |  |  |  |
| Welfare queue |  |  |  |  |  |  |  |  |  |
| Case workspace |  |  |  |  |  |  |  |  |  |
| Medical acute |  |  |  |  |  |  |  |  |  |
| Command posture |  |  |  |  |  |  |  |  |  |
| Governance |  |  |  |  |  |  |  |  |  |
| Architecture |  |  |  |  |  |  |  |  |  |
| Stage |  |  |  |  |  |  |  |  |  |

Fill after screenshots. Any cell below 4 gets a fix note in "Fixes" below.

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

Round notes go here after the first after-screenshots.
