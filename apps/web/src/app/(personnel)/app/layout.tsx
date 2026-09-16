"use client";

import { arjunHome } from "@manobal/contracts";
import { SaathiShell } from "@manobal/ui";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

export default function SaathiLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const chrome =
    pathname.startsWith("/app/safety") || pathname.startsWith("/app/toolkit/breathe")
      ? "none"
      : pathname.startsWith("/app/check-in") || pathname === "/app/saathi"
        ? "flow"
        : "full";
  return (
    <SaathiShell
      chrome={chrome}
      greeting={pathname === "/app" ? arjunHome.greeting : "Saathi"}
      pathname={pathname}
      queued={0}
      shiftLine={pathname === "/app" ? arjunHome.shift_line : undefined}
    >
      {children}
    </SaathiShell>
  );
}
