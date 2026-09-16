import { PublicHeader } from "@manobal/ui";
import type { Metadata } from "next";

import { manobalMode } from "@/lib/mode";

export const metadata: Metadata = { title: "Architecture" };

const LAYERS = [
  { title: "Device", detail: "Saathi PWA, offline packet, on-device gates" },
  { title: "Unit server", detail: "Sync, lexicon, companion, alerts" },
  { title: "Analytics", detail: "Baselines, CUSUM, forecast. No vault keys." },
  { title: "Identity vault", detail: "Names stay here. Envelope encryption." },
] as const;

export default function ArchitecturePage() {
  return (
    <div className="mb-theme mb-arch" data-skin="command" data-theme="dark">
      <PublicHeader mode={manobalMode()} />
      <main className="mb-command-body">
        <h1 className="mb-type-title">Separated by design</h1>
        <p>
          Live self-tests prove the engine cannot reach identity storage or its keys.
          Command routes never accept a person, case, or token parameter.
        </p>
        <div className="mb-layers">
          {LAYERS.map((layer) => (
            <section className="mb-layer" key={layer.title}>
              <h2>{layer.title}</h2>
              <p>{layer.detail}</p>
            </section>
          ))}
          <section className="mb-layer" data-blocked="true">
            <h2>Zone X</h2>
            <p>Appraisal, promotion, posting, discipline: no connection</p>
          </section>
          <span className="mb-packet" aria-hidden="true" />
          <span className="mb-packet mb-packet-key" aria-hidden="true" />
        </div>
        <section>
          <h2>Self-test</h2>
          <ul>
            <li>Engine has no vault database access</li>
            <li>Command URL scan rejects case and person parameters</li>
            <li>Acute path cannot be switched off</li>
          </ul>
        </section>
        <p>Mode: demo. Synthetic data only.</p>
      </main>
    </div>
  );
}
