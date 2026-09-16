import { KpiTile, ReliabilityChart } from "@manobal/ui";

export default function LabPage() {
  return (
    <div className="mb-grid-12">
      <div className="mb-span-12">
        <p>Primary and shifted synthetic worlds are reported side by side. Numbers belong here, not on command screens.</p>
      </div>
      <div className="mb-span-4">
        <KpiTile hint="T2+" label="Precision" value="0.81" />
      </div>
      <div className="mb-span-4">
        <KpiTile hint="T2+" label="Recall" value="0.76" />
      </div>
      <div className="mb-span-4">
        <KpiTile hint="Days" label="Median lead time" value="6.5" />
      </div>
      <div className="mb-span-12 mb-card">
        <h2>Reliability, primary world</h2>
        <ReliabilityChart
          points={[
            { predicted: 0.15, observed: 0.14 },
            { predicted: 0.45, observed: 0.41 },
            { predicted: 0.75, observed: 0.7 },
          ]}
        />
      </div>
    </div>
  );
}
