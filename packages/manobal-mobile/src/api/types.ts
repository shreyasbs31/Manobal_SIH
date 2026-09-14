export type Assessment = {
  tier: string | null;
  contributing_categories: string[];
  why?: Array<{ category: string; meaning: string }>;
  offer_checkin?: boolean;
  incident_category?: string;
};

export type InsightNote = {
  field: string;
  direction: string;
  text: string;
};

export type InsightAction = {
  id: string;
  title: string;
  detail: string;
  href: string;
};

export type Insights = {
  lede: string;
  notes: InsightNote[];
  why: Array<{ category: string; meaning: string }>;
  settled_low: boolean;
  settled_message: string;
  engine_note: string;
  streak: number;
  next: InsightAction[];
};

export type Checkin = {
  observed_on: string | null;
  mood: number | null;
  sleep_quality: number | null;
  stress: number | null;
  fatigue: number | null;
  connection: number | null;
  concern_tag?: string;
  picture_changed?: boolean;
  previous_tier?: string | null;
  tier?: string | null;
  insights?: Insights;
};

export type ConsentState = {
  subject_token: string;
  consents: Record<string, boolean | null>;
};

export type HelplineCard = {
  helplines: Record<string, string>;
  recorded: false;
};

export type JournalEntry = {
  id: number;
  created_at: string;
  body: string;
  crisis_referred: boolean;
};

export type AgentTurn = {
  session_id: string;
  reply: string;
  crisis: boolean;
  accepted: boolean;
};

export type OwnTrends = {
  checkins: Array<{
    observed_on: string;
    mood: number | null;
    sleep_quality: number | null;
    fatigue: number | null;
  }>;
};

export type SeedInfo = {
  personnel_token: string;
  unit_code: string;
  llm_configured?: boolean;
};

export type AudioPart = {
  uri: string;
  name: string;
  type: string;
  language?: string;
};
