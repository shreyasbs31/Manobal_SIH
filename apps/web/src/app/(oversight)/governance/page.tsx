import { governanceOverview } from "@manobal/contracts";
import {
  AuditRow,
  ChainStatus,
  FairnessBar,
  KpiTile,
  ProviderBadge,
} from "@manobal/ui";

export default function GovernancePage() {
  return (
    <div>
      <div className="mb-kpi-row">
        {governanceOverview.kpis.map((kpi) => (
          <KpiTile hint={kpi.hint} key={kpi.label} label={kpi.label} value={kpi.value} />
        ))}
      </div>
      <div className="mb-grid-12">
        {governanceOverview.fairness.map((row) => (
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
          <div className="mb-kill">
            <span>Forecast briefs</span>
            <button className="mb-toggle" type="button">
              On
            </button>
          </div>
          <div className="mb-kill">
            <span>Companion chat</span>
            <button className="mb-toggle" type="button">
              On
            </button>
          </div>
          <div className="mb-kill" data-locked="true">
            <span>Acute path</span>
            <button aria-disabled="true" className="mb-toggle" disabled type="button">
              Always on
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
