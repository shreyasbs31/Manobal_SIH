import { FairnessBar, KpiTile } from "@manobal/ui";

export default function HqPage() {
  return (
    <div className="mb-grid-12">
      <div className="mb-span-12">
        <p>Theatre comparison stays grouped. Cells under the minimum size stay hidden.</p>
      </div>
      <div className="mb-span-4">
        <KpiTile hint="18-month view" label="Leave backlog" value="High in sector N" />
      </div>
      <div className="mb-span-4">
        <KpiTile hint="Observational" label="Welfare capacity" value="Stretched" />
      </div>
      <div className="mb-span-4">
        <KpiTile hint="k-anonymous" label="Open grievance age" value="21 days" />
      </div>
      <div className="mb-span-12">
        <FairnessBar label="Posture share across theatres" ratio={1.04} />
      </div>
    </div>
  );
}
