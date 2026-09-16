import type {
  CheckInQuestion,
  CommandPosture,
  HomePayload,
  TrendPoint,
  WelfareCase,
} from "./ui-fixtures";

export type { components, paths } from "./schema";
export {
  PERSONA_IDS,
  arjunHome,
  arjunVoice,
  arjunWorkspace,
  checkInQuestions,
  commandPosture,
  demoPrincipal,
  governanceOverview,
  landingRibbon,
  mePrivacy,
  medicalAcute,
  psMapping,
  welfareQueue,
} from "./ui-fixtures";
export type {
  CheckInQuestion,
  CommandPosture,
  FixtureTier,
  FixtureTrajectory,
  HomePayload,
  PersonaId,
  TrendPoint,
  WelfareCase,
} from "./ui-fixtures";

export type ManobalRole =
  | "personnel"
  | "uwo"
  | "counsellor"
  | "mo"
  | "commander"
  | "hq"
  | "wdec"
  | "dpo"
  | "hrms_integrator"
  | "admin"
  | "director";

export interface Principal {
  actor_id: string;
  role: ManobalRole;
  scopes: string[];
  scope_path: string;
  subject_token?: string | null;
  synthetic: boolean;
}

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  principal: Principal;
}

export interface DemoLoginRequest {
  role: ManobalRole;
  persona_id?: string | null;
}

interface ErrorEnvelope {
  error: {
    code: string;
    message: string;
    hint: string;
    trace_id?: string;
  };
}

function isErrorEnvelope(value: unknown): value is ErrorEnvelope {
  if (typeof value !== "object" || value === null || !("error" in value)) {
    return false;
  }
  const error = value.error;
  return (
    typeof error === "object" &&
    error !== null &&
    "code" in error &&
    typeof error.code === "string" &&
    "message" in error &&
    typeof error.message === "string" &&
    "hint" in error &&
    typeof error.hint === "string"
  );
}

export class ManobalApiError extends Error {
  readonly code: string;
  readonly hint: string;
  readonly status: number;
  readonly traceId?: string;

  constructor(status: number, envelope: ErrorEnvelope) {
    super(envelope.error.message);
    this.name = "ManobalApiError";
    this.code = envelope.error.code;
    this.hint = envelope.error.hint;
    this.status = status;
    if (envelope.error.trace_id !== undefined) {
      this.traceId = envelope.error.trace_id;
    }
  }
}

export class ManobalClient {
  constructor(
    private readonly baseUrl: string,
    private readonly getAccessToken: () => string | null = () => null,
  ) {}

  async request<TResponse, TBody = never>(
    path: string,
    options: {
      method?: "GET" | "POST";
      body?: TBody;
      signal?: AbortSignal | undefined;
    } = {},
  ): Promise<TResponse> {
    const headers = new Headers({ accept: "application/json" });
    const token = this.getAccessToken();
    if (token) {
      headers.set("authorization", `Bearer ${token}`);
    }
    const init: RequestInit = {
      method: options.method ?? "GET",
      headers,
      cache: "no-store",
    };
    if (options.signal) {
      init.signal = options.signal;
    }
    if (options.body !== undefined) {
      headers.set("content-type", "application/json");
      init.body = JSON.stringify(options.body);
    }
    const response = await fetch(new URL(path, this.baseUrl), init);
    const payload: unknown = await response.json();
    if (!response.ok) {
      if (isErrorEnvelope(payload)) {
        throw new ManobalApiError(response.status, payload);
      }
      throw new Error(`API request failed with status ${response.status}`);
    }
    return payload as TResponse;
  }

  demoLogin(body: DemoLoginRequest): Promise<LoginResponse> {
    return this.request<LoginResponse, DemoLoginRequest>(
      "/api/v1/auth/demo-login",
      { method: "POST", body },
    );
  }

  meHome(signal?: AbortSignal): Promise<HomePayload> {
    return this.request<HomePayload>("/api/v1/me/home", { signal });
  }

  meTrends(signal?: AbortSignal): Promise<{ points: TrendPoint[] }> {
    return this.request("/api/v1/me/trends", { signal });
  }

  meCheckIn(signal?: AbortSignal): Promise<{
    questions: CheckInQuestion[];
    busy_day?: boolean;
    voice_default?: boolean;
    tags?: string[];
    saved?: string;
  }> {
    return this.request("/api/v1/me/check-in", { signal });
  }

  meOnboarding(signal?: AbortSignal): Promise<{
    languages: string[];
    consents: {
      id: string;
      title: string;
      leavesPhone: string;
      whoCanSee: string;
      default: boolean;
    }[];
    exception: string;
    helpers: string[];
    profile: Record<string, unknown>;
    receipt: { hash: string; time: string } | null;
  }> {
    return this.request("/api/v1/me/onboarding", { signal });
  }

