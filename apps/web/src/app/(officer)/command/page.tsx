import {
  DomainChip,
  DriverList,
  FormationGrid,
  KpiTile,
} from "@manobal/ui";

const units = ["Company A", "Company B", "Company C", "Company D"] as const;
const cells = units.flatMap((unit) =>
  Array.from({ length: 12 }, (_, index) => {
    const week = index + 1;
    const hidden = unit === "Company D" && week > 7;
    return {
      unit,
      week,
      band: hidden ? ("hidden" as const) : week > 10 ? ("T2" as const) : week > 6 ? ("T1" as const) : ("T0" as const),
      shareLabel: hidden ? undefined : week > 10 ? "T2+ higher" : "typical",
    };
  }),
);

export default function CommandPage() {
  return (
    <div className="mb-grid-12">
      <div className="mb-span-12">
        <p>
          Nothing on this surface resolves to a person. Hidden tiles are groups
          too small to show.
        </p>
      </div>
      <div className="mb-span-12 mb-card">
        <h2>Formation, 12 weeks</h2>
        <FormationGrid cells={cells} units={units} weeks={12} />
      </div>
      <div className="mb-span-3">
        <KpiTile hint="Company median" label="Duty hours this week" value="68" />
      </div>
      <div className="mb-span-3">
        <KpiTile hint="Unit aggregate" label="Rest denials" value="12" />
      </div>
      <div className="mb-span-3">
        <KpiTile hint="Night share" label="Night load" value="31%" />
      </div>
      <div className="mb-span-3">
        <KpiTile hint="k-anonymous" label="Median days since leave" value="46" />
      </div>
      <div className="mb-span-6 mb-card">
        <h2>Aggregate drivers</h2>
        <DriverList items={["Roster overtime", "Sleep loss", "Leave backlog"]} />
        <div className="mb-action-row">
          <DomainChip label="Roster" />
          <DomainChip label="Sleep" />
          <DomainChip label="Leave" />
        </div>
      </div>
      <div className="mb-span-6 mb-card">
        <h2>Copilot</h2>
        <p>Ask about the unit, never about a person. Press Control K to jump.</p>
      </div>
    </div>
  );
}
