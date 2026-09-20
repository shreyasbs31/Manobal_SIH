export const PERSONA_IDS = [
  "MB-4091",
  "MB-2217",
  "MB-3380",
  "MB-1506",
  "MB-5120",
  "MB-6604",
  "MB-7342",
  "MB-8815",
] as const;

export type PersonaId = (typeof PERSONA_IDS)[number];

export type FixtureTier = "T0" | "T1" | "T2" | "T3" | "T4";
export type FixtureTrajectory = "rising" | "steady" | "easing";

/** GET /api/v1/me/home */
export interface HomePayload {
  persona_id: PersonaId;
  given_name: string;
  greeting: string;
  shift_line: string;
  takeaway: string;
  checkin: { title: string; duration_s: number; href: string; done?: boolean };
  nudge: { title: string; detail: string; why: string };
  ribbon: readonly { day: number; value: number }[];
  persona?: string;
  simple_mode?: boolean;
  language?: string;
  context_cards?: readonly { title: string; detail: string; why: string; kind: string }[];
  tiles?: readonly { href: string; label: string }[];
  status?: { wearable?: string; last_sync?: string; queued?: number };
  checkin_done?: boolean;
  onboarding_done?: boolean;
  lifecycle_state?: string;
  device_tier?: string;
}

/** GET /api/v1/me/trends */
export interface TrendPoint {
  day: number;
  value: number;
}

/** POST /api/v1/edge/sync check-in item */
export type CheckInQuestion = {
  id: "mood" | "energy" | "sleep";
  prompt: string;
};

/** GET /api/v1/welfare/queue */
export interface WelfareCase {
  case_id: PersonaId;
  subject_token: string;
  tier: FixtureTier;
  trajectory: FixtureTrajectory;
  drivers: readonly string[];
  drift: string;
  sla_label: string;
  remaining_ratio: number;
  lever_id: string;
  lever_title: string;
  limited: boolean;
  source: string;
  status: string;
}

/** GET /api/v1/command/posture */
export interface CommandPosture {
  unit_label: string;
  week: number;
  duty_hours: string;
  rest_denials: string;
  night_load: string;
  leave_backlog: string;
  takeaway: string;
  companies: readonly string[];
  quick_returns?: string;
  median_leave?: string;
  incident_exposure?: string;
  grievance_age?: string;
  sparks?: Record<string, readonly number[]>;
  cells: readonly {
    unit: string;
    week: number;
    band: FixtureTier | "hidden";
    shareLabel?: string | undefined;
  }[];
}

export const arjunHome: HomePayload = {
  persona_id: "MB-4091",
  given_name: "Arjun",
  greeting: "Suprabhat, Arjun",
  shift_line: "Night duty ended at 06:00",
  takeaway: "Your sleep has been below your usual rhythm for 3 nights.",
  checkin: {
    title: "How are you after duty?",
    duration_s: 20,
    href: "/app/check-in",
  },
  nudge: {
    title: "Sleep before tonight's duty",
    detail: "A 20-minute nap plan",
    why: "Roster days are running long this rotation. This is a private nudge.",
  },
  ribbon: [
    { day: 1, value: 6.4 },
    { day: 3, value: 6.2 },
    { day: 5, value: 6.1 },
    { day: 7, value: 5.8 },
    { day: 9, value: 5.4 },
    { day: 11, value: 4.9 },
    { day: 13, value: 4.4 },
    { day: 14, value: 4.2 },
  ],
};

export const checkInQuestions: readonly CheckInQuestion[] = [
  { id: "mood", prompt: "How is your mood right now?" },
  { id: "energy", prompt: "How is your energy right now?" },
  { id: "sleep", prompt: "How was your sleep?" },
];

export const arjunVoice = {
  persona_id: "MB-4091" as const,
  language: "Hindi",
  lines: [
    { speaker: "you" as const, text: "Aaj neend poori nahi hui" },
    {
      speaker: "saathi" as const,
      text: "Raat ki duty ke baad aisa ho sakta hai. Kya aaj thoda aaram mil paaya?",
    },
  ],
  audio_cleared_ms: 84,
  model_caption: "Prototype: open-weight model on Azure",
};

