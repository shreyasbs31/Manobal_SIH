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

  async requestBlob(path: string, signal?: AbortSignal): Promise<Blob> {
    const headers = new Headers({ accept: "application/pdf" });
    const token = this.getAccessToken();
    if (token) {
      headers.set("authorization", `Bearer ${token}`);
    }
    const init: RequestInit = { method: "GET", headers, cache: "no-store" };
    if (signal) {
      init.signal = signal;
    }
    const response = await fetch(new URL(path, this.baseUrl), init);
    if (!response.ok) {
      throw new Error(`API request failed with status ${response.status}`);
    }
    return response.blob();
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

  welfareTabs(signal?: AbortSignal): Promise<Record<string, unknown>> {
    return this.request("/api/v1/welfare/tabs", { signal });
  }

  welfareReveal(
    caseId: string,
    body: { purpose_code: string; justification: string },
  ): Promise<{
    revealed: boolean;
    grant_id: string;
    contact_note_due: string;
    notice: string;
    card: Record<string, string | boolean>;
  }> {
    return this.request(`/api/v1/welfare/cases/${caseId}/reveal`, { method: "POST", body });
  }

  welfareContactNote(grantId: string, note: string): Promise<{ grant_id: string; status: string }> {
    return this.request("/api/v1/welfare/contact-note", {
      method: "POST",
      body: { grant_id: grantId, note },
    });
  }

  welfareAction(
    caseId: string,
    body: { mode: string; lever: string; outcome: string; follow_up: string; refer: string },
  ): Promise<Record<string, string>> {
    return this.request(`/api/v1/welfare/cases/${caseId}/action`, { method: "POST", body });
  }

  welfareTrendRequest(caseId: string, domain: string): Promise<Record<string, string>> {
    return this.request(`/api/v1/welfare/cases/${caseId}/trend-request`, {
      method: "POST",
      body: { domain },
    });
  }

  counselDesk(signal?: AbortSignal): Promise<{
    calendar: string[];
    requests: Record<string, string | null>[];
    routing: { counsellor: string; languages: string[]; matched?: boolean };
    acs: { demo_join: boolean; label: string };
    notes_scope: string;
  }> {
    return this.request("/api/v1/counsel/desk", { signal });
  }

  counselNotes(sessionId: string, note: string): Promise<{ session_id: string; scope: string }> {
    return this.request("/api/v1/counsel/notes", {
      method: "POST",
      body: { session_id: sessionId, note },
    });
  }

  counselSuggest(
    caseId: string,
    lever: string,
    sentence: string,
  ): Promise<{ lever: string; notes_shared: boolean }> {
    return this.request("/api/v1/counsel/suggest", {
      method: "POST",
      body: { case_id: caseId, lever, sentence },
    });
  }

  medicalReferrals(signal?: AbortSignal): Promise<{
    items: { from: string; case_id: string; context: string }[];
    guide: { title: string; steps: string[]; note: string };
  }> {
    return this.request("/api/v1/medical/referrals", { signal });
  }

  commandRoster(signal?: AbortSignal): Promise<{
    companies: {
      id: string;
      label: string;
      n: number;
      duty_hours: number;
      rest_days: number;
      night_share: number;
      quick_return_cap: number;
      leave_release: number;
      locked: boolean;
      lock_reason?: string;
    }[];
  }> {
    return this.request("/api/v1/command/roster", { signal });
  }

  commandSimulate(body: Record<string, unknown>): Promise<Record<string, unknown>> {
    return this.request("/api/v1/command/simulate", { method: "POST", body });
  }

  commandDraft(body: Record<string, unknown>): Promise<{ title: string; body: string }> {
    return this.request("/api/v1/command/draft-order", { method: "POST", body });
  }

  commandLeave(signal?: AbortSignal): Promise<{
    copy: string;
    companies: { label: string; backlog_days: number; longest_wait: string }[];
    minimum_strength: string;
  }> {
    return this.request("/api/v1/command/leave", { signal });
  }

  commandClimate(signal?: AbortSignal): Promise<{
    pulse: { week: string; heavy: string }[];
    colleague_conflict: string;
    grievances: { category: string; age: string }[];
  }> {
    return this.request("/api/v1/command/climate", { signal });
  }

  commandCopilot(
    question: string,
    lang = "en",
  ): Promise<{
    refuse: boolean;
    answer: string;
    chart_spec: { type: string; metric: string; value: string };
    tools_used: string[];
  }> {
    return this.request("/api/v1/command/copilot", { method: "POST", body: { question, lang } });
  }

  hqOverview(signal?: AbortSignal): Promise<Record<string, unknown>> {
    return this.request("/api/v1/hq/overview", { signal });
  }

  hqSaveBrief(body: string): Promise<{ title: string; body: string; edited: boolean }> {
    return this.request("/api/v1/hq/brief", { method: "POST", body: { body } });
  }

  hqBriefPdf(signal?: AbortSignal): Promise<Blob> {
    return this.requestBlob("/api/v1/hq/brief.pdf", signal);
  }

  hqSimulate(body: Record<string, unknown>): Promise<Record<string, unknown>> {
    return this.request("/api/v1/hq/simulate", { method: "POST", body });
  }

  officerProfile(signal?: AbortSignal): Promise<Record<string, unknown>> {
    return this.request("/api/v1/officer/profile", { signal });
  }

  patchOfficerProfile(body: Record<string, unknown>): Promise<Record<string, unknown>> {
    return this.request("/api/v1/officer/profile", { method: "POST", body });
  }

  govOverview(signal?: AbortSignal): Promise<{
    kpis: { label: string; value: string; hint: string; code?: string }[];
    cost_guard?: boolean;
    cost_banner?: string;
  }> {
    return this.request("/api/v1/gov/kpis", { signal });
  }

  govFairness(signal?: AbortSignal): Promise<{
    fairness: { label: string; ratio: number }[];
    exposure_parity?: { slice: string; ratio: number; within_band: boolean }[];
    band?: string;
    note?: string;
  }> {
    return this.request("/api/v1/gov/fairness", { signal });
  }

  govKillswitches(signal?: AbortSignal): Promise<Record<string, boolean>> {
    return this.request("/api/v1/gov/killswitches", { signal });
  }

  setKillswitch(name: string): Promise<{ name: string; enabled: boolean }> {
    return this.request(`/api/v1/gov/killswitches/${name}`, { method: "POST", body: {} });
  }

  govProviders(signal?: AbortSignal): Promise<Record<string, unknown>> {
    return this.request("/api/v1/gov/providers", { signal });
  }

  govModels(signal?: AbortSignal): Promise<Record<string, unknown>> {
    return this.request("/api/v1/gov/models", { signal });
  }

  govRulesets(signal?: AbortSignal): Promise<{
    active: string;
    shadow: string;
    signed: boolean;
    signers: string[];
    yaml: string;
    needs: number;
  }> {
    return this.request("/api/v1/gov/rulesets", { signal });
  }

  govAudit(signal?: AbortSignal): Promise<{
    mode: string;
    valid: boolean;
    checked: number;
    broken_seq: number | null;
    head_hash: string;
    blocks: number;
  }> {
    return this.request("/api/v1/gov/audit", { signal });
  }

  govAuditVerify(): Promise<{ valid: boolean; checked: number; broken_seq: number | null }> {
    return this.request("/api/v1/gov/audit/verify", { method: "POST", body: {} });
  }

  govAuditTamper(): Promise<Record<string, unknown>> {
    return this.request("/api/v1/gov/audit/tamper", { method: "POST", body: {} });
  }

  govAuditRestore(): Promise<Record<string, unknown>> {
    return this.request("/api/v1/gov/audit/restore", { method: "POST", body: {} });
  }

  govTransparency(): Promise<Record<string, unknown>> {
    return this.request("/api/v1/gov/transparency-report", { method: "POST", body: {} });
  }

  govTransparencyPdf(signal?: AbortSignal): Promise<Blob> {
    return this.requestBlob("/api/v1/gov/transparency-report.pdf", signal);
  }

  govReviews(signal?: AbortSignal): Promise<{ items: Record<string, string>[] }> {
    return this.request("/api/v1/gov/reviews", { signal });
  }

  govAgentSafety(signal?: AbortSignal): Promise<Record<string, unknown>> {
    return this.request("/api/v1/gov/agent-safety", { signal });
  }

  publicTrust(signal?: AbortSignal): Promise<{
    title: string;
    promise: string;
    hosting: string;
    read_aloud: string;
    matrix: {
      collects: string;
      leaves_phone: string;
      who: string;
      exception: string;
    }[];
    languages: { code: string; name: string; reviewed: boolean }[];
  }> {
    return this.request("/api/v1/public/trust", { signal });
  }

  publicArchitecture(signal?: AbortSignal): Promise<{
    edge_up: boolean;
    queued: number;
    packets: { id: string; kind: string; held: boolean }[];
    mode: string;
    foundry: boolean;
    acs: boolean;
    speech: boolean;
    translator: boolean;
    content_safety: boolean;
    cost_guard: boolean;
  }> {
    return this.request("/api/v1/public/architecture", { signal });
  }

  dpoRequests(signal?: AbortSignal): Promise<Record<string, unknown>> {
    return this.request("/api/v1/dpo/requests", { signal });
  }

  dpoDecide(id: string, decision: string): Promise<Record<string, unknown>> {
    return this.request(`/api/v1/dpo/requests/${id}`, {
      method: "POST",
      body: { decision },
    });
  }

  integrationsJobs(signal?: AbortSignal): Promise<Record<string, unknown>> {
    return this.request("/api/v1/integrations/jobs", { signal });
  }

  integrationsUpload(filename: string, rows: Record<string, unknown>[]): Promise<Record<string, unknown>> {
    return this.request("/api/v1/integrations/hrms/upload", {
      method: "POST",
      body: { filename, rows },
    });
  }

  adminConsole(signal?: AbortSignal): Promise<Record<string, unknown>> {
    return this.request("/api/v1/admin/console", { signal });
  }

  adminFlag(name: string, enabled: boolean): Promise<Record<string, unknown>> {
    return this.request("/api/v1/admin/flags", { method: "POST", body: { name, enabled } });
  }

  labOverview(signal?: AbortSignal): Promise<Record<string, unknown>> {
    return this.request("/api/v1/lab/overview", { signal });
  }

  labMetrics(world: string, signal?: AbortSignal): Promise<Record<string, unknown>> {
    return this.request(`/api/v1/lab/metrics?world=${encodeURIComponent(world)}`, { signal });
  }

  labBenchmark(): Promise<{ subjects: number; seconds: number }> {
    return this.request("/api/v1/lab/benchmark", { method: "POST", body: {} });
  }

  directorBoard(signal?: AbortSignal): Promise<Record<string, unknown>> {
    return this.request("/api/v1/director/board", { signal });
  }

  demoScenario(name: string): Promise<Record<string, unknown>> {
    return this.request(`/api/v1/demo/scenario/${name}`, { method: "POST", body: {} });
  }

  demoReset(): Promise<{ status: string; seconds: number; scenario: string }> {
    return this.request("/api/v1/demo/reset", { method: "POST", body: {} });
  }

  demoTamper(): Promise<Record<string, unknown>> {
    return this.request("/api/v1/demo/tamper", { method: "POST", body: {} });
  }

  demoRestore(): Promise<Record<string, unknown>> {
    return this.request("/api/v1/demo/restore", { method: "POST", body: {} });
  }

  demoOutage(provider: string, opened: boolean): Promise<Record<string, unknown>> {
    return this.request("/api/v1/demo/outage", { method: "POST", body: { provider, opened } });
  }

  demoResilience(enabled: boolean): Promise<Record<string, unknown>> {
    return this.request("/api/v1/demo/resilience", { method: "POST", body: { enabled } });
  }

  demoWarmup(): Promise<Record<string, string>> {
    return this.request("/api/v1/demo/warmup", { method: "POST", body: {} });
  }

  demoClockJump(body: { days?: number; running?: boolean; speed?: number }): Promise<Record<string, unknown>> {
    return this.request("/api/v1/demo/director-clock", { method: "POST", body });
  }

  demoNightly(): Promise<Record<string, unknown>> {
    return this.request("/api/v1/demo/nightly", { method: "POST", body: {} });
  }

  demoCostExceeded(): Promise<Record<string, unknown>> {
    return this.request("/api/v1/demo/cost-exceeded", { method: "POST", body: {} });
  }

  edgeQueue(signal?: AbortSignal): Promise<{ up: boolean; queued: number; items?: Record<string, unknown>[] }> {
    return this.request("/api/v1/demo/edge-queue", { signal });
  }

  systemMode(signal?: AbortSignal): Promise<{
    mode: string;
    foundry: boolean;
    acs: boolean;
    speech: boolean;
  }> {
    return this.request("/api/v1/system/mode", { signal });
  }

  systemMetrics(signal?: AbortSignal): Promise<Record<string, unknown>> {
    return this.request("/api/v1/system/metrics", { signal });
  }

  systemSelftest(signal?: AbortSignal): Promise<{
    healthy: boolean;
    core_database_reachable: boolean;
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
