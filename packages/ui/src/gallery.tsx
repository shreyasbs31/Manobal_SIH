"use client";

import { useMemo, useState, type ReactNode } from "react";

import {
  AudioClearedChip,
  DomainChip,
  DriverList,
  EmptyState,
  ErrorState,
  LimitedDataTag,
  MachineTranslatedBadge,
  ModeChip,
  OfflineChip,
  ProviderBadge,
  SimClock,
  SyncQueueIndicator,
  TierBadge,
  TrajectoryArrow,
  ValidatedBadge,
} from "./badges";
import {
  BaselineRibbonChart,
  FairnessBar,
  FormationGrid,
  HiddenTile,
  ReliabilityChart,
} from "./charts";
import { CaptionStream, CallPanel, PhoneFrame, SOSButton, VoiceOrb, ZoneDiagram } from "./companion";
import { VoiceContour } from "./voice-contour";
import {
  EmojiScale,
  FaceScale,
  LanguageGrid,
  LeaveWindowPicker,
  SafetyPlanEditor,
  ShiftTimeline,
} from "./forms";
import {
  IconBuddyPair,
  IconEdgeQueue,
  IconHiddenLock,
  IconLayRibbon,
  IconLeaveWindow,
  IconShiftMoon,
  IconVaultKey,
  IconVoiceContour,
  TierGlyph,
} from "./icons";
import { PublicHeader } from "./shells";
import { ThemeRoot } from "./theme-root";
import type { Skin, ThemeName, TierId } from "./types";
import { COMPONENT_REGISTRY } from "./types";
import {
  AccessLedgerItem,
  AuditRow,
  BriefPanel,
  CaseCard,
  CaseStrip,
  ChainStatus,
  ConsentToggleCard,
  EscalationLadder,
  KpiTile,
  LeverOption,
  ReceiptCard,
  SlaTimer,
} from "./workflow";

const THEMES: readonly { skin: Skin; theme: ThemeName; label: string }[] = [
  { skin: "saathi", theme: "light", label: "Saathi light" },
  { skin: "saathi", theme: "dark", label: "Saathi dark" },
  { skin: "saathi", theme: "hc", label: "Saathi high contrast" },
  { skin: "command", theme: "dark", label: "Command dark" },
  { skin: "command", theme: "light", label: "Command light" },
];

const RIBBON: readonly { day: number; value: number }[] = [
  { day: 1, value: 3.1 },
  { day: 8, value: 3.0 },
  { day: 15, value: 3.2 },
  { day: 22, value: 2.9 },
  { day: 29, value: 3.4 },
  { day: 36, value: 3.6 },
  { day: 43, value: 4.8 },
  { day: 50, value: 5.4 },
  { day: 57, value: 6.1 },
  { day: 64, value: 5.8 },
];

const LANGUAGES = [
  { tag: "as", label: "অসমীয়া", direction: "ltr" },
  { tag: "bn", label: "বাংলা", direction: "ltr" },
  { tag: "brx", label: "बड़ो", direction: "ltr" },
  { tag: "doi", label: "डोगरी", direction: "ltr" },
  { tag: "gu", label: "ગુજરાતી", direction: "ltr" },
  { tag: "hi", label: "हिन्दी", direction: "ltr" },
  { tag: "kn", label: "ಕನ್ನಡ", direction: "ltr" },
  { tag: "ks", label: "کٲشُر", direction: "rtl" },
  { tag: "kok", label: "कोंकणी", direction: "ltr" },
  { tag: "mai", label: "मैथिली", direction: "ltr" },
  { tag: "ml", label: "മലയാളം", direction: "ltr" },
  { tag: "mni", label: "মৈতৈলোন্", direction: "ltr" },
  { tag: "mr", label: "मराठी", direction: "ltr" },
  { tag: "ne", label: "नेपाली", direction: "ltr" },
  { tag: "or", label: "ଓଡ଼ିଆ", direction: "ltr" },
  { tag: "pa", label: "ਪੰਜਾਬੀ", direction: "ltr" },
  { tag: "sa", label: "संस्कृतम्", direction: "ltr" },
  { tag: "sat", label: "ᱥᱟᱱᱛᱟᱲᱤ", direction: "ltr" },
  { tag: "sd", label: "سنڌي", direction: "rtl" },
  { tag: "ta", label: "தமிழ்", direction: "ltr" },
  { tag: "te", label: "తెలుగు", direction: "ltr" },
  { tag: "ur", label: "اردو", direction: "rtl" },
  { tag: "en", label: "English", direction: "ltr" },
] as const;

function formationCells() {
  const units = ["Company A", "Company B", "Company C", "Company D"];
  const cells = [];
  for (const unit of units) {
    for (let week = 1; week <= 12; week += 1) {
      const hidden = unit === "Company D" && week > 8;
      cells.push({
        unit,
        week,
        band: hidden
          ? "hidden"
          : week > 9
            ? "T2"
            : week > 6
              ? "T1"
              : "T0",
      } as const);
    }
  }
  return { units, cells };
}

