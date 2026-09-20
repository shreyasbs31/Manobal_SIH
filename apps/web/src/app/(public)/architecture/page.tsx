"use client";

import { useState } from "react";

import { ConsoleChrome } from "@/components/console-chrome";
import { ScreenState } from "@/components/screen-state";
import { engineClient } from "@/lib/engine";
import { useEngine } from "@/lib/use-engine";

const LAYERS = [
  { title: "Phone", detail: "Check-ins and talks stay on the phone when there is no network." },
  { title: "Unit", detail: "The unit keeps sync, alerts, and Saathi replies." },
  { title: "Patterns", detail: "Looks at unit patterns, never names." },
  { title: "Names", detail: "Names stay locked until a welfare officer needs to reach someone." },
] as const;

export default function ArchitecturePage() {
  const live = useEngine("architecture-live", (client, signal) => client.publicArchitecture(signal));
  const selftest = useEngine("selftest", (client, signal) => client.systemSelftest(signal));
  const [layer, setLayer] = useState<(typeof LAYERS)[number]["title"] | "Zone X">("Phone");
  const selected = LAYERS.find((item) => item.title === layer);

  return (
    <ConsoleChrome>
      <div className="mb-desk mb-desk-fill mb-arch">
        <div className="mb-layers" data-link={live.data?.edge_up ? "up" : "down"}>
          {LAYERS.map((item) => (
            <button
              aria-pressed={layer === item.title}
              className="mb-layer"
              key={item.title}
              onClick={() => setLayer(item.title)}
              type="button"
            >
              <h2>{item.title}</h2>
              <p>{item.detail}</p>
            </button>
          ))}
          <button
            aria-pressed={layer === "Zone X"}
            className="mb-layer"
            data-blocked="true"
            onClick={() => setLayer("Zone X")}
            type="button"
          >
            <h2>Never connected</h2>
            <p>Appraisal, promotion, posting, and discipline have no path in.</p>
          </button>
          {(live.data?.packets ?? []).map((packet) => (
            <span
              aria-hidden="true"
              className={packet.kind.includes("vault") ? "mb-packet mb-packet-key" : "mb-packet"}
              data-held={packet.held ? "true" : "false"}
              key={packet.id}
            />
          ))}
        </div>
        <aside className="mb-sheet">
          <h2>{layer === "Zone X" ? "Never connected" : layer}</h2>
          <p>
            {layer === "Zone X"
              ? "Nothing here can be used for posting, promotion, or discipline."
              : selected?.detail}
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
              {live.data?.edge_up ? "Hold the unit link" : "Restore the unit link"}
            </button>
            <button className="mb-ghost" onClick={() => selftest.reload()} type="button">
              Run self-test
            </button>
          </div>
          <ScreenState error={selftest.error} loading={selftest.loading} offline={selftest.offline}>
            <ul className="mb-selftest">
              <li>{selftest.data?.healthy ? "Services are up" : selftest.data ? "Services need attention" : "Checking"}</li>
              <li>{selftest.data?.vault_database_isolated ? "Names stay separate" : "Checking names"}</li>
              <li>
                {selftest.data?.zone_x_unreachable
                  ? "Appraisal systems cannot connect"
                  : "Checking the closed path"}
              </li>
            </ul>
          </ScreenState>
        </aside>
      </div>
    </ConsoleChrome>
  );
}
