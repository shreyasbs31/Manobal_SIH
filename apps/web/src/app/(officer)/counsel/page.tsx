import { CallPanel, EmptyState } from "@manobal/ui";

export default function CounselPage() {
  return (
    <div className="mb-home-stack">
      <p>Anonymous and named sessions share only the minimum needed context.</p>
      <CallPanel peer="Anonymous handle" status="Slot open. Notes never leave this desk." />
      <EmptyState message="The calendar fills when bookings arrive." title="No other sessions today" />
    </div>
  );
}
