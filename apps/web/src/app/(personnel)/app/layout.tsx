"use client";

import { SaathiShell } from "@manobal/ui";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";

import { queueCount } from "@/lib/offline";
import { useEngine } from "@/lib/use-engine";
import { useFlowMetaValue } from "@/lib/flow-meta";

function languageLabel(code?: string): string | undefined {
  if (code === "ta" || code === "Tamil") {
    return "Tamil";
  }
  if (code === "en" || code === "English") {
    return "English";
  }
  if (code === "hi" || code === "Hindi" || code === "hi-Latn" || code === "Hinglish") {
    return code === "hi-Latn" || code === "Hinglish" ? "Hinglish" : "Hindi";
  }
  return undefined;
}

function screenTitle(pathname: string): string | undefined {
  if (pathname === "/app") {
    return undefined;
  }
  if (pathname === "/app/saathi") {
    return "Saathi";
  }
  if (pathname.startsWith("/app/onboarding")) {
    return "Getting started";
  }
  if (pathname.startsWith("/app/check-in")) {
    return "Check-in";
  }
  if (pathname.startsWith("/app/talk")) {
    return "Talk to a person";
  }
  if (pathname.startsWith("/app/toolkit")) {
    return "Toolkit";
  }
  if (pathname === "/app/me") {
    return "Me";
  }
  if (pathname.startsWith("/app/assessments/")) {
    return "Assessments";
  }
  if (pathname.startsWith("/app/assessments")) {
    return "Assessments";
  }
  if (pathname.startsWith("/app/rest")) {
    return "Plan my rest";
  }
  if (pathname.startsWith("/app/plan")) {
    return "My safety plan";
  }
  if (pathname.startsWith("/app/family")) {
    return "Family connect";
  }
  if (pathname.startsWith("/app/concerns")) {
    return "Raise a concern";
  }
  if (pathname.startsWith("/app/buddy")) {
    return "Buddy";
  }
  return "Saathi";
}

export default function SaathiLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const chrome =
    pathname.startsWith("/app/safety") ||
    pathname.startsWith("/app/toolkit/")
      ? "none"
      : pathname.startsWith("/app/check-in") ||
          pathname === "/app/saathi" ||
          pathname.startsWith("/app/onboarding") ||
          pathname.startsWith("/app/assessments/")
        ? "flow"
        : "full";
  const { data } = useEngine("home-chrome", (client, signal) => client.meHome(signal));
  const greeting = pathname === "/app" ? (data?.greeting ?? "Saathi") : "Saathi";
  const shiftLine = pathname === "/app" ? data?.shift_line : undefined;
  const [offline, setOffline] = useState(false);
  const [queued, setQueued] = useState(0);
  const stepMeta = useFlowMetaValue();
  const flowLabel = screenTitle(pathname);
  const flowMeta =
    pathname === "/app/saathi" ? languageLabel(data?.language) : stepMeta || undefined;

  useEffect(() => {
    const sync = () => {
      setOffline(typeof navigator !== "undefined" ? !navigator.onLine : false);
      void queueCount().then(setQueued);
    };
    sync();
    window.addEventListener("online", sync);
    window.addEventListener("offline", sync);
    window.addEventListener("manobal-queue", sync);
    return () => {
      window.removeEventListener("online", sync);
      window.removeEventListener("offline", sync);
      window.removeEventListener("manobal-queue", sync);
    };
  }, []);

  return (
    <SaathiShell
      chrome={chrome}
      flowLabel={flowLabel}
      flowMeta={flowMeta}
      greeting={greeting}
      offline={offline}
      onNavigate={(href) => router.push(href)}
      pathname={pathname}
      queued={queued}
      shiftLine={shiftLine}
      simple={Boolean(data?.simple_mode)}
    >
      {children}
    </SaathiShell>
  );
}
