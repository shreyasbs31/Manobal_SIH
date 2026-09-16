import { PublicHeader } from "@manobal/ui";
import type { Metadata } from "next";

import { manobalMode } from "@/lib/mode";

export const metadata: Metadata = { title: "Trust centre" };

export default function TrustPage() {
  return (
    <div className="mb-theme mb-landing" data-skin="saathi" data-theme="light">
      <PublicHeader mode={manobalMode()} />
      <main className="mb-landing-hero">
        <h1>What MANOBAL collects, and what it never does</h1>
        <p>
          Your commander never sees you. Welfare officers see a case, not a
          name, until a purpose is recorded. Medical fitness categories never
          mix with this system.
        </p>
        <article className="mb-card">
          <h2>Support, not surveillance</h2>
          <p>
            Check-ins, voice, and toolkit use stay in your control. You can
            pause sync, download receipts, and ask for erasure.
          </p>
        </article>
      </main>
    </div>
  );
}
