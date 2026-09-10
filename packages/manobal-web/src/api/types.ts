export type Role =
  | "personnel"
  | "welfare_officer"
  | "medical_officer"
  | "commander"
  | "wdec_auditor"
  | "integration";

export type Session = {
  token: string;
  role: Role;
  actorId: string;
  subjectToken: string;
  unitCode: string;
};

export type ConsentState = {
  subject_token: string;
  consents: Record<string, boolean | null>;
};

export type Assessment = {
  tier: string | null;
  contributing_categories: string[];
  assessed_at?: string;
  acute_override?: boolean;
};

export type Checkin = {
  observed_on: string | null;
  mood: number | null;
  sleep_quality: number | null;
  stress: number | null;
  connection: number | null;
  concern_tag?: string;
};

export type CaseSummary = {
  id: number;
  subject_token: string;
  tier: string;
  contributing_categories: string[];
  status: string;
  sla_due_at: string;
  opened_at: string;
};

export type Recommendation = {
  code: string;
  rationale: string;
  priority: number;
  accepted: boolean | null;
};

export type CaseDetail = CaseSummary & {
  first_contact_at: string | null;
  closed_at: string | null;
  outcome_code: string;
  officer_rationale: string;
  contested_at: string | null;
  contest_note: string;
  recommendations: Recommendation[];
};

export type JournalEntry = {
  id: number;
  created_at: string;
  body: string;
  crisis_referred: boolean;
};

export type InstrumentCatalogue = {
  code: string;
  version: string;
  language: string;
  stem: string;
  items: string[];
  options: string[];
  launch: { title: string; body: string; acute: string };
};

export type InstrumentHistory = {
  code: string;
  completed_at: string;
  total: number;
  acute: boolean;
};

export type OwnCase = {
  id: number;
  tier: string;
  status: string;
  contributing_categories: string[];
  contested_at: string | null;
};

export type DisclosureRow = {
  id: number;
  case_id: number;
  category: string;
  rationale: string;
  expires_at: string;
  responded_at: string | null;
  granted: boolean | null;
};

export type PairedDevice = {
  id: number;
  device_id: string;
  paired_at: string;
  revoked_at: string | null;
};

export type FairnessReport = {
  unit: string;
  k_threshold: number;
  cells: Array<{
    rank_band: string;
    suppressed: boolean;
    elevated_band?: string;
    dominant_category?: string;
  }>;
};

export type AuditRow = {
  id: number;
  occurred_at: string;
  actor_role: string;
  action: string;
  purpose_code: string;
  outcome: string;
  subject_token: string;
  detail: Record<string, unknown>;
};

export type TrendPoint = {
  assessed_at: string;
  tier_visible: boolean;
  present: boolean;
};

export type Aggregate = {
  unit: string;
  period_start: string;
  period_end: string;
  suppressed: boolean;
  elevated_band?: string;
  dominant_category?: string;
  trend_direction?: string;
};

export type ResolvedIdentity = {
  service_no: string;
  full_name: string;
  rank_code: string;
  mobile_e164: string;
  unit_code: string;
  force_code: string;
};

export type BreakGlassGrant = {
  id: number;
  grantee_id: string;
  justification: string;
  granted_at: string;
  case_id: number | null;
};

export type Anchor = {
  anchored_at: string;
  head_hash: string;
  event_count: number;
  published_to: string;
};

export type RulesetProposal = {
  id: number;
  version: string;
  digest: string;
  status: string;
  clinical_approver: string;
  wdec_approver: string;
  proposed_at: string;
};

export type AgentTurn = {
  session_id: string;
  reply: string;
  crisis: boolean;
  accepted: boolean;
};
