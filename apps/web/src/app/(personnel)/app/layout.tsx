"use client";

import { SaathiShell } from "@manobal/ui";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";

import { queueCount } from "@/lib/offline";
import { useEngine } from "@/lib/use-engine";

export default function SaathiLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const chrome =
    pathname.startsWith("/app/safety") ||
    pathname.startsWith("/app/toolkit/")
      ? "none"
      : pathname.startsWith("/app/check-in") ||
          pathname === "/app/saathi" ||
          pathname.startsWith("/app/onboarding")
        ? "flow"
        : "full";
  const { data } = useEngine("home-chrome", (client, signal) => client.meHome(signal));
  const greeting = pathname === "/app" ? (data?.greeting ?? "Saathi") : "Saathi";
  const shiftLine = pathname === "/app" ? data?.shift_line : undefined;
  const [offline, setOffline] = useState(false);
  const [queued, setQueued] = useState(0);

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
      greeting={greeting}
      offline={offline}
      pathname={pathname}
      queued={queued}
      shiftLine={shiftLine}
      simple={Boolean(data?.simple_mode)}
    >
      {children}
    </SaathiShell>
  );
}
