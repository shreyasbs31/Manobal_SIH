"use client";

import { CommandShell, type NavItem } from "@manobal/ui";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { useEffect } from "react";

import { manobalMode } from "@/lib/mode";
import { allowedConsolePath } from "@/lib/stage-role";

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
  "/command": "Bn C-02",
  "/command/roster": "Roster balancer",
  "/welfare": "Bn C-02 welfare",
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

function titleFor(pathname: string): string {
  if (pathname.startsWith("/welfare/cases/")) {
    return pathname.slice("/welfare/cases/".length);
  }
  return TITLES[pathname] ?? "Console";
}

function goViaStage(href: string) {
  window.parent.postMessage(
    { type: "manobal.stage.console-go", path: href, frame: window.name },
    window.location.origin,
  );
}

export function ConsoleChrome({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  useEffect(() => {
    if (typeof window === "undefined" || window.parent === window) {
      return;
    }
    const onClick = (event: MouseEvent) => {
      if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.shiftKey) {
        return;
      }
      const target = event.target;
      if (!(target instanceof Element)) {
        return;
      }
      const anchor = target.closest("a");
      if (!anchor) {
        return;
      }
      const href = anchor.getAttribute("href");
      if (!href || !href.startsWith("/") || href.startsWith("//") || href.includes("://")) {
        return;
      }
      const path = href.split("?")[0] ?? href;
      if (!allowedConsolePath(path)) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      goViaStage(href);
    };
    document.addEventListener("click", onClick, true);
    return () => document.removeEventListener("click", onClick, true);
  }, []);

  return (
    <CommandShell
      clock="2026-09-16 10:00 IST"
      mode={manobalMode()}
      navItems={NAV}
      onNavigate={(href) => {
        if (typeof window !== "undefined" && window.parent !== window) {
          goViaStage(href);
          return;
        }
        window.location.assign(href);
      }}
      pathname={pathname}
      title={titleFor(pathname)}
    >
      {children}
    </CommandShell>
  );
}
