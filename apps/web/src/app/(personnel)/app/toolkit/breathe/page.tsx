"use client";

import { BreathGuide } from "@manobal/ui";
import Link from "next/link";

export default function BreathePage() {
  return (
    <main className="mb-breathe">
      <h1>Box breathing</h1>
      <Link className="mb-ghost mb-breathe-exit" href="/app/toolkit">
        Close
      </Link>
      <BreathGuide title="Box breathing" />
    </main>
  );
}
