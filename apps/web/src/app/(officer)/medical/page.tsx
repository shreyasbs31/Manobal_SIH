"use client";

import { CaseCard, EscalationLadder, SlaTimer, chimeKindForQueue, playConsoleChime } from "@manobal/ui";
import { useEffect, useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { engineClient } from "@/lib/engine";
import { useEngine } from "@/lib/use-engine";

export default function MedicalPage() {
  const { data, error, loading, offline, reload } = useEngine("medical-acute", (client, signal) =>
    client.medicalAcute(signal),
  );
  const extra = useEngine("medical-referrals", (client, signal) => client.medicalReferrals(signal));
  const items = data ?? [];
  const [picked, setPicked] = useState("");

  useEffect(() => {
    const t4 = items.filter((item) => item.tier === "T4").length;
    const kind = chimeKindForQueue(t4, 0);
    if (kind) {
      playConsoleChime(kind);
    }
  }, [items]);

  useEffect(() => {
    if (!picked && items[0]) {
      setPicked(items[0].case_id);
    }
  }, [items, picked]);

  const current = items.find((item) => item.case_id === picked) ?? items[0];

  return (
    <ScreenState
      empty={items.length === 0}
      emptyText="No acute cases."
      error={error}
      loading={loading}
      offline={offline}
    >
      <div className="mb-desk mb-desk-fill">
        <div className="mb-acute-board">
          <div className="mb-acute-list">
            {items.map((item) => (
              <article data-focus={item.case_id === current?.case_id ? "true" : "false"} key={item.case_id}>
                <button className="mb-sheet-head" onClick={() => setPicked(item.case_id)} type="button">
                  <SlaTimer
                    label="Acknowledge"
                    remainingLabel={item.sla_label}
                    remainingRatio={item.remaining_ratio}
                    tier="T4"
                  />
                </button>
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
              </article>
            ))}
          </div>
          {current ? (
            <aside className="mb-sheet">
              <h2>{current.case_id}</h2>
              <SlaTimer
                label="Acknowledge"
                remainingLabel={current.sla_label}
                remainingRatio={current.remaining_ratio}
                tier="T4"
              />
              <EscalationLadder
                current={current.status === "ack" ? "Battalion MO" : "waiting"}
                steps={[
                  { role: "UWO", status: "notified", time: "09:41" },
                  { role: "Company welfare deputy", status: "waiting", time: "" },
                  {
                    role: "Battalion MO",
                    status: current.status === "ack" ? "acknowledged" : "waiting",
                    time: current.status === "ack" ? "now" : "",
                  },
                  { role: "Sector counsellor", status: "waiting", time: "" },
                ]}
              />
              <button
                className="mb-primary mb-ack"
                onClick={() => {
                  void engineClient()
                    .medicalAck(current.case_id)
                    .then(() => reload());
                }}
                type="button"
              >
                {current.status === "ack" ? "Acknowledged" : "Acknowledge"}
              </button>
              {extra.data?.items.length ? (
                <div className="mb-work-list">
                  {extra.data.items.map((item) => (
                    <button
                      className="mb-compare-band"
                      key={item.case_id}
                      onClick={() => setPicked(item.case_id)}
                      type="button"
                    >
                      <span>{item.case_id}</span>
                      <strong>{item.from}</strong>
                      <em>{item.context}</em>
                    </button>
                  ))}
                </div>
              ) : null}
            </aside>
          ) : null}
        </div>
      </div>
    </ScreenState>
  );
}
