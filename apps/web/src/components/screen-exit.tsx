"use client";

import { ScreenNav, goHref, popPathStack, resetPathStack } from "@manobal/ui";
import { usePathname } from "next/navigation";

import { usePersonnelI18n } from "@/lib/personnel-i18n";

const SAATHI_STACK = "manobal.nav.saathi";

export function ScreenExit({
  backHref,
  closeHref = "/app",
  title,
}: {
  backHref: string;
  closeHref?: string;
  title?: string;
}) {
  const { p } = usePersonnelI18n();
  const pathname = usePathname();
  return (
    <ScreenNav
      backLabel={p("Back")}
      closeLabel={p("Close")}
      onBack={() => {
        popPathStack(SAATHI_STACK, pathname, closeHref);
        goHref(backHref);
      }}
      onClose={() => goHref(resetPathStack(SAATHI_STACK, closeHref))}
      showBack
      showClose
      title={title}
    />
  );
}
