"use client";

import { ScreenNav, goHref, popPathStack, resetPathStack } from "@manobal/ui";
import { usePathname } from "next/navigation";

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
  const pathname = usePathname();
  return (
    <ScreenNav
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
