import type {
  AgentTurn,
  Assessment,
  AudioPart,
  Checkin,
  ConsentState,
  HelplineCard,
  Insights,
  JournalEntry,
  OwnTrends,
  SeedInfo,
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

type FetchLike = (input: string, init?: RequestInit) => Promise<Response>;

export type PersonnelClientOptions = {
  baseUrl: string;
  token: string;
  fetchImpl?: FetchLike;
};

export function publicHeaders(extra: Record<string, string> = {}): Record<string, string> {
  return {
    Accept: "application/json",
    "ngrok-skip-browser-warning": "1",
    ...extra,
  };
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

export function createPersonnelClient(options: PersonnelClientOptions) {
  const base = options.baseUrl.replace(/\/$/, "");
  const fetchImpl = options.fetchImpl ?? fetch;

  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = publicHeaders({
      Authorization: `Bearer ${options.token}`,
    });
    if (init.body && !(init.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }
    const response = await fetchImpl(`${base}${path}`, {
      ...init,
      headers: { ...headers, ...(init.headers as Record<string, string> | undefined) },
    });
    const body: unknown = await response.json().catch(() => ({}));
    if (!response.ok) {
      const problem = asRecord(body);
      throw new ApiError(
        response.status,
        String(problem.code ?? `MB-${response.status}0`),
        String(problem.detail ?? problem.title ?? response.statusText),
      );
    }
    return body as T;
  }

  return {
    seed: () => request<SeedInfo>("/dev/seed"),
    consent: () => request<ConsentState>("/v1/me/consent"),
    setConsent: (data_type: string, granted: boolean) =>
      request("/v1/me/consent", {
        method: "POST",
        body: JSON.stringify({ data_type, granted }),
      }),
    assessment: () => request<Assessment>("/v1/me/assessment"),
    insights: () => request<Insights>("/v1/me/insights"),
    trends: () => request<OwnTrends>("/v1/me/trends"),
    checkin: () => request<Checkin>("/v1/me/checkin"),
    submitCheckin: (payload: Omit<Checkin, "observed_on">) =>
      request<Checkin>("/v1/me/checkin", { method: "POST", body: JSON.stringify(payload) }),
    helpline: () => request<HelplineCard>("/v1/me/helpline", { method: "POST", body: "{}" }),
    sos: () => request<{ accepted: true }>("/v1/me/sos", { method: "POST", body: "{}" }),
    journal: () => request<{ entries: JournalEntry[]; paused: boolean }>("/v1/me/journal"),
    writeJournal: (body: string) =>
      request<JournalEntry>("/v1/me/journal", {
        method: "POST",
        body: JSON.stringify({ body }),
      }),
    agent: (message: string, session_id?: string) =>
      request<AgentTurn>("/v1/me/agent", {
        method: "POST",
        body: JSON.stringify({ message, session_id }),
      }),
    async transcribe(part: AudioPart): Promise<string> {
      const form = new FormData();
      form.append(
        "audio",
        { uri: part.uri, name: part.name, type: part.type } as unknown as Blob,
      );
      form.append("language", part.language ?? "en");
      const body = await request<{ transcript?: string }>("/v1/me/transcribe", {
        method: "POST",
        body: form,
      });
      return typeof body.transcript === "string" ? body.transcript : "";
    },
  };
}

export async function mintPersonnelToken(
  options: {
    baseUrl: string;
    subjectToken: string;
    unitCode: string;
    fetchImpl?: FetchLike;
  },
): Promise<string> {
  const fetchImpl = options.fetchImpl ?? fetch;
  const response = await fetchImpl(`${options.baseUrl.replace(/\/$/, "")}/dev/token`, {
    method: "POST",
    headers: publicHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({
      role: "personnel",
      actor_id: options.subjectToken,
      unit_code: options.unitCode,
      force_code: "CAPF",
      subject_token: options.subjectToken,
    }),
  });
  const body = asRecord(await response.json().catch(() => ({})));
  if (!response.ok || typeof body.token !== "string") {
    throw new ApiError(response.status, "MB-4010", "could not pair this device");
  }
  return body.token;
}