export const mePrivacy = {
  persona_id: "MB-4091" as const,
  statements: [
    "Your commander never sees you",
    "You choose what is shared",
    "You can see every access",
  ],
  consents: [
    {
      title: "Daily check-in",
      leavesPhone: "A short summary of your check-in",
      whoCanSee: "You. A welfare officer only after you agree.",
      on: true,
    },
    {
      title: "Voice conversation",
      leavesPhone: "Nothing. Audio is cleared on the phone.",
      whoCanSee: "Nobody. Captions stay in this session unless you save a journal.",
      on: true,
    },
  ],
  ledger: [
    {
      month: "September 2026",
      items: [
        {
          actor: "Welfare Officer, your unit, viewed your identity",
          purpose: "To call you about rest after long night duty",
          when: "16 Sep 2026",
        },
      ],
    },
  ],
  receipt: {
    hash: "4ab1c0ffee91b3d2",
    time: "16 Sep 2026, 09:12 IST",
  },
  sleep_ribbon: [
    { day: 1, value: 6.2 },
    { day: 15, value: 6.0 },
    { day: 30, value: 5.4 },
    { day: 45, value: 4.8 },
    { day: 60, value: 4.1 },
    { day: 75, value: 3.6 },
    { day: 90, value: 3.4 },
  ] as const,
};

export const welfareQueue: readonly WelfareCase[] = [
  {
    case_id: "MB-6604",
    subject_token: "st_DEEPAK00000001",
    tier: "T4",
    trajectory: "rising",
    drivers: ["Crisis gate"],
    drift: "Acute path opened 3 minutes ago",
    sla_label: "11:42",
    remaining_ratio: 0.12,
    lever_id: "ACUTE_CONTACT",
    lever_title: "Immediate human contact",
    limited: false,
    source: "Independent gates",
    status: "Unacknowledged",
  },
  {
    case_id: "MB-4091",
    subject_token: "st_ARJUN0000000001",
    tier: "T3",
    trajectory: "rising",
    drivers: ["Roster overtime", "Sleep"],
    drift: "Drift began about 20 days ago",
    sla_label: "46:10",
    remaining_ratio: 0.46,
    lever_id: "REST_48H",
    lever_title: "Sanction 48-hour rest",
    limited: false,
    source: "Nightly scoring",
    status: "Open",
  },
  {
    case_id: "MB-7342",
    subject_token: "st_RAJESH000000001",
    tier: "T2",
    trajectory: "steady",
    drivers: ["Leave denial", "Stress"],
    drift: "Drift began about 12 days ago",
    sla_label: "5d 04h",
    remaining_ratio: 0.62,
    lever_id: "GRIEVANCE_EXPEDITE",
    lever_title: "Expedite grievance",
    limited: false,
    source: "Nightly scoring",
    status: "Open",
  },
  {
    case_id: "MB-2217",
    subject_token: "st_MEENA0000000001",
    tier: "T2",
    trajectory: "rising",
    drivers: ["Leave", "Family"],
    drift: "Drift began about 14 days ago",
    sla_label: "4d 11h",
    remaining_ratio: 0.55,
    lever_id: "LEAVE_PRIORITISE",
    lever_title: "Prioritise pending earned leave",
    limited: true,
    source: "Digest",
    status: "Open",
  },
];

export const arjunWorkspace = {
  case: welfareQueue[1]!,
  what_changed: [
    { title: "Roster overtime", detail: "19 days without a rest day" },
    { title: "Sleep loss", detail: "Less sleep than usual" },
  ],
  levers: [
    {
      title: "Sanction 48-hour rest",
      rationale: "Often helpful when duty days stack without a gap.",
      hint: "Draft only. You decide.",
    },
    {
      title: "Rotate off night duty",
      rationale: "Night load is high in Charlie Coy this week.",
      hint: "Needs company agreement.",
    },
    {
      title: "Informal conversation",
      rationale: "A walk, not a summons.",
      hint: "Keep it off the record unless they ask.",
    },
  ],
  brief:
    "Sleep and consecutive duty are both outside his usual range. A 48-hour rest is the first lever. He has not asked for help.",
  strip: Array.from({ length: 24 }, (_, index) => ({
    day: index * 5,
    tier: (index < 8 ? "T0" : index < 14 ? "T1" : index < 20 ? "T2" : "T3") as FixtureTier,
  })),
  onset_day: 100,
  incidents: [118],
  actions: [110],
};

