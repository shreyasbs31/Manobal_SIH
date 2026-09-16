"use client";

import { SaathiShell } from "@manobal/ui";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

export default function SaathiLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return (
    <SaathiShell greeting="Saathi" pathname={pathname} queued={0}>
      {children}
    </SaathiShell>
  );
}
