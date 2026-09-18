"use client";

import {
  ManobalApiError,
  ManobalClient,
  type DemoLoginRequest,
  type LoginResponse,
  type Principal,
} from "@manobal/contracts";

import { principalMatchesPath } from "@/lib/stage-role";

export function engineBaseUrl(): string {
  if (typeof window !== "undefined") {
    return window.location.origin;
  }
  return process.env.ENGINE_INTERNAL_URL ?? "http://localhost:8000";
}

export function voiceWebSocketUrl(): string {
  if (typeof window === "undefined") {
    return "ws://localhost:8000/api/v1/voice/session";
  }
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.hostname;
  if (host === "localhost" || host === "127.0.0.1") {
    return `${proto}//${host}:8000/api/v1/voice/session`;
  }
  return `${proto}//${window.location.host}/api/v1/voice/session`;
}

export function persistLogin(login: LoginResponse, demo?: DemoLoginRequest | null): void {
  sessionStorage.setItem("manobal.access_token", login.access_token);
  sessionStorage.setItem("manobal.principal", JSON.stringify(login.principal));
  if (demo) {
    sessionStorage.setItem("manobal.demo_login", JSON.stringify(demo));
  }
}

export function demoLoginBody(): DemoLoginRequest | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const stored = sessionStorage.getItem("manobal.demo_login");
    if (stored) {
      return JSON.parse(stored) as DemoLoginRequest;
    }
    const raw = sessionStorage.getItem("manobal.principal");
    if (!raw) {
      return null;
    }
    const principal = JSON.parse(raw) as { role: DemoLoginRequest["role"]; actor_id: string };
    const personaId = principal.actor_id.startsWith("demo:")
      ? principal.actor_id.slice("demo:".length)
      : null;
    return {
      role: principal.role,
      persona_id: principal.role === "personnel" ? personaId : null,
    };
  } catch {
    return null;
  }
}

let refreshInFlight: Promise<boolean> | null = null;

export async function refreshDemoSession(): Promise<boolean> {
  if (typeof window === "undefined") {
    return false;
  }
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      const body = demoLoginBody();
      if (!body) {
        return false;
      }
      try {
        const login = await new ManobalClient(engineBaseUrl()).demoLogin(body);
        persistLogin(login, body);
        return true;
      } catch {
        return false;
      }
    })().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

let frameAccessToken: string | null = null;
let framePrincipal: Principal | null = null;

export const STAGE_PHONE_FRAME = "mb-phone";
export const STAGE_CONSOLE_FRAME = "mb-console";

export function inStageFrame(): boolean {
  return typeof window !== "undefined" && window.parent !== window;
}

export function currentAccessToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  if (inStageFrame()) {
    return frameAccessToken;
  }
  return sessionStorage.getItem("manobal.access_token");
}

export function currentPrincipal(): Principal | null {
  if (typeof window === "undefined") {
    return null;
  }
  if (inStageFrame()) {
    return framePrincipal;
  }
  try {
    const raw = sessionStorage.getItem("manobal.principal");
    return raw ? (JSON.parse(raw) as Principal) : null;
  } catch {
    return null;
  }
}

export function canDrainPersonnelQueue(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  if (window.location.pathname.startsWith("/stage")) {
    return false;
  }
  if (inStageFrame() && window.name === STAGE_CONSOLE_FRAME) {
    return false;
  }
  const principal = currentPrincipal();
  return Boolean(principal?.scopes.includes("me:write"));
}

export function applyFrameSession(token: string, principal?: Principal | null): void {
  const changed = frameAccessToken !== token;
  const roleChanged = Boolean(principal && principal.role !== framePrincipal?.role);
  frameAccessToken = token;
  if (principal) {
    framePrincipal = principal;
  }
  if (changed || roleChanged) {
    window.dispatchEvent(new Event("manobal-session"));
  }
}

export function askParentForStageRole(pathname: string): void {
  if (typeof window === "undefined" || !inStageFrame()) {
    return;
  }
  window.parent.postMessage(
    { type: "manobal.stage.need-role", path: pathname, frame: window.name },
    window.location.origin,
  );
}

