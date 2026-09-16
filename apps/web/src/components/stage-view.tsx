"use client";

import { PhoneFrame, RibbonMark, SimClock, StatusChip, SyntheticMarker } from "@manobal/ui";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

const PHONES = new Set([
  "/app",
  "/app/saathi",
  "/app/toolkit",
  "/app/me",
  "/app/check-in",
  "/app/safety",
  "/app/toolkit/breathe",
  "/app/onboarding",
  "/app/talk",
  "/app/rest",
  "/app/plan",
  "/app/buddy",
]);
const CONSOLES = new Set([
  "/command",
  "/command/roster",
  "/welfare",
  "/welfare/cases/MB-4091",
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
]);

const SHOT_LABELS: Record<string, string> = {
  landing: "Landing ribbon",
  onboarding: "Hindi onboarding",
  checkin: "Twenty second check-in",
  voice: "Hindi voice check-in",
  drift: "Arjun time travel",
  workspace: "Case workspace reveal",
  "imran-thomas": "Imran and Thomas",
  formation: "Formation and hidden tile",
  copilot: "Copilot Hindi refusal",
  roster: "Roster balancer",
  deepak: "Deepak safety and T4",
  governance: "Governance chain",
  lab: "Validation lab",
  offline: "Offline then sync",
  architecture: "Zones and self-test",
  close: "Landing second fold",
  karthik: "Karthik Tamil voice",
  rajesh: "Rajesh grievance",
  lalit: "Lalit incident",
  meena: "Meena leave planner",
};

function safePath(value: string | null, allowed: Set<string>, fallback: string): string {
  if (!value) {
    return fallback;
  }
  if (!value.startsWith("/") || value.startsWith("//") || value.includes("://")) {
    return fallback;
  }
  return allowed.has(value) ? value : fallback;
}

export function StageView({
  phonePath,
  consolePath,
  shot,
}: {
  phonePath: string;
  consolePath: string;
  shot?: string | undefined;
}) {
  const phone = safePath(phonePath, PHONES, "/app");
  const consoleSafe = safePath(consolePath, CONSOLES, "/command");
  const [drawer, setDrawer] = useState(false);
  const label = (shot && SHOT_LABELS[shot]) || "Arjun home";

  const onKey = useCallback((event: KeyboardEvent) => {
    if (event.key.toLowerCase() === "d" && !event.metaKey && !event.ctrlKey) {
      const target = event.target;
      if (target instanceof HTMLElement && (target.tagName === "INPUT" || target.tagName === "TEXTAREA")) {
        return;
      }
      setDrawer((open) => !open);
    }
  }, []);

  useEffect(() => {
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onKey]);

  return (
    <div className="mb-stage">
      <header className="mb-stage-bar" aria-label="Recording">
        <h1 className="mb-brand">
          <RibbonMark />
          MANOBAL
        </h1>
        <SimClock value="2026-09-16 10:00 IST" />
        <span>{label}</span>
        <StatusChip kind="demo" />
        <SyntheticMarker />
      </header>
      <main className="mb-stage-split" aria-label="Phone and console">
        <PhoneFrame title="Saathi phone">
          <iframe src={phone} title="Saathi" loading="eager" />
        </PhoneFrame>
        <div className="mb-stage-console">
          <iframe src={consoleSafe} title="Command console" loading="eager" />
        </div>
      </main>
      <aside className="mb-stage-drawer" data-open={drawer ? "true" : "false"}>
        <p>Director drawer. Hidden during recording unless toggled with D.</p>
        <span>Phone {phone}</span>
        <span>Console {consoleSafe}</span>
        <Link className="mb-secondary" href="/director">
          Open director
        </Link>
        <Link className="mb-secondary" href="/stage?phone=/app/me&console=/welfare/cases/MB-4091&shot=workspace">
          Arjun reveal plus ledger
        </Link>
        <Link className="mb-secondary" href="/stage?phone=/app/saathi&console=/welfare&shot=voice">
          Companion plus queue
        </Link>
        <Link className="mb-secondary" href="/stage?phone=/app/safety&console=/medical&shot=deepak">
          Safety plus acute
        </Link>
        <Link className="mb-secondary" href="/stage?phone=/app&console=/command&shot=formation">
          Formation plus hidden tile
        </Link>
        <Link className="mb-secondary" href="/stage?phone=/app&console=/governance&shot=governance">
          Governance chain
        </Link>
        <Link className="mb-secondary" href="/stage?phone=/app/check-in&console=/architecture&shot=offline">
          Offline plus architecture
        </Link>
      </aside>
    </div>
  );
}
