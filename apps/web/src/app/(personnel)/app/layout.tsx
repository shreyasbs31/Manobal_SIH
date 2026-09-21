"use client";

import { SaathiShell } from "@manobal/ui";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";

import {
  PersonnelLanguageProvider,
  usePersonnelI18n,
} from "@/lib/personnel-i18n";
import { queueCount } from "@/lib/offline";
import { useEngine } from "@/lib/use-engine";
import { useFlowMetaValue } from "@/lib/flow-meta";

function languageLabel(code: string | undefined, p: (text: string) => string): string | undefined {
  if (code === "ta" || code === "Tamil") {
    return p("Tamil");
  }
  if (code === "en" || code === "English") {
    return p("English");
  }
  if (code === "hi" || code === "Hindi" || code === "hi-Latn" || code === "Hinglish") {
    return p(code === "hi-Latn" || code === "Hinglish" ? "Hinglish" : "Hindi");
  }
  return undefined;
}

function screenTitle(pathname: string, p: (text: string) => string): string | undefined {
  if (pathname === "/app") {
    return undefined;
  }
  if (pathname === "/app/saathi") {
    return p("Saathi");
  }
  if (pathname.startsWith("/app/onboarding")) {
    return p("Getting started");
  }
  if (pathname.startsWith("/app/check-in")) {
    return p("Check-in");
  }
  if (pathname.startsWith("/app/talk")) {
    return p("Talk to a person");
  }
  if (pathname.startsWith("/app/toolkit")) {
    return p("Toolkit");
  }
  if (pathname === "/app/me") {
    return p("Me");
  }
  if (pathname.startsWith("/app/assessments/")) {
    return p("Assessments");
  }
  if (pathname.startsWith("/app/assessments")) {
    return p("Assessments");
  }
  if (pathname.startsWith("/app/rest")) {
    return p("Plan my rest");
  }
  if (pathname.startsWith("/app/plan")) {
    return p("My safety plan");
  }
  if (pathname.startsWith("/app/family")) {
    return p("Family connect");
  }
  if (pathname.startsWith("/app/concerns")) {
    return p("Raise a concern");
  }
  if (pathname.startsWith("/app/buddy")) {
    return p("Buddy");
  }
  return p("Saathi");
}

function LocalisedSaathiShell({
  children,
  pathname,
  chrome,
  greeting,
  shiftLine,
  language,
  offline,
  queued,
  simple,
  stepMeta,
}: {
  children: ReactNode;
  pathname: string;
  chrome: "full" | "flow" | "none";
  greeting?: string | undefined;
  shiftLine?: string | undefined;
  language?: string | undefined;
  offline: boolean;
  queued: number;
  simple: boolean;
  stepMeta: string;
}) {
  const router = useRouter();
  const { lang, p } = usePersonnelI18n();
  const isHome = pathname === "/app";
  const flowLabel = screenTitle(pathname, p);
  const flowMeta = pathname === "/app/saathi" ? languageLabel(language, p) : stepMeta || undefined;
  const homeGreeting =
    lang === "hi" ? p("Good morning") : lang === "ta" ? (greeting ?? p("Saathi")) : "Good morning";
  const offlineLabel =
    queued > 0 ? p("Offline. {n} check-ins saved on this phone.", { n: queued }) : p("Offline");

  return (
    <SaathiShell
      chrome={chrome}
      copy={{
        skip: p("Skip to content"),
        shell: p("Saathi"),
        content: p("Saathi content"),
        back: p("Back"),
        close: p("Close"),
        offline: offlineLabel,
        syncing: p("Syncing"),
        demo: p("Demo"),
      }}
      flowLabel={flowLabel}
      flowMeta={flowMeta}
      greeting={isHome ? homeGreeting : p("Saathi")}
      navItems={[
        { href: "/app", label: p("Home") },
        { href: "/app/saathi", label: p("Saathi") },
        { href: "/app/toolkit", label: p("Toolkit") },
        { href: "/app/me", label: p("Me") },
      ]}
      offline={offline}
      onNavigate={(href) => router.push(href)}
      pathname={pathname}
      queued={queued}
      shiftLine={isHome && shiftLine ? p(shiftLine) : undefined}
      simple={simple}
    >
      {children}
    </SaathiShell>
  );
}

export default function SaathiLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
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
  const [offline, setOffline] = useState(false);
  const [queued, setQueued] = useState(0);
  const stepMeta = useFlowMetaValue();

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
    <PersonnelLanguageProvider fallback={data?.language}>
      <LocalisedSaathiShell
        chrome={chrome}
        greeting={data?.greeting}
        language={data?.language}
        offline={offline}
        pathname={pathname}
        queued={queued}
        shiftLine={data?.shift_line}
        simple={Boolean(data?.simple_mode)}
        stepMeta={stepMeta}
      >
        {children}
      </LocalisedSaathiShell>
    </PersonnelLanguageProvider>
  );
}
