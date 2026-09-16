import {
  AuditRow,
  ChainStatus,
  FairnessBar,
  KpiTile,
  ProviderBadge,
  ReliabilityChart,
} from "@manobal/ui";

export default function GovernancePage() {
  return (
    <div className="mb-grid-12">
      <div className="mb-span-3">
        <KpiTile hint="K1" label="Lead time" value="4.2 days" />
      </div>
      <div className="mb-span-3">
        <KpiTile hint="From outcomes" label="False-positive rate" value="0.11" />
      </div>
      <div className="mb-span-3">
        <KpiTile hint="K11" label="Break-glass rate" value="0.4%" />
      </div>
      <div className="mb-span-3">
        <KpiTile hint="K10" label="Trust index" value="Held" />
      </div>
      <div className="mb-span-6">
        <FairnessBar label="Flag rate by rank band" ratio={0.92} />
      </div>
      <div className="mb-span-6 mb-card">
        <h2>Reliability</h2>
        <ReliabilityChart
          points={[
            { predicted: 0.2, observed: 0.19 },
            { predicted: 0.5, observed: 0.46 },
            { predicted: 0.8, observed: 0.73 },
          ]}
        />
      </div>
      <div className="mb-span-12 mb-card">
        <ChainStatus intact />
        <AuditRow action="anchor.daily" token="tok_aa19" when="06:00" />
        <ProviderBadge name="Azure Speech" />
      </div>
    </div>
  );
}
