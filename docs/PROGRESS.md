# Progress

## Prompt 3: UI Direction v3 upgrade

Upgrade Prompt 2 shells to UI Direction v3 so later screens inherit a distinctive, video-ready look.

Choices implied by the spec (recorded, not blocked):
- Command light is Survey paper from UI 2.1 (`#EEF1EB` / `#F8FAF6` / brass `#8F6F1E`), not the Prompt 2 parchment.
- `FaceScale` replaces emoji faces; `EmojiScale` keeps the registry name and renders `FaceScale`.
- `VoiceContour` replaces the orb; `VoiceOrb` stays as a thin alias so the 16.6 registry still resolves.
- Generated OpenAPI in `packages/contracts` is still a skeleton. Fixture types live in `packages/contracts/src/ui-fixtures.ts` using spec 19 field names and persona 29 ids, so screens consume contract-shaped data before those routes exist.
- Illustration generation: Cursor image model, then clean SVG. If an output fails the banned list, ship original line-art SVG in the UI 2.6 style (31.1 has no image-model row).
- `make dev` is the one workflow: compose `--build`, web on port 3000.

1. [x] Audit current UI against UI direction 0 and 8; write `docs/UI_NOTES.md` with before screenshots in `e2e/artifacts/ui/`. Check: notes file lists findings per screen; `before-*.png` exist for landing, home, saathi, toolkit, me, welfare, command, medical, stage, gallery. Governance and architecture before frames follow with the capture script.
2. Replace colour, elevation, radius, spacing, and motion tokens with UI 2.1, 2.3, 2.7; add Survey paper; keep contrast tests and extend glyphs 3:1 and text 4.5:1 for every theme. Check: `pnpm --filter @manobal/ui test` contrast suite passes including survey paper.
3. Configure Anek width-axis roles (expanded 112, normal 100, condensed 75) and the 2.2 scale; Devanagari line-height 1.7; no monospace in UI (YAML in Governance excepted). Check: `fonts.ts` loads `wdth`; CSS has no `monospace` / `ui-monospace` outside `.mb-yaml`; `html[lang="hi"]` line-height 1.7.
4. Seeded contour SVG generator (simplex plus marching squares) and Command map grid (2.4); seed from a stable per-user value. Check: unit tests prove same seed same paths, different seed different paths; home and rail render texture only where 2.4 allows.
5. Tier glyph set and custom icons in 2.5 (Lay ribbon, voice contour, hidden lock, edge queue, vault key, buddy pair, leave window, shift moon). Check: gallery shows five distinct stroked glyphs; custom icons export from `@manobal/ui`.
6. Rebuild `BaselineRibbonChart` as the Lay ribbon (hero, detail, empty); `VoiceContour` canvas states from amplitude; `FormationGrid` as a map sheet with references, banded cells, hidden hatch, lock, tooltip, selection. Check: gallery plus unit tests for MAD band, hidden hatch, and four voice states.
7. Rebuild `CaseCard` and add `CaseStrip`, `SlaTimer`, `EscalationLadder`, `FaceScale` (five SVG faces), `ConsentCard`, `ReceiptCard`, `AccessLedgerItem`, `ChainStatus` (verify, tamper, heal), status chips (3.9). Check: gallery headings exist for each; SLA colour rules covered by a unit test.
8. Create `packages/illustrations` with typed slots for the 14 scenes in 2.6; generate, clean to SVG, review against the banned list. Check: 14 exports typecheck; banned-list review is in `docs/UI_NOTES.md`; no raster stock images shipped.
9. Named motions and orchestrated moments from 2.7 as reusable hooks, with reduced-motion fallbacks. Check: hooks module exports every named token; reduced-motion test asserts opacity-only fallback.
10. Sound and haptics utilities (2.8) with settings (sound off by default). Check: unit test that sound is off until enabled; vibrate helpers no-op when unsupported.
11. Restyle Saathi shell (4.1) and Command shell (4.7); status strip per 3.9. Check: SOS is a 48 px ring; Saathi chips are only Offline, Syncing, Demo; Command top bar has SimClock, Mode, unit scope.
12. Rebuild landing to 4.15 (animated Lay ribbon hero, role doors, sourced figures, second-fold mapping table). Check: hero copy matches 4.15; mapping rows match spec 26.2.
13. Rebuild stage to 4.16 (1920 by 1080, recording top bar, Director drawer hidden until toggled). Check: top bar 44 px; drawer not in the default screenshot.
14. Static fixture-driven screens: Saathi home, check-in, voice, safety, breathing, Me, Welfare queue, case workspace, Medical acute, Command posture, Governance, Architecture. Fixtures match contracts and persona 29. Check: each route renders persona ids from spec 29; axe clean on each.
15. Run the UI direction 9 review loop on all of the above; score in `docs/UI_NOTES.md`; fix anything below 4 (max three rounds). Check: every step-14 screen scores at least 4 on every rubric line; after screenshots in `e2e/artifacts/ui/`.
16. `make dev` serves web on port 3000 and rebuilds the image when Dockerfiles or lockfiles change; add `make lint`. Check: `Makefile` `dev` target publishes 3000; `make lint` runs package lints.

End-of-prompt gate: `make test`, `make lint`, `copy-lint`, UI review loop, both skins and all themes render, axe clean.