  completeOnboarding(body: Record<string, unknown>): Promise<{
    receipt: { hash: string; time: string; skipped: Record<string, boolean> };
    profile: { onboarding_done: boolean; language: string };
  }> {
    return this.request("/api/v1/me/onboarding", { method: "POST", body });
  }

  saveCheckIn(body: Record<string, unknown>): Promise<{
    saved: boolean;
    message?: string;
    skipped?: boolean;
  }> {
    return this.request("/api/v1/me/check-in", { method: "POST", body });
  }

  meAssessments(signal?: AbortSignal): Promise<{
    items: {
      id: string;
      title: string;
      badge: string;
      self_only: boolean;
      badge_label: string;
      items: number;
    }[];
  }> {
    return this.request("/api/v1/me/assessments", { signal });
  }

  meAssessment(id: string, signal?: AbortSignal): Promise<{
    id: string;
    title: string;
    self_only: boolean;
    prompts: string[];
    options: string[];
    items: number;
  }> {
    return this.request(`/api/v1/me/assessments/${id}`, { signal });
  }

  saveAssessment(
    id: string,
    body: { item: number; value: number; conversational?: boolean },
  ): Promise<{ saved: boolean; safety: boolean; self_only: boolean; verbatim?: boolean }> {
    return this.request(`/api/v1/me/assessments/${id}`, { method: "POST", body });
  }

  meToolkit(signal?: AbortSignal): Promise<{
    items: { id: string; title: string; detail: string; href: string; offline: boolean }[];
    ranking: { order: string[]; context: Record<string, unknown> };
  }> {
    return this.request("/api/v1/me/toolkit", { signal });
  }

  meRest(signal?: AbortSignal): Promise<{
    el_days: number;
    cl_days: number;
    window: { start: string; end: string; travel_days: number; note: string } | null;
    copy: string;
    days: { label: string; start: number; end: number; sleep: string; caffeine: string }[];
  }> {
    return this.request("/api/v1/me/rest", { signal });
  }

  meTalk(signal?: AbortSignal): Promise<{
    requests: Record<string, unknown>[];
    bookings: Record<string, unknown>[];
    acs_configured: boolean;
    demo_join: boolean;
    demo_label: string;
    anonymous_handle: string;
  }> {
    return this.request("/api/v1/me/talk", { signal });
  }

  saveTalk(body: Record<string, unknown>): Promise<{
    request: Record<string, unknown>;
    demo_join: boolean;
    demo_label: string;
  }> {
    return this.request("/api/v1/me/talk", { method: "POST", body });
  }

  meBuddy(signal?: AbortSignal): Promise<{
    paired: boolean;
    code?: string;
    lessons: string[];
    privacy: string;
  }> {
    return this.request("/api/v1/me/buddy", { signal });
  }

  saveBuddy(body: Record<string, unknown>): Promise<Record<string, unknown>> {
    return this.request("/api/v1/me/buddy", { method: "POST", body });
  }

  meFamily(signal?: AbortSignal): Promise<{
    reminder: string | null;
    share_link: string;
    personal_data: boolean;
    resources: string[];
  }> {
    return this.request("/api/v1/me/family", { signal });
  }

  saveFamily(reminder = "sunday"): Promise<{ reminder: string; personal_data: boolean }> {
    return this.request(`/api/v1/me/family?reminder=${reminder}`, { method: "POST" });
  }

  meRights(signal?: AbortSignal): Promise<{
    notice: { version: string; hash: string; language: string };
    actions: string[];
    receipts: Record<string, unknown>[];
    remembers_opt_in: boolean;
    simple_mode: boolean;
  }> {
    return this.request("/api/v1/me/rights", { signal });
  }

  eraseRights(dataType = "self_report"): Promise<{
    sha256: string;
    signature: string;
    at: string;
  }> {
    return this.request(`/api/v1/me/rights/erase?data_type=${dataType}`, { method: "POST" });
  }

  meRemembers(signal?: AbortSignal): Promise<{
    opt_in: boolean;
    items: { group: string; text: string }[];
    groups: string[];
  }> {
    return this.request("/api/v1/me/remembers", { signal });
  }

  saveRemembers(body: Record<string, unknown>): Promise<{
    opt_in: boolean;
    items: { group: string; text: string }[];
  }> {
    return this.request("/api/v1/me/remembers", { method: "POST", body });
  }

  savePersonalisation(patch: Record<string, unknown>): Promise<{ profile: Record<string, unknown> }> {
    return this.request("/api/v1/me/personalisation", { method: "POST", body: { patch } });
  }

