import { CaseCard } from "@manobal/ui";

export default function WelfarePage() {
  return (
    <div className="mb-home-stack">
      <p>Cases are ordered by due time only. Identity stays locked until a purpose is recorded.</p>
      <CaseCard
        caseId="Case 7F2A"
        domains={["Sleep", "Roster"]}
        drift="Drift began about 18 days ago"
        lever="Rest day restoration"
        limited
        sla="04:10"
        source="Nightly scoring"
        status="Open"
        tier="T3"
        trajectory="rising"
      />
      <CaseCard
        caseId="Case 12C8"
        domains={["Family"]}
        drift="Drift began about 6 days ago"
        lever="Counsellor offer"
        limited={false}
        sla="11:20"
        source="Self-referral"
        status="Open"
        tier="T2"
        trajectory="steady"
      />
    </div>
  );
}
