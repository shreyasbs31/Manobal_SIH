"use client";

import { CommandShell } from "@manobal/ui";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";

import { currentPrincipal, inStageFrame, setStagePendingPath, waitForStageRole } from "@/lib/engine";
import { readConsoleTheme, useConsoleLang } from "@/lib/console-i18n";
import { manobalMode } from "@/lib/mode";
import { roleForPath } from "@/lib/stage-role";

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
    for (const item of tx.nav) {
      router.prefetch(item.href);
    }
  }, [router, tx.nav]);

  useEffect(() => {
    if (typeof window === "undefined" || window.parent === window) {
      return;
    }
    window.parent.postMessage(
      { type: "manobal.stage.console-path", path: pathname, frame: window.name },
      window.location.origin,
    );
  }, [pathname]);

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
        if (inStageFrame()) {
          const needed = roleForPath(href);
          const role = currentPrincipal()?.role;
          if (needed !== "any" && needed !== "personnel" && role && needed !== role) {
            void waitForStageRole(href).then(() => {
              router.push(href);
              window.setTimeout(() => setStagePendingPath(null), 600);
            });
            return;
          }
        }
        router.push(href);
      }}
      pathname={pathname}
      deskLabel={deskLabel}
      theme={readConsoleTheme()}
      title={titleFor(pathname, tx.titles)}
      units={[tx.units["Bn C-02"] ?? "Bn C-02", tx.units["Charlie Coy"] ?? "Charlie Coy", tx.units["Alpha Coy"] ?? "Alpha Coy"]}
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
        simulated: tx.simulated,
        skip: tx.skip,
        theme: tx.theme,
        unitScope: tx.unitScope,
        soundOn: tx.soundOn,
        soundOff: tx.soundOff,
        palette: tx.palette,
      }}
    >
      {children}
    </CommandShell>
  );
}
