import { SimClock } from "@manobal/ui";
import type { Metadata } from "next";
import Link from "next/link";

import { ConsoleChrome } from "@/components/console-chrome";

export const metadata: Metadata = { title: "Demo director" };

export default function DirectorPage() {
  return (
    <ConsoleChrome>
      <div className="mb-home-stack">
        <SimClock playing value="2026-09-16 10:00 IST" />
        <div className="mb-action-row">
          <button className="mb-secondary" type="button">
            Pause
          </button>
          <button className="mb-secondary" type="button">
            +1 day
          </button>
          <button className="mb-secondary" type="button">
            +1 week
          </button>
          <button className="mb-primary" type="button">
            Run nightly scoring now
          </button>
        </div>
        <p>Stage presets open the phone and a console together.</p>
        <Link className="mb-primary" href="/stage?phone=/app&console=/command">
          Open stage
        </Link>
      </div>
    </ConsoleChrome>
  );
}