export function stageRoleReady(pathname: string): boolean {
  if (typeof window === "undefined" || !inStageFrame()) {
    return true;
  }
  const principal = currentPrincipal();
  if (!principal || !currentAccessToken()) {
    return false;
  }
  return principalMatchesPath(principal.role, pathname);
}

const STAGE_STORE: Record<string, { token: string; principal: string }> = {
  [STAGE_PHONE_FRAME]: {
    token: "manobal.stage.phone",
    principal: "manobal.stage.phone.principal",
  },
  [STAGE_CONSOLE_FRAME]: {
    token: "manobal.stage.console",
    principal: "manobal.stage.console.principal",
  },
};

export function storeStageSession(
  frame: typeof STAGE_PHONE_FRAME | typeof STAGE_CONSOLE_FRAME,
  token: string,
  principal: Principal,
): void {
  if (typeof window === "undefined") {
    return;
  }
  const keys = STAGE_STORE[frame];
  if (!keys) {
    return;
  }
  sessionStorage.setItem(keys.token, token);
  sessionStorage.setItem(keys.principal, JSON.stringify(principal));
}

function sessionFromFrameName(): { token: string; principal: Principal | null } | null {
  const keys = STAGE_STORE[window.name];
  if (!keys) {
    return null;
  }
  const token = sessionStorage.getItem(keys.token);
  if (!token) {
    return null;
  }
  try {
    const raw = sessionStorage.getItem(keys.principal);
    return { token, principal: raw ? (JSON.parse(raw) as Principal) : null };
  } catch {
    return { token, principal: null };
  }
}

if (typeof window !== "undefined" && inStageFrame()) {
  const stored = sessionFromFrameName();
  const path = window.location.pathname;
  if (stored?.principal && principalMatchesPath(stored.principal.role, path)) {
    applyFrameSession(stored.token, stored.principal);
  } else if (stored && !stored.principal) {
    applyFrameSession(stored.token, stored.principal);
  }
  window.addEventListener("message", (event: MessageEvent) => {
    if (event.origin !== window.location.origin) {
      return;
    }
    const data = event.data as {
      type?: string;
      access_token?: string;
      principal?: Principal;
      kind?: string;
    };
    if (data?.type === "manobal.stage.auth" && typeof data.access_token === "string") {
      const nextPrincipal = data.principal ?? null;
      if (nextPrincipal && !principalMatchesPath(nextPrincipal.role, window.location.pathname)) {
        askParentForStageRole(window.location.pathname);
        return;
      }
      applyFrameSession(data.access_token, nextPrincipal);
    }
    if (data?.type === "manobal.stage.invalidate") {
      window.dispatchEvent(new CustomEvent("manobal-live", { detail: data }));
    }
  });
  window.parent.postMessage({ type: "manobal.stage.ready" }, window.location.origin);
}

function sendToLogin(): void {
  if (typeof window === "undefined" || inStageFrame()) {
    return;
  }
  if (!window.location.pathname.startsWith("/login")) {
    window.location.assign("/login");
  }
}

export function engineClient(): ManobalClient {
  const client = new ManobalClient(engineBaseUrl(), () => currentAccessToken());
  const original = client.request.bind(client);
  client.request = (async (path, options) => {
    try {
      return await original(path, options);
    } catch (error) {
      const canRefresh =
        typeof window !== "undefined" &&
        !inStageFrame() &&
        error instanceof ManobalApiError &&
        error.status === 401 &&
        !path.includes("/auth/demo-login");
      if (canRefresh && (await refreshDemoSession())) {
        return await original(path, options);
      }
      if (canRefresh) {
        sendToLogin();
      }
      throw error;
    }
  }) as ManobalClient["request"];
  return client;
}

export function subjectToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  if (inStageFrame() && framePrincipal) {
    return framePrincipal.subject_token ?? null;
  }
  try {
    const raw = sessionStorage.getItem("manobal.principal");
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as { subject_token?: string | null };
    return parsed.subject_token ?? null;
  } catch {
    return null;
  }
}
