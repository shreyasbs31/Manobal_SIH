"use client";

import { PublicHeader } from "@manobal/ui";

import { ScreenState } from "@/components/screen-state";
import { useEngine } from "@/lib/use-engine";
import { manobalMode } from "@/lib/mode";

const LAYERS = [
  { title: "Device", detail: "Saathi PWA, offline packet, on-device gates" },
  { title: "Unit server", detail: "Sync, lexicon, companion, alerts" },
  { title: "Analytics", detail: "Baselines, CUSUM, forecast. No vault keys." },
  { title: "Identity vault", detail: "Names stay here. Envelope encryption." },
] as const;

export default function ArchitecturePage() {
  const { data, error, loading, offline } = useEngine("selftest", (client, signal) =>
    client.systemSelftest(signal),
  );

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
          <ScreenState error={error} loading={loading} offline={offline}>
            <ul>
              <li>
                Engine has no vault database access
                {data ? `: ${data.vault_database_isolated ? "held" : "failed"}` : ""}
              </li>
              <li>Command URL scan rejects case and person parameters</li>
              <li>
                Zone X unreachable
                {data ? `: ${data.zone_x_unreachable ? "held" : "failed"}` : ""}
              </li>
              <li>Acute path cannot be switched off</li>
            </ul>
          </ScreenState>
        </section>
        <p>Mode: demo. Synthetic data only.</p>
      </main>
    </div>
  );
}
