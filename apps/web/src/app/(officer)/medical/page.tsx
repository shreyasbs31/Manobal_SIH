"use client";

import { CaseCard, EscalationLadder, SlaTimer } from "@manobal/ui";

import { ScreenState } from "@/components/screen-state";
import { engineClient } from "@/lib/engine";
import { useEngine } from "@/lib/use-engine";

export default function MedicalPage() {
  const { data, error, loading, offline, reload } = useEngine("medical-acute", (client, signal) =>
    client.medicalAcute(signal),
  );
  const items = data ?? [];

  return (
    <ScreenState
      empty={items.length === 0}
      emptyText="No acute cases."
      error={error}
      loading={loading}
      offline={offline}
    >
      <div className="mb-acute-board">
        {items.map((item) => (
          <article key={item.case_id}>
            <SlaTimer
              label="Acknowledge"
              remainingLabel={item.sla_label}
              remainingRatio={item.remaining_ratio}
              tier="T4"
            />
            <CaseCard
              caseId={item.case_id}
              domains={[...item.drivers]}
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
            <button
              className="mb-primary mb-ack"
              onClick={() => {
                void engineClient()
                  .medicalAck(item.case_id)
                  .then(() => reload());
              }}
              type="button"
            >
              Acknowledge
            </button>
          </article>
        ))}
      </div>
    </ScreenState>
  );
}
