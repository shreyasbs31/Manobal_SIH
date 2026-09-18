import type { ManobalRole } from "@manobal/contracts";

export type StageDeskRole = ManobalRole | "any";

export function roleForPath(pathname: string): StageDeskRole {
  const path = pathname.split("?")[0] ?? pathname;
  if (path.startsWith("/app")) {
    return "personnel";
  }
  if (path.startsWith("/welfare")) {
    return "uwo";
  }
  if (path.startsWith("/counsel")) {
    return "counsellor";
  }
  if (path.startsWith("/medical")) {
    return "mo";
  }
  if (path.startsWith("/command")) {
    return "commander";
  }
  if (path.startsWith("/hq")) {
    return "hq";
  }
  if (path.startsWith("/governance") || path.startsWith("/lab")) {
    return "wdec";
  }
  if (path.startsWith("/dpo")) {
    return "dpo";
  }
  if (path.startsWith("/integrations")) {
    return "hrms_integrator";
  }
  if (path.startsWith("/admin")) {
    return "admin";
  }
  if (path.startsWith("/director") || path.startsWith("/architecture")) {
    return "director";
  }
  return "any";
}

export function principalMatchesPath(role: string | undefined, pathname: string): boolean {
  const needed = roleForPath(pathname);
  if (needed === "any") {
    return true;
  }
  return role === needed;
}

export function allowedPhonePath(path: string): boolean {
  return path === "/app" || path.startsWith("/app/");
}

export function allowedConsolePath(path: string): boolean {
  const prefixes = [
    "/command",
    "/welfare",
    "/counsel",
    "/medical",
    "/hq",
    "/governance",
    "/lab",
    "/dpo",
    "/integrations",
    "/admin",
    "/architecture",
    "/trust",
    "/director",
  ];
  return prefixes.some((prefix) => path === prefix || path.startsWith(`${prefix}/`));
}
