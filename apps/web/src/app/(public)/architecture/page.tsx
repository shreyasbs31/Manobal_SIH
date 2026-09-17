"use client";

import { PublicHeader } from "@manobal/ui";

import { ScreenState } from "@/components/screen-state";
import { engineClient } from "@/lib/engine";
import { manobalMode } from "@/lib/mode";
import { useEngine } from "@/lib/use-engine";

const LAYERS = [
  { title: "Device", detail: "Saathi PWA, offline packet, on-device gates" },
  { title: "Unit server", detail: "Sync, lexicon, companion, alerts" },
  { title: "Analytics", detail: "Baselines, CUSUM, forecast. No vault keys." },
  { title: "Identity vault", detail: "Names stay here. Envelope encryption." },
] as const;

export default function ArchitecturePage() {
  const live = useEngine("architecture-live", (client, signal) => client.publicArchitecture(signal));
  const selftest = useEngine("selftest", (client, signal) => client.systemSelftest(signal));
  const mode = useEngine("system-mode", (client, signal) => client.systemMode(signal));

  return (
    <div className="mb-theme mb-arch" data-skin="command" data-theme="dark">
      <PublicHeader mode={manobalMode()} />
      <main className="mb-command-body">
        <h1 className="mb-type-title">Separated by design</h1>
        <p>
          Live self-tests prove the engine cannot reach identity storage or its keys. Command routes
          never accept a person, case, or token parameter.
        </p>
        <p className="mb-hosting-caption">
          Prototype: open-weight model hosted on Azure. Deployable on force servers.
        </p>
        <div className="mb-layers" data-link={live.data?.edge_up ? "up" : "down"}>
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
          {(live.data?.packets ?? []).map((packet) => (
            <span
              aria-hidden="true"
              className={packet.kind.includes("vault") ? "mb-packet mb-packet-key" : "mb-packet"}
              data-held={packet.held ? "true" : "false"}
              key={packet.id}
            />
          ))}
        </div>
        <section>
          <h2>Edge queue</h2>
          <p>
            Unit server link is {live.data?.edge_up ? "up" : "down"}. Held packets:{" "}
            {live.data?.queued ?? 0}.
          </p>
          <div className="mb-action-row">
            <button
              className="mb-secondary"
              onClick={() => {
                void engineClient()
                  .setEdgeLink(!(live.data?.edge_up ?? true))
                  .then(() => live.reload());
              }}
              type="button"
            >
              Toggle unit server link
            </button>
          </div>
        </section>
        <section>
          <h2>Self-test</h2>
          <ScreenState error={selftest.error} loading={selftest.loading} offline={selftest.offline}>
            <p>
              Stack:{" "}
              {selftest.data
                ? selftest.data.healthy
                  ? "healthy"
                  : "not healthy"
                : "checking"}
              {selftest.data
                ? `. Core database ${selftest.data.core_database_reachable ? "reachable" : "down"}.`
                : ""}
            </p>
            <ul>
              <li>
                Engine has no vault database access
                {selftest.data
                  ? `: ${selftest.data.vault_database_isolated ? "held" : "failed"}`
                  : ""}
              </li>
              <li>Command URL scan rejects case and person parameters</li>
              <li>
                Zone X unreachable
                {selftest.data ? `: ${selftest.data.zone_x_unreachable ? "held" : "failed"}` : ""}
              </li>
              <li>Acute path cannot be switched off</li>
            </ul>
          </ScreenState>
        </section>
        <section className="mb-mode-panel">
          <h2>Mode</h2>
          <p>Runtime: {mode.data?.mode ?? manobalMode()}.</p>
          <p>Foundry: {mode.data?.foundry ? "configured" : "unset, local fallback"}.</p>
          <p>Speech: {mode.data?.speech ? "configured" : "unset, silent WAV"}.</p>
          <p>ACS: {mode.data?.acs ? "configured" : "unset, labelled demo join"}.</p>
        </section>
      </main>
    </div>
  );
}
