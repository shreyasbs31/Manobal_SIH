export type Skin = "saathi" | "command";
export type ThemeName = "light" | "dark" | "hc";
export type TierId = "T0" | "T1" | "T2" | "T3" | "T4";
export type Trajectory = "rising" | "steady" | "easing";
export type ManobalMode = "demo" | "sovereign";

export const TIER_LABELS: Record<TierId, string> = {
  T0: "Steady",
  T1: "Watch",
  T2: "Elevated",
  T3: "High",
  T4: "Acute",
};

export const COMPONENT_REGISTRY = [
  "TierBadge",
  "TrajectoryArrow",
  "LimitedDataTag",
  "DomainChip",
  "DriverList",
  "BaselineRibbonChart",
  "FormationGrid",
  "HiddenTile",
  "SlaTimer",
  "EscalationLadder",
  "CaseCard",
  "LeverOption",
  "BriefPanel",
  "ConsentToggleCard",
  "ReceiptCard",
  "AccessLedgerItem",
  "AuditRow",
  "ChainStatus",
  "KpiTile",
  "FairnessBar",
  "ReliabilityChart",
  "PhoneFrame",
  "OfflineChip",
  "SyncQueueIndicator",
  "AudioClearedChip",
  "VoiceOrb",
  "CaptionStream",
  "SOSButton",
  "EmojiScale",
  "LanguageGrid",
  "ValidatedBadge",
  "MachineTranslatedBadge",
  "ModeChip",
  "StatusChip",
  "SimClock",
  "EmptyState",
  "ErrorState",
  "ProviderBadge",
  "ZoneDiagram",
  "CallPanel",
  "SafetyPlanEditor",
  "LeaveWindowPicker",
  "ShiftTimeline",
  "FaceScale",
  "CaseStrip",
  "VoiceContour",
] as const;

export type ComponentName = (typeof COMPONENT_REGISTRY)[number];