export function ComponentGallery() {
  const [pairIndex, setPairIndex] = useState(0);
  const [mood, setMood] = useState(3);
  const [language, setLanguage] = useState("hi");
  const [consent, setConsent] = useState(false);
  const pair = THEMES[pairIndex] ?? THEMES[0]!;
  const formation = useMemo(() => formationCells(), []);

  return (
    <ThemeRoot className="mb-gallery" skin={pair.skin} theme={pair.theme}>
      <a className="mb-skip" href="#gallery-main">
        Skip to components
      </a>
      <PublicHeader />
      <main className="mb-gallery-grid" id="gallery-main">
        <h1>Component gallery</h1>
        <div aria-label="Skin and theme" className="mb-gallery-toolbar" role="toolbar">
          <p className="mb-chip">Demo only</p>
          {THEMES.map((item, index) => (
            <button
              aria-pressed={index === pairIndex}
              className="mb-secondary"
              key={item.label}
              onClick={() => setPairIndex(index)}
              type="button"
            >
              {item.label}
            </button>
          ))}
        </div>
        <p>
          Showing {pair.label}. Every component below keeps its label and shape, not colour
          alone.
        </p>
        <GalleryItem name="TierBadge">
          <div className="mb-action-row">
            {(["T0", "T1", "T2", "T3", "T4"] as const).map((tier: TierId) => (
              <TierBadge key={tier} tier={tier} />
            ))}
          </div>
          <div className="mb-action-row">
            {(["T0", "T1", "T2", "T3", "T4"] as const).map((tier) => (
              <TierGlyph key={`g-${tier}`} tier={tier} />
            ))}
            <IconLayRibbon width={24} height={24} />
            <IconVoiceContour width={24} height={24} />
            <IconHiddenLock width={24} height={24} />
            <IconEdgeQueue width={24} height={24} />
            <IconVaultKey width={24} height={24} />
            <IconBuddyPair width={24} height={24} />
            <IconLeaveWindow width={24} height={24} />
            <IconShiftMoon width={24} height={24} />
          </div>
        </GalleryItem>
        <GalleryItem name="TrajectoryArrow">
          <div className="mb-action-row">
            <TrajectoryArrow direction="rising" />
            <TrajectoryArrow direction="steady" />
            <TrajectoryArrow direction="easing" />
          </div>
        </GalleryItem>
        <GalleryItem name="LimitedDataTag">
          <LimitedDataTag />
        </GalleryItem>
        <GalleryItem name="DomainChip">
          <div className="mb-action-row">
            <DomainChip label="Sleep" />
            <DomainChip label="Roster" />
            <DomainChip label="Family" />
          </div>
        </GalleryItem>
        <GalleryItem name="DriverList">
          <DriverList items={["Roster overtime", "Sleep loss", "Leave backlog"]} />
        </GalleryItem>
        <GalleryItem name="BaselineRibbonChart">
          <BaselineRibbonChart label="Mood, 90 days" values={RIBBON} />
        </GalleryItem>
        <GalleryItem name="FormationGrid">
          <FormationGrid cells={formation.cells} units={formation.units} weeks={12} />
        </GalleryItem>
        <GalleryItem name="HiddenTile">
          <HiddenTile reason="Hidden: group too small to show" />
        </GalleryItem>
        <GalleryItem name="SlaTimer">
          <SlaTimer label="Acknowledge" remainingLabel="12:40" urgent />
        </GalleryItem>
        <GalleryItem name="EscalationLadder">
          <EscalationLadder
            current="Call"
            steps={["Acknowledge", "Call", "Hand off", "Outcome"]}
          />
        </GalleryItem>
        <GalleryItem name="CaseCard">
          <CaseCard
            caseId="Case 7F2A"
            domains={["Sleep", "Roster"]}
            drift="Drift began about 18 days ago"
            lever="Rest day restoration"
            limited
            sla="04:10"
            source="Nightly scoring"
            status="Open"
            tier="T3"
            trajectory="rising"
          />
        </GalleryItem>
        <GalleryItem name="CaseStrip">
          <CaseStrip
            days={[
              { day: 1, tier: "T0" },
              { day: 40, tier: "T1" },
              { day: 80, tier: "T3" },
              { day: 120, tier: "T3" },
            ]}
            onsetDay={40}
            incidents={[90]}
            actions={[100]}
          />
        </GalleryItem>
        <GalleryItem name="LeverOption">
          <LeverOption
            hint="Often helpful in similar situations"
            rationale="Consecutive duty days are above the unit baseline."
            title="Restore a rest day"
          />
        </GalleryItem>
        <GalleryItem name="BriefPanel">
          <BriefPanel>
            <p>
              Contributing:{" "}
              <dfn title="field: roster.overtime_days">Roster overtime</dfn>,{" "}
              <dfn title="field: sleep.hours">Sleep loss</dfn>.
            </p>
          </BriefPanel>
        </GalleryItem>
        <GalleryItem name="ConsentToggleCard">
          <ConsentToggleCard
            checked={consent}
            leavesPhone="Encrypted check-in summary"
            onChange={setConsent}
            title="Daily check-in"
            whoCanSee="You, and a welfare officer only after you agree"
          />
        </GalleryItem>
        <GalleryItem name="ReceiptCard">
          <ReceiptCard hash="sha256:9c2a…e81" time="16 Sep 2026, 10:04 IST" />
        </GalleryItem>
        <GalleryItem name="AccessLedgerItem">
          <AccessLedgerItem
            actor="Welfare officer (token only)"
            purpose="Follow-up after consent"
            when="16 Sep 2026"
          />
        </GalleryItem>
        <GalleryItem name="AuditRow">
          <AuditRow action="grant.created" token="tok_4c19" when="10:04" />
        </GalleryItem>
        <GalleryItem name="ChainStatus">
          <ChainStatus intact />
        </GalleryItem>
        <GalleryItem name="KpiTile">
          <KpiTile
            hint="Unit aggregate, k-anonymous"
            label="Median days since leave"
            value="46"
          />
        </GalleryItem>
        <GalleryItem name="FairnessBar">
          <FairnessBar label="Flag rate by rank band" ratio={0.94} />
        </GalleryItem>
        <GalleryItem name="ReliabilityChart">
          <ReliabilityChart
            points={[
              { predicted: 0.2, observed: 0.18 },
              { predicted: 0.5, observed: 0.47 },
              { predicted: 0.8, observed: 0.74 },
            ]}
          />
        </GalleryItem>
        <GalleryItem name="PhoneFrame">
          <PhoneFrame>
            <div style={{ padding: 16 }}>
              <p>Saathi home lives in this frame on the stage.</p>
            </div>
          </PhoneFrame>
        </GalleryItem>
        <GalleryItem name="OfflineChip">
          <OfflineChip offline={false} />
          <OfflineChip offline />
        </GalleryItem>
        <GalleryItem name="SyncQueueIndicator">
          <SyncQueueIndicator count={2} />
        </GalleryItem>
        <GalleryItem name="AudioClearedChip">
          <AudioClearedChip />
        </GalleryItem>
        <GalleryItem name="VoiceOrb">
          <VoiceOrb state="listening" />
        </GalleryItem>
        <GalleryItem name="VoiceContour">
          <VoiceContour amplitude={0.5} seed="MB-4091" state="listening" />
        </GalleryItem>
        <GalleryItem name="CaptionStream">
          <CaptionStream
            language="Hindi"
            lines={["Aap kaise hain aaj?", "You have been on duty 11 days in a row."]}
          />
        </GalleryItem>
        <GalleryItem name="SOSButton">
          <SOSButton />
        </GalleryItem>
        <GalleryItem name="EmojiScale">
          <EmojiScale label="Mood" onChange={setMood} value={mood} />
        </GalleryItem>
        <GalleryItem name="FaceScale">
          <FaceScale label="Mood" onChange={setMood} value={mood} />
        </GalleryItem>
        <GalleryItem name="LanguageGrid">
          <LanguageGrid
            languages={LANGUAGES}
            onChange={setLanguage}
            value={language}
          />
        </GalleryItem>
        <GalleryItem name="ValidatedBadge">
          <ValidatedBadge />
        </GalleryItem>
        <GalleryItem name="MachineTranslatedBadge">
          <MachineTranslatedBadge />
        </GalleryItem>
        <GalleryItem name="ModeChip">
          <ModeChip mode="demo" />
        </GalleryItem>
        <GalleryItem name="SimClock">
          <SimClock value="2026-09-16 10:00 IST" />
        </GalleryItem>
        <GalleryItem name="EmptyState">
          <EmptyState />
        </GalleryItem>
        <GalleryItem name="ErrorState">
          <ErrorState />
        </GalleryItem>
        <GalleryItem name="ProviderBadge">
          <ProviderBadge name="Azure Speech" />
        </GalleryItem>
        <GalleryItem name="ZoneDiagram">
          <ZoneDiagram />
        </GalleryItem>
        <GalleryItem name="CallPanel">
          <CallPanel peer="Counsellor" status="Waiting in the private room" />
        </GalleryItem>
        <GalleryItem name="SafetyPlanEditor">
          <SafetyPlanEditor />
        </GalleryItem>
        <GalleryItem name="LeaveWindowPicker">
          <LeaveWindowPicker />
        </GalleryItem>
        <GalleryItem name="ShiftTimeline">
          <ShiftTimeline
            days={[
              { label: "Mon", start: 10, end: 70 },
              { label: "Tue", start: 40, end: 90 },
              { label: "Wed", start: 0, end: 40 },
            ]}
          />
        </GalleryItem>
        <GalleryItem name="CommandPalette">
          <p>Press Control K on any command console to open the palette.</p>
        </GalleryItem>
        <p className="mb-chip">Registry {COMPONENT_REGISTRY.length} components</p>
      </main>
    </ThemeRoot>
  );
}

function GalleryItem({
  name,
  children,
}: {
  name: string;
  children: ReactNode;
}) {
  return (
    <section className="mb-gallery-item mb-card" data-component={name}>
      <h2>{name}</h2>
      {children}
    </section>
  );
}
