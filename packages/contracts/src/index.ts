export type { components, paths } from "./schema";

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
      signal?: AbortSignal;
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
    if (options.signal !== undefined) {
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
}
