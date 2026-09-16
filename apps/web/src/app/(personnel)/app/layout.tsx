"use client";

import { SaathiShell } from "@manobal/ui";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { useEngine } from "@/lib/use-engine";

export default function SaathiLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const chrome =
    pathname.startsWith("/app/safety") || pathname.startsWith("/app/toolkit/breathe")
      ? "none"
      : pathname.startsWith("/app/check-in") || pathname === "/app/saathi"
        ? "flow"
        : "full";
  const { data } = useEngine("home-chrome", (client, signal) => client.meHome(signal));
  const greeting = pathname === "/app" ? (data?.greeting ?? "Saathi") : "Saathi";
  const shiftLine = pathname === "/app" ? data?.shift_line : undefined;
  return (
    <SaathiShell
      chrome={chrome}
      greeting={greeting}
      pathname={pathname}
      queued={0}
      shiftLine={shiftLine}
    >
      {children}
    </SaathiShell>
  );
}
