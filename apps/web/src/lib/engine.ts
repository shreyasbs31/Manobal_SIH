"use client";

import { ManobalClient } from "@manobal/contracts";

export function engineClient(): ManobalClient {
  return new ManobalClient(
    process.env.NEXT_PUBLIC_ENGINE_URL ?? "http://localhost:8000",
    () =>
      typeof window === "undefined" ? null : sessionStorage.getItem("manobal.access_token"),
  );
}

export function subjectToken(): string | null {
  if (typeof window === "undefined") {
    return null;
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
