"use client";

import { CaseCard, EscalationLadder, SlaTimer, chimeKindForQueue, playConsoleChime } from "@manobal/ui";
import { useEffect } from "react";

import { ScreenState } from "@/components/screen-state";
import { engineClient } from "@/lib/engine";
import { useEngine } from "@/lib/use-engine";

export default function MedicalPage() {
  const { data, error, loading, offline, reload } = useEngine("medical-acute", (client, signal) =>
    client.medicalAcute(signal),
  );
  const extra = useEngine("medical-referrals", (client, signal) => client.medicalReferrals(signal));
  const items = data ?? [];

  useEffect(() => {
    const t4 = items.filter((item) => item.tier === "T4").length;
    const kind = chimeKindForQueue(t4, 0);
    if (kind) {
      playConsoleChime(kind);
    }
  }, [items]);

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
              current={item.status === "ack" ? "Battalion MO" : "waiting"}
              steps={[
                { role: "UWO", status: "notified", time: "09:41" },
                { role: "Company welfare deputy", status: "waiting", time: "" },
                {
                  role: "Battalion MO",
                  status: item.status === "ack" ? "acknowledged" : "waiting",
                  time: item.status === "ack" ? "now" : "",
                },
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
        <details>
          <summary>Referrals and guide</summary>
          {extra.data?.items.map((item) => (
            <p key={item.case_id}>
              From {item.from}. {item.case_id}. {item.context}
            </p>
          ))}
          {extra.data ? (
            <>
              <h2>{extra.data.guide.title}</h2>
              <ol>
                {extra.data.guide.steps.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>
              <p>{extra.data.guide.note}</p>
            </>
          ) : null}
        </details>
      </div>
    </ScreenState>
  );
}
