import type {
  AgentTurn,
  Aggregate,
  Anchor,
  Assessment,
  BreakGlassGrant,
  CaseDetail,
  CaseSummary,
  Checkin,
  ConsentState,
  ResolvedIdentity,
  RulesetProposal,
  Session,
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
    setConsent: (data_type: string, granted: boolean) =>
      request("/v1/me/consent", { method: "POST", body: JSON.stringify({ data_type, granted }) }),
    assessment: () => request<Assessment>("/v1/me/assessment"),
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
