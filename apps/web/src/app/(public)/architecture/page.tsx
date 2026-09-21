"use client";

import { useMemo, useState } from "react";

import { ConsoleChrome } from "@/components/console-chrome";
import { ScreenState } from "@/components/screen-state";
import { useConsoleLang } from "@/lib/console-i18n";
import { engineClient } from "@/lib/engine";
import { useEngine } from "@/lib/use-engine";

export default function ArchitecturePage() {
  const { tx } = useConsoleLang();
  const live = useEngine("architecture-live", (client, signal) => client.publicArchitecture(signal));
  const selftest = useEngine("selftest", (client, signal) => client.systemSelftest(signal));
  const layers = useMemo(
    () =>
      [
        { id: "0", title: tx.archPhone, detail: tx.archPhoneDetail, key: "Phone" as const },
        { id: "1", title: tx.archUnit, detail: tx.archUnitDetail, key: "Unit" as const },
        { id: "2", title: tx.archPatterns, detail: tx.archPatternsDetail, key: "Patterns" as const },
        { id: "3", title: tx.archNames, detail: tx.archNamesDetail, key: "Names" as const },
      ] as const,
    [tx],
  );
  const [layer, setLayer] = useState<(typeof layers)[number]["key"] | "Zone X">("Phone");
  const selected = layers.find((item) => item.key === layer);
  const held = (live.data?.packets ?? []).filter((packet) => packet.held).length;
  const modeLabel = live.data?.mode === "sovereign" ? tx.archSovereign : tx.archDemo;

  return (
    <ConsoleChrome>
      <div className="mb-desk mb-desk-fill mb-arch">
        <div className="mb-arch-main">
          <p className="mb-desk-purpose">{tx.archPurpose}</p>
          <div className="mb-layers" data-link={live.data?.edge_up ? "up" : "down"}>
            {layers.map((item) => (
              <button
                aria-pressed={layer === item.key}
                className="mb-layer"
                key={item.key}
                onClick={() => setLayer(item.key)}
                type="button"
              >
                <span>
                  {tx.archZone} {item.id}
                </span>
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
              <span>{tx.archZone} X</span>
              <h2>{tx.archNever}</h2>
              <p>{tx.archNeverDetail}</p>
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
        </div>
        <aside className="mb-sheet">
          <h2>{layer === "Zone X" ? tx.archNever : selected?.title}</h2>
          <p>
            {layer === "Zone X"
              ? tx.archNeverDetail
              : selected?.detail}
          </p>
          <p>
            {tx.archQueue}: {live.data?.queued ?? 0} {tx.archHeld}
            {held ? ` (${held})` : ""}.
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
              {live.data?.edge_up ? tx.archHold : tx.archRestore}
            </button>
            <button className="mb-ghost" onClick={() => selftest.reload()} type="button">
              {tx.archRunTest}
            </button>
          </div>
          <h3>{tx.archSelftest}</h3>
          <ScreenState error={selftest.error} loading={selftest.loading} offline={selftest.offline}>
            <ul className="mb-selftest">
              <li>
                {selftest.data?.healthy ? tx.archUp : selftest.data ? tx.archNeed : tx.archChecking}
              </li>
              <li>{selftest.data?.vault_database_isolated ? tx.archNamesOk : tx.archChecking}</li>
              <li>{selftest.data?.zone_x_unreachable ? tx.archClosed : tx.archChecking}</li>
            </ul>
          </ScreenState>
          <h3>{tx.archMode}</h3>
          <p>
            {modeLabel}. {tx.archModeNote}
          </p>
          <ul className="mb-selftest">
            <li>
              {tx.archFoundry}: {live.data?.foundry ? tx.archLive : tx.archHeld}
            </li>
            <li>
              {tx.archSpeech}: {live.data?.speech ? tx.archLive : tx.archHeld}
            </li>
            <li>
              {tx.archTranslator}: {live.data?.translator ? tx.archLive : tx.archHeld}
            </li>
            <li>
              {tx.archSafety}: {live.data?.content_safety ? tx.archLive : tx.archHeld}
            </li>
          </ul>
        </aside>
      </div>
    </ConsoleChrome>
  );
}
