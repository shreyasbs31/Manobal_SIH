"use client";

import {
  AuditRow,
  ChainStatus,
  FairnessBar,
  KpiTile,
  ProviderBadge,
} from "@manobal/ui";

import { ScreenState } from "@/components/screen-state";
import { useEngine } from "@/lib/use-engine";

export default function GovernancePage() {
  const { data, error, loading, offline } = useEngine("governance", async (client, signal) => {
    const [kpis, fairness, switches] = await Promise.all([
      client.govOverview(signal),
      client.govFairness(signal),
      client.govKillswitches(signal),
    ]);
    return { kpis, fairness, switches };
  });

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={!data}>
      {data ? (
        <div>
          <div className="mb-kpi-row">
            {data.kpis.kpis.map((kpi) => (
              <KpiTile hint={kpi.hint} key={kpi.label} label={kpi.label} value={kpi.value} />
            ))}
          </div>
          <div className="mb-grid-12">
            {data.fairness.fairness.map((row) => (
              <div className="mb-span-6" key={row.label}>
                <FairnessBar label={row.label} ratio={row.ratio} />
              </div>
            ))}
            <div className="mb-span-12 mb-card">
              <h2>Audit chain</h2>
              <ChainStatus mode="intact" />
              <AuditRow action="anchor.daily" token="tok_aa19" when="06:00" />
              <ProviderBadge name="Azure Speech" />
            </div>
            <div className="mb-span-12 mb-card">
              <h2>Kill switches</h2>
              {Object.entries(data.switches).map(([name, enabled]) => (
                <div className="mb-kill" key={name}>
                  <span>{name}</span>
                  <button className="mb-toggle" type="button">
                    {enabled ? "On" : "Off"}
                  </button>
                </div>
              ))}
              <div className="mb-kill" data-locked="true">
                <span>Acute path</span>
                <button aria-disabled="true" className="mb-toggle" disabled type="button">
                  Always on
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </ScreenState>
  );
}
