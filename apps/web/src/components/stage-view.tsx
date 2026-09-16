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
]);

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
}: {
  phonePath: string;
  consolePath: string;
}) {
  const phone = safePath(phonePath, PHONES, "/app");
  const consoleSafe = safePath(consolePath, CONSOLES, "/command");
  const [drawer, setDrawer] = useState(false);

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
        <span>Arjun home</span>
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
        <Link className="mb-secondary" href="/stage?phone=/app/me&console=/welfare/cases/MB-4091">
          Arjun reveal plus ledger
        </Link>
        <Link className="mb-secondary" href="/stage?phone=/app/saathi&console=/welfare">
          Companion plus queue
        </Link>
        <Link className="mb-secondary" href="/stage?phone=/app/safety&console=/medical">
          Safety plus acute
        </Link>
      </aside>
    </div>
  );
}
