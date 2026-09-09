import type { Role, Session } from "../api/types";

const KEY = "manobal.session";

export function readSession(): Session | null {
  const raw = sessionStorage.getItem(KEY);
  if (!raw) {
    return null;
  }
  try {
    const parsed = JSON.parse(raw) as Session;
    return parsed.token && parsed.role ? parsed : null;
  } catch {
    return null;
  }
}

export function writeSession(session: Session): void {
  sessionStorage.setItem(KEY, JSON.stringify(session));
}

export function clearSession(): void {
  sessionStorage.removeItem(KEY);
}

export function homeFor(role: Role): string {
  if (role === "personnel") return "/me";
  if (role === "welfare_officer" || role === "medical_officer") return "/officer";
  if (role === "commander") return "/commander";
  if (role === "wdec_auditor") return "/wdec";
  return "/";
}