export const medicalAcute = welfareQueue.filter((item) => item.tier === "T4");

export const commandPosture: CommandPosture = {
  unit_label: "Bn C-02",
  week: 38,
  duty_hours: "61",
  rest_denials: "14",
  night_load: "38%",
  leave_backlog: "22 days",
  takeaway: "Charlie Coy's workload has risen for three weeks.",
  companies: ["Alpha Coy", "Bravo Coy", "Charlie Coy", "Delta Coy"],
  cells: ["Alpha Coy", "Bravo Coy", "Charlie Coy", "Delta Coy"].flatMap((unit) =>
    Array.from({ length: 12 }, (_, index) => {
      const week = index + 1;
      const hidden = unit === "Delta Coy" && week > 7;
      const charlieStrain = unit === "Charlie Coy" && week > 8;
      return {
        unit,
        week,
        band: hidden
          ? ("hidden" as const)
          : charlieStrain
            ? ("T2" as const)
            : week > 10
              ? ("T1" as const)
              : ("T0" as const),
        shareLabel: hidden
          ? undefined
          : charlieStrain
            ? "20 to 30%"
            : "under 10%",
      };
    }),
  ),
};

export const governanceOverview = {
  kpis: [
    { label: "Lead time", value: "4.2 d", hint: "Median days from onset to first action" },
    { label: "False-positive rate", value: "0.11", hint: "Alerts with no later corroboration" },
    { label: "Break-glass rate", value: "0.4%", hint: "Identity reveals per open case" },
    { label: "Trust index", value: "Held", hint: "Opt-out does not change scoring" },
    { label: "Ack time T4", value: "3.1 min", hint: "Median until a human acknowledges" },
  ],
  fairness: [
    { label: "Flag rate by rank band", ratio: 0.92 },
    { label: "Flag rate by theatre", ratio: 1.08 },
  ],
};

export const landingRibbon = [
  { day: 1, value: 3.1 },
  { day: 12, value: 3.0 },
  { day: 24, value: 3.3 },
  { day: 36, value: 3.2 },
  { day: 48, value: 4.6 },
  { day: 60, value: 5.4 },
  { day: 72, value: 4.2 },
  { day: 84, value: 3.4 },
] as const;

export const psMapping = [
  ["Personnel Wellness Monitoring Dashboard", "Welfare Console, Command Console, Force HQ"],
  ["Mobile-based Wellness and Self-Assessment Application", "Saathi PWA"],
  [
    "Predictive Behavioral Analytics Engine",
    "Engine (baselines, regimes, CUSUM, change points), Validation Lab",
  ],
  [
    "Stress and Burnout Risk Prediction Models",
    "14-day forecast with calibration and drivers; CBI burnout domain",
  ],
  ["Welfare Intervention Recommendation System", "Lever library, ranking, closed loop, JITAI"],
  [
    "Role-based Access Control and Privacy Management Framework",
    "Roles, grants, vault, Rights Centre, DPO Centre, Trust Centre",
  ],
  ["Automated Alerts for authorized welfare personnel", "Tiered alerts, escalation ladder, acute path"],
  [
    "Data anonymization and secure storage mechanisms",
    "Tokenisation, envelope encryption with Key Vault, k-anonymity, audit chain",
  ],
  ["Secure integration with HRMS", "Integration Console"],
] as const;

export const demoPrincipal = {
  actor_id: "uwo-c02",
  role: "uwo" as const,
  scopes: ["welfare:bn-c-02"],
  scope_path: "bn-c-02",
  synthetic: true,
};
