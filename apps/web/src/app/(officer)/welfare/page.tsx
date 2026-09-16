"use client";

import { welfareQueue } from "@manobal/contracts";
import { CaseCard, CaseStrip, SlaTimer } from "@manobal/ui";
import { useEffect, useMemo, useState } from "react";

const T4 = welfareQueue.filter((item) => item.tier === "T4");
const T3 = welfareQueue.filter((item) => item.tier === "T3");
const T2 = welfareQueue.filter((item) => item.tier === "T2");

export default function WelfarePage() {
  const [selected, setSelected] = useState(welfareQueue[1]?.case_id ?? "MB-4091");
  const current = useMemo(
    () => welfareQueue.find((item) => item.case_id === selected) ?? welfareQueue[0],
    [selected],
  );

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "j" && event.key !== "k" && event.key !== "Enter") {
        return;
      }
      const index = welfareQueue.findIndex((item) => item.case_id === selected);
      if (event.key === "j") {
        const next = welfareQueue[Math.min(index + 1, welfareQueue.length - 1)];
        if (next) setSelected(next.case_id);
      }
      if (event.key === "k") {
        const next = welfareQueue[Math.max(index - 1, 0)];
        if (next) setSelected(next.case_id);
      }
      if (event.key === "Enter") {
        window.location.assign(`/welfare/cases/${selected}`);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selected]);

  const groups = [
    { label: "Urgent", items: T4 },
    { label: "High", items: T3 },
    { label: "Elevated", items: T2 },
  ] as const;

  return (
    <div>
      {T4[0] ? (
        <div className="mb-t4-banner" role="status">
          Acute case {T4[0].case_id}. Acknowledge within {T4[0].sla_label}.
        </div>
      ) : null}
      <p className="mb-queue-meta">
        <span>Open {welfareQueue.length}</span>
        <span>Overdue 1</span>
        <span>My load {welfareQueue.length} of 25</span>
      </p>
      <div className="mb-queue">
        <div>
          {groups.map((group) => (
            <section className="mb-queue-group" key={group.label}>
              <h2>
                {group.label} ({group.items.length})
              </h2>
              {group.items.map((item) => (
                <a
                  href={`/welfare/cases/${item.case_id}`}
                  key={item.case_id}
                  onClick={(event) => {
                    event.preventDefault();
                    setSelected(item.case_id);
                  }}
                  onDoubleClick={() => window.location.assign(`/welfare/cases/${item.case_id}`)}
                >
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
                </a>
              ))}
            </section>
          ))}
        </div>
        {current ? (
          <aside className="mb-card">
            <h2>
              {current.case_id} {current.tier} {current.trajectory}
            </h2>
            <p>{current.drift}</p>
            <CaseStrip
              actions={[110]}
              days={Array.from({ length: 24 }, (_, index) => ({
                day: index * 5,
                tier: current.tier,
              }))}
              incidents={[118]}
              onsetDay={100}
            />
            <p>Recommended: {current.lever_title}</p>
            <SlaTimer
              label="SLA"
              remainingLabel={current.sla_label}
              remainingRatio={current.remaining_ratio}
              tier={current.tier}
            />
            <a className="mb-primary" href={`/welfare/cases/${current.case_id}`}>
              Open case
            </a>
          </aside>
        ) : null}
      </div>
    </div>
  );
}
