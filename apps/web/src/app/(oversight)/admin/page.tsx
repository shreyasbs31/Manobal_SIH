import { EmptyState, MachineTranslatedBadge, ValidatedBadge } from "@manobal/ui";

export default function AdminPage() {
  return (
    <div className="mb-home-stack">
      <p>Language catalog and reviewed content live here. The acute path is not listed as a flag.</p>
      <div className="mb-action-row">
        <ValidatedBadge />
        <MachineTranslatedBadge />
      </div>
      <EmptyState message="Synthetic org tree and officer assignments load with seed data." title="Configuration" />
    </div>
  );
}
