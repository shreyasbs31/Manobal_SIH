"use client";

import { BreathGuide } from "@manobal/ui";

import { ScreenExit } from "@/components/screen-exit";
import { usePersonnelI18n } from "@/lib/personnel-i18n";

export default function BreathePage() {
  const { p } = usePersonnelI18n();
  return (
    <main className="mb-breathe">
      <h1 className="mb-sr-only">{p("Box breathing")}</h1>
      <div className="mb-breathe-nav">
        <ScreenExit backHref="/app/toolkit" />
      </div>
      <BreathGuide title={p("Box breathing")} translateLabel={p} />
    </main>
  );
}
