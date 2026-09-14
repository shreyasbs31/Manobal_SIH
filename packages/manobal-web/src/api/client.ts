import type {
  AgentTurn,
  Aggregate,
  Anchor,
  Assessment,
  AuditRow,
  BreakGlassGrant,
  CaseDetail,
  CaseSummary,
  Checkin,
  ConsentLedgerEntry,
  ConsentState,
  DisclosureRow,
  ErasureReceipt,
  FairnessReport,
  HelplineCard,
  InstrumentCatalogue,
  InstrumentHistory,
  Insights,
  JournalEntry,
  OfficerDestination,
  OwnCase,
  OwnTrends,
  PairedDevice,
  ResolvedIdentity,
  RulesetProposal,
  Session,
  TrendPoint,
} from "./types";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, detail: string) {
    super(detail);
    this.status = status;
    this.code = code;
  }
}

export function createClient(session: Session | null) {
  const headers = (): HeadersInit => {
    const next: Record<string, string> = { Accept: "application/json" };
    if (session?.token) {
      next.Authorization = `Bearer ${session.token}`;
    }
    return next;
  };

  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const response = await fetch(path, {
      ...init,
      headers: { ...headers(), ...(init.headers ?? {}), "Content-Type": "application/json" },
    });
    const body: unknown = await response.json().catch(() => ({}));
    if (!response.ok) {
      const problem = asRecord(body);
      throw new ApiError(
        response.status,
        String(problem.code ?? `MB-${response.status}0`),
        String(problem.detail ?? response.statusText),
      );
    }
    return body as T;
  }

  return {
    consent: () => request<ConsentState>("/v1/me/consent"),
    consentLedger: () => request<{ entries: ConsentLedgerEntry[] }>("/v1/me/consent/ledger"),
    setConsent: (data_type: string, granted: boolean) =>
      request("/v1/me/consent", { method: "POST", body: JSON.stringify({ data_type, granted }) }),
    assessment: () => request<Assessment>("/v1/me/assessment"),
    insights: () => request<Insights>("/v1/me/insights"),
    trends: () => request<OwnTrends>("/v1/me/trends"),
    helpline: () =>
      request<HelplineCard>("/v1/me/helpline", { method: "POST", body: "{}" }),
    requestErasure: (data_type?: string) =>
      request<ErasureReceipt>("/v1/me/erasure", {
        method: "POST",
        body: JSON.stringify(data_type ? { data_type } : {}),
      }),
    erasure: () => request<{ requests: ErasureReceipt[] }>("/v1/me/erasure"),
    checkin: () => request<Checkin>("/v1/me/checkin"),
    submitCheckin: (payload: Omit<Checkin, "observed_on">) =>
      request<Checkin>("/v1/me/checkin", { method: "POST", body: JSON.stringify(payload) }),
    sos: () => request<{ accepted: true }>("/v1/me/sos", { method: "POST", body: "{}" }),
    agent: (message: string, session_id?: string) =>
      request<AgentTurn>("/v1/me/agent", {
        method: "POST",
        body: JSON.stringify({ message, session_id }),
      }),
    queue: () => request<{ cases: CaseSummary[] }>("/v1/officer/queue"),
    officerDestination: () => request<OfficerDestination>("/v1/officer/destination"),
    setOfficerDestination: (payload: { duty_phone_e164?: string; push_token?: string }) =>
      request<OfficerDestination>("/v1/officer/destination", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    caseDetail: (id: number) => request<CaseDetail>(`/v1/officer/cases/${id}`),
    contact: (id: number) =>
      request<CaseDetail>(`/v1/officer/cases/${id}/contact`, { method: "POST", body: "{}" }),
    decide: (id: number, outcome_code: string, rationale: string, status: string) =>
      request<CaseDetail>(`/v1/officer/cases/${id}/decision`, {
        method: "POST",
        body: JSON.stringify({ outcome_code, rationale, status }),
      }),
    resolve: async (id: number): Promise<ResolvedIdentity> => {
      const identity = await request<ResolvedIdentity>(`/v1/officer/cases/${id}/resolve`, {
        method: "POST",
        body: "{}",
      });
      return identity;
    },
    aggregates: (unit: string) =>
      request<Aggregate>(`/v1/commander/aggregates?unit=${encodeURIComponent(unit)}`),
    breakGlass: () => request<{ grants: BreakGlassGrant[] }>("/v1/wdec/break-glass"),
    anchors: () => request<{ anchors: Anchor[] }>("/v1/wdec/anchors"),
    rulesets: () => request<{ proposals: RulesetProposal[] }>("/v1/wdec/rulesets"),
    proposeRuleset: (payload: {
      version: string;
      digest: string;
      signature: string;
      signing_key_id: string;
    }) => request("/v1/wdec/rulesets", { method: "POST", body: JSON.stringify(payload) }),
    approveRuleset: (id: number, clinical: boolean) =>
      request(
        clinical ? `/v1/clinical/rulesets/${id}/approve` : `/v1/wdec/rulesets/${id}/approve`,
        { method: "POST", body: "{}" },
      ),
    journal: () => request<{ entries: JournalEntry[]; paused?: boolean }>("/v1/me/journal"),
    writeJournal: (body: string, crisis_accepted = false, retain = true) =>
      request<JournalEntry>("/v1/me/journal", {
        method: "POST",
        body: JSON.stringify({ body, crisis_accepted, retain }),
      }),
    deleteJournal: (id: number) =>
      request<undefined>(`/v1/me/journal/${id}`, { method: "DELETE", body: "{}" }),
    instrumentCatalogue: (code: string, lang: string) =>
      request<InstrumentCatalogue>(
        `/v1/me/instruments/catalogue?code=${encodeURIComponent(code)}&lang=${encodeURIComponent(lang)}`,
      ),
    instruments: () => request<{ history: InstrumentHistory[] }>("/v1/me/instruments"),
    submitInstrument: (code: string, language: string, answers: number[], duration_seconds?: number) =>
      request<{ code: string; total: number; acute: boolean; straight_lined: boolean }>(
        "/v1/me/instruments",
        {
          method: "POST",
          body: JSON.stringify({ code, language, answers, duration_seconds }),
        },
      ),
    myCases: () => request<{ cases: OwnCase[] }>("/v1/me/cases"),
    contestCase: (id: number, note: string) =>
      request<{ id: number; status: string }>(`/v1/me/cases/${id}/contest`, {
        method: "POST",
        body: JSON.stringify({ note }),
      }),
    disclosures: () => request<{ requests: DisclosureRow[] }>("/v1/me/disclosures"),
    answerDisclosure: (id: number, granted: boolean) =>
      request<DisclosureRow>(`/v1/me/disclosures/${id}`, {
        method: "POST",
        body: JSON.stringify({ granted }),
      }),
    devices: () => request<{ devices: PairedDevice[] }>("/v1/me/devices"),
    pairDevice: (device_id: string, public_key: string) =>
      request<PairedDevice>("/v1/me/devices", {
        method: "POST",
        body: JSON.stringify({ device_id, public_key }),
      }),
    revokeDevice: (id: number) =>
      request<PairedDevice>(`/v1/me/devices/${id}/revoke`, { method: "POST", body: "{}" }),
    requestDisclosure: (id: number, category: string, rationale: string) =>
      request<{ id: number; category: string; expires_at: string; granted: boolean | null }>(
        `/v1/officer/cases/${id}/disclosure`,
        { method: "POST", body: JSON.stringify({ category, rationale }) },
      ),
    categoryTrend: (id: number, category: string) =>
      request<{ category: string; points: TrendPoint[] }>(
        `/v1/officer/cases/${id}/trend?category=${encodeURIComponent(category)}`,
      ),
    referClinical: (id: number, medical_actor_id: string, rationale: string) =>
      request<{ grant_id: number; scope: string; assigned: false }>(
        `/v1/officer/cases/${id}/refer-clinical`,
        { method: "POST", body: JSON.stringify({ medical_actor_id, rationale }) },
      ),
    clinicalQueue: () => request<{ cases: CaseSummary[] }>("/v1/clinical/queue"),
    fairness: (unit: string) =>
      request<FairnessReport>(`/v1/wdec/fairness?unit=${encodeURIComponent(unit)}`),
    audit: () => request<{ events: AuditRow[] }>("/v1/wdec/audit"),
    invokeBreakGlass: (case_id: number, justification: string, second_approver_id: string) =>
      request<ResolvedIdentity>("/v1/wdec/break-glass", {
        method: "POST",
        body: JSON.stringify({ case_id, justification, second_approver_id }),
      }),
    reviewBreakGlass: (id: number) =>
      request<{ id: number; wdec_reviewed_at: string }>(`/v1/wdec/break-glass/${id}/review`, {
        method: "POST",
        body: "{}",
      }),
  };
}

export async function mintDevToken(input: {
  role: string;
  actor_id: string;
  unit_code: string;
  subject_token?: string;
}): Promise<{ token: string; role: string; actor_id: string }> {
  const response = await fetch("/dev/token", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  const body: unknown = await response.json();
  if (!response.ok) {
    throw new ApiError(response.status, "MB-4220", "could not mint a development token");
  }
  return body as { token: string; role: string; actor_id: string };
}

function asRecord(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

export function commanderPayloadHasNoToken(payload: Aggregate): boolean {
  return !JSON.stringify(payload).includes("tok_") && !("subject_token" in payload);
}

export function fairnessPayloadHasNoToken(payload: FairnessReport): boolean {
  return !JSON.stringify(payload).includes("tok_") && !("subject_token" in payload);
}
