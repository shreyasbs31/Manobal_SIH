import type { Role } from "../api/types";

const ROLE_LABEL: Record<Role, string> = {
  personnel: "Personnel",
  welfare_officer: "Welfare officer",
  medical_officer: "Medical officer",
  commander: "Commander",
  wdec_auditor: "WDEC auditor",
  integration: "Integration",
};

export function roleLabel(role: Role): string {
  return ROLE_LABEL[role] ?? role;
}

export function formatWhen(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function shortToken(token: string): string {
  if (token.length <= 14) return token;
  return `${token.slice(0, 8)}…${token.slice(-4)}`;
}

export function humanize(value: string): string {
  return value.replaceAll("_", " ");
}

export function categoryList(names: string[]): string {
  return names.length ? names.map(humanize).join(" · ") : "None recorded";
}

export function consentLabel(value: boolean | null | undefined): string {
  if (value === true) return "granted";
  if (value === false) return "withdrawn";
  return "unset";
}
