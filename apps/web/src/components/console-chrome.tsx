"use client";

import { CommandShell, type NavItem } from "@manobal/ui";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { manobalMode } from "@/lib/mode";

const NAV: readonly NavItem[] = [
  { href: "/command", label: "Unit posture" },
  { href: "/command/roster", label: "Roster balancer" },
  { href: "/welfare", label: "Welfare queue" },
  { href: "/counsel", label: "Counsellor desk" },
  { href: "/medical", label: "Acute board" },
  { href: "/hq", label: "Force HQ" },
  { href: "/governance", label: "Governance" },
  { href: "/dpo", label: "DPO centre" },
  { href: "/integrations", label: "Integrations" },
  { href: "/admin", label: "Admin" },
  { href: "/lab", label: "Validation lab" },
  { href: "/architecture", label: "Architecture" },
  { href: "/director", label: "Director" },
];

const TITLES: Record<string, string> = {
  "/command": "Unit posture",
  "/command/roster": "Roster balancer",
  "/welfare": "Support queue",
  "/counsel": "Counsellor desk",
  "/medical": "Acute response",
  "/hq": "Force HQ",
  "/governance": "Governance",
  "/dpo": "DPO centre",
  "/integrations": "Integration console",
  "/admin": "Administration",
  "/lab": "Validation lab",
  "/architecture": "Architecture",
  "/director": "Demo director",
};

export function ConsoleChrome({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return (
    <CommandShell
      clock="2026-09-16 10:00 IST"
      mode={manobalMode()}
      navItems={NAV}
      pathname={pathname}
      title={TITLES[pathname] ?? "Console"}
    >
      {children}
    </CommandShell>
  );
}
