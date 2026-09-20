"use client";

import { BreathGuide } from "@manobal/ui";

import { ScreenExit } from "@/components/screen-exit";

export default function BreathePage() {
  return (
    <main className="mb-breathe">
      <h1 className="mb-sr-only">Box breathing</h1>
      <div className="mb-breathe-nav">
        <ScreenExit backHref="/app/toolkit" />
      </div>
      <BreathGuide title="Box breathing" />
    </main>
  );
}
