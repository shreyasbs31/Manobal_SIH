"use client";

import { SimClock } from "@manobal/ui";
import type { Metadata } from "next";
import Link from "next/link";

import { ConsoleChrome } from "@/components/console-chrome";
import { DirectorControls } from "@/components/director-controls";

export const metadata: Metadata = { title: "Demo director" };

export default function DirectorPage() {
  return (
    <ConsoleChrome>
      <div className="mb-home-stack">
        <SimClock playing value="2026-09-16 10:00 IST" />
        <DirectorControls />
        <p>Stage presets open the phone and a console together.</p>
        <Link className="mb-primary" href="/stage?phone=/app&console=/command">
          Open stage
        </Link>
      </div>
    </ConsoleChrome>
  );
}