  jitaiNotNow(): Promise<{ silenced_until: string }> {
    return this.request("/api/v1/me/jitai/not-now", { method: "POST" });
  }

  savePulse(kind: "unit" | "trust", value: number): Promise<{ saved: boolean }> {
    return this.request("/api/v1/me/pulse", { method: "POST", body: { kind, value } });
  }

  saveConcern(body: Record<string, unknown>): Promise<Record<string, unknown>> {
    return this.request("/api/v1/me/concerns", { method: "POST", body });
  }

  meConcerns(signal?: AbortSignal): Promise<{ items: Record<string, unknown>[] }> {
    return this.request("/api/v1/me/concerns", { signal });
  }

  offlineSnapshot(signal?: AbortSignal): Promise<Record<string, unknown>> {
    return this.request("/api/v1/me/offline-snapshot", { signal });
  }

  syncQueue(items: { kind: string; payload: Record<string, unknown>; client_id: string }[]): Promise<{
    drained: number;
    edge_up: boolean;
  }> {
    return this.request("/api/v1/me/sync", { method: "POST", body: items });
  }

  i18n(lang: string, signal?: AbortSignal): Promise<{
    lang: string;
    reviewed: boolean;
    machine_translated: boolean;
    strings: Record<string, string>;
  }> {
    return this.request(`/api/v1/i18n/${lang}`, { signal });
  }

  setEdgeLink(up: boolean): Promise<{ up: boolean; queued: number; drained: number }> {
    return this.request("/api/v1/demo/edge-link", { method: "POST", body: { up } });
  }

  meVoice(signal?: AbortSignal): Promise<{
    persona_id: string;
    language: string;
    lines: { speaker: "you" | "saathi"; text: string }[];
    audio_cleared_ms: number;
    model_caption: string;
  }> {
    return this.request("/api/v1/me/voice", { signal });
  }

  meConsents(signal?: AbortSignal): Promise<{
    token: string | null;
    items: { title: string; leavesPhone: string; whoCanSee: string; on: boolean }[];
  }> {
    return this.request("/api/v1/me/consents", { signal });
  }

  meLedger(signal?: AbortSignal): Promise<{ items: Record<string, string>[] }> {
    return this.request("/api/v1/me/access-ledger", { signal });
  }

  mePurge(dataType: string): Promise<{ signature: string; row_count: number; sha256: string; at: string }> {
    return this.request(`/api/v1/me/purge/${dataType}`, { method: "POST" });
  }

  welfareQueue(signal?: AbortSignal): Promise<WelfareCase[]> {
    return this.request("/api/v1/welfare/queue", { signal });
  }

  welfareCase(caseId: string, signal?: AbortSignal): Promise<Record<string, unknown>> {
    return this.request(`/api/v1/welfare/cases/${caseId}`, { signal });
  }

  medicalAcute(signal?: AbortSignal): Promise<WelfareCase[]> {
    return this.request("/api/v1/medical/acute", { signal });
  }

  medicalAck(caseId: string): Promise<{ status: string }> {
    return this.request(`/api/v1/medical/acute/${caseId}/ack`, { method: "POST" });
  }

  commandPosture(signal?: AbortSignal): Promise<CommandPosture> {
    return this.request("/api/v1/command/posture", { signal });
  }

  govOverview(signal?: AbortSignal): Promise<{
    kpis: { label: string; value: string; hint: string }[];
  }> {
    return this.request("/api/v1/gov/kpis", { signal });
  }

  govFairness(signal?: AbortSignal): Promise<{ fairness: { label: string; ratio: number }[] }> {
    return this.request("/api/v1/gov/fairness", { signal });
  }

  govKillswitches(signal?: AbortSignal): Promise<Record<string, boolean>> {
    return this.request("/api/v1/gov/killswitches", { signal });
  }

  systemSelftest(signal?: AbortSignal): Promise<{
    healthy: boolean;
    vault_database_isolated: boolean;
    vault_identity_keys_isolated: boolean;
    zone_x_unreachable: boolean;
  }> {
    return this.request("/api/v1/system/selftest", { signal });
  }

  postAcute(body: {
    token: string;
    trigger: string;
    lang: string;
    channel: string;
  }): Promise<{ case_id: string; tier: string; alerts: number; llm_invoked: boolean }> {
    return this.request("/api/v1/acute", { method: "POST", body });
  }

  companionTurn(body: { text: string; lang: string; mode: string }): Promise<{
    acute: boolean;
    injection: boolean;
    reply: string | null;
    script: string | null;
    model_reached: boolean;
    citations: string[];
    hosting_caption: string;
  }> {
    return this.request("/api/v1/companion/turn", { method: "POST", body });
  }
}
