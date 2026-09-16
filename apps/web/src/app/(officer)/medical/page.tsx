import { medicalAcute } from "@manobal/contracts";
import { CaseCard, EscalationLadder, SlaTimer } from "@manobal/ui";

export default function MedicalPage() {
  const acute = medicalAcute[0];
  if (!acute) {
    return <p>No acute cases.</p>;
  }
  return (
    <div className="mb-acute-board">
      {medicalAcute.map((item) => (
        <article key={item.case_id}>
          <SlaTimer
            label="Acknowledge"
            remainingLabel={item.sla_label}
            remainingRatio={item.remaining_ratio}
            tier="T4"
          />
          <CaseCard
            caseId={item.case_id}
            domains={item.drivers}
            drift={item.drift}
            lever={item.lever_title}
            limited={item.limited}
            remainingRatio={item.remaining_ratio}
            sla={item.sla_label}
            source={item.source}
            status={item.status}
            tier={item.tier}
            trajectory={item.trajectory}
          />
          <EscalationLadder
            steps={[
              { role: "UWO", status: "notified", time: "09:41" },
              { role: "Company welfare deputy", status: "waiting", time: "" },
              { role: "Battalion MO", status: "waiting", time: "" },
              { role: "Sector counsellor", status: "waiting", time: "" },
            ]}
          />
          <button className="mb-primary mb-ack" type="button">
            Acknowledge
          </button>
        </article>
      ))}
    </div>
  );
}
