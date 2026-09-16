import { CaseCard, EscalationLadder, SlaTimer } from "@manobal/ui";

export default function MedicalPage() {
  return (
    <div className="mb-home-stack">
      <SlaTimer label="T4 acknowledge" remainingLabel="12:40" urgent />
      <EscalationLadder
        current="Call"
        steps={["Acknowledge", "Call", "Hand off", "Outcome"]}
      />
      <CaseCard
        caseId="Case 9A01"
        domains={["Crisis gate"]}
        drift="Acute path opened 3 minutes ago"
        lever="Immediate human contact"
        limited={false}
        sla="12:40"
        source="Independent gates"
        status="Unacknowledged"
        tier="T4"
        trajectory="rising"
      />
    </div>
  );
}
