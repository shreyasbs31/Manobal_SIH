"use client";

import { CommandShell } from "@manobal/ui";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";

import { currentPrincipal } from "@/lib/engine";
import { readConsoleTheme, useConsoleLang } from "@/lib/console-i18n";
import { manobalMode } from "@/lib/mode";
import { allowedConsolePath } from "@/lib/stage-role";

function titleFor(pathname: string, titles: Record<string, string>): string {
  if (pathname.startsWith("/welfare/cases/")) {
    return pathname.slice("/welfare/cases/".length);
  }
  return titles[pathname] ?? "Console";
}

function homeHrefFor(pathname: string, titles: Record<string, string>): string {
  if (pathname.startsWith("/welfare")) {
    return "/welfare";
  }
  if (pathname.startsWith("/command")) {
    return "/command";
  }
  const root = `/${pathname.split("/").filter(Boolean)[0] ?? "command"}`;
  return titles[root] ? root : "/command";
}

function goViaStage(href: string) {
  window.parent.postMessage(
    { type: "manobal.stage.console-go", path: href, frame: window.name },
    window.location.origin,
  );
}

export function ConsoleChrome({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { lang, setLang, tx } = useConsoleLang();
  const [deskRole, setDeskRole] = useState("");

  useEffect(() => {
    const sync = () => {
      const role = currentPrincipal()?.role;
      setDeskRole(role ?? "");
    };
    sync();
    window.addEventListener("manobal-session", sync);
    return () => window.removeEventListener("manobal-session", sync);
  }, [pathname]);

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

  const deskLabel = deskRole ? (tx.desks[deskRole] ?? deskRole) : "";

  return (
    <CommandShell
      clock="2026-09-16 10:00 IST"
      homeHref={homeHrefFor(pathname, tx.titles)}
      language={lang}
      mode={manobalMode()}
      navItems={[...tx.nav]}
      onLanguageChange={setLang}
      onNavigate={(href) => {
        if (typeof window !== "undefined" && window.parent !== window) {
          goViaStage(href);
          return;
        }
        router.push(href);
      }}
      pathname={pathname}
      deskLabel={deskLabel}
      theme={readConsoleTheme()}
      title={titleFor(pathname, tx.titles)}
      chromeCopy={{
        expand: tx.expand,
        collapse: tx.collapse,
        search: tx.search,
        themeLight: tx.themeLight,
        themeDark: tx.themeDark,
        langEn: tx.langEn,
        langHi: tx.langHi,
        langGroup: tx.langGroup,
        deskSuffix: tx.deskSuffix,
      }}
    >
      {children}
    </CommandShell>
  );
}
