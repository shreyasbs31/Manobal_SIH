"use client";

import type { WelfareCase } from "@manobal/contracts";
import { CaseCard, CaseStrip, SlaTimer } from "@manobal/ui";
import { useEffect, useMemo, useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { useEngine } from "@/lib/use-engine";

export default function WelfarePage() {
  const { data, error, loading, offline } = useEngine("welfare-queue", (client, signal) =>
    client.welfareQueue(signal),
  );
  const queue = data ?? [];
  const [selected, setSelected] = useState("");
  useEffect(() => {
    if (!selected && queue[0]) {
      setSelected(queue[0].case_id);
    }
  }, [queue, selected]);
  const current = useMemo(
    () => queue.find((item) => item.case_id === selected) ?? queue[0],
    [queue, selected],
  );
  const t4 = queue.filter((item) => item.tier === "T4");
  const t3 = queue.filter((item) => item.tier === "T3");
  const t2 = queue.filter((item) => item.tier === "T2");

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "j" && event.key !== "k" && event.key !== "Enter") {
        return;
      }
      const index = queue.findIndex((item) => item.case_id === selected);
      if (event.key === "j") {
        const next = queue[Math.min(index + 1, queue.length - 1)];
        if (next) setSelected(next.case_id);
      }
      if (event.key === "k") {
        const next = queue[Math.max(index - 1, 0)];
        if (next) setSelected(next.case_id);
      }
      if (event.key === "Enter" && selected) {
        window.location.assign(`/welfare/cases/${selected}`);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [queue, selected]);

  const groups = [
    { label: "Urgent", items: t4 },
    { label: "High", items: t3 },
    { label: "Elevated", items: t2 },
  ] as const;

  return (
    <ScreenState
      empty={queue.length === 0}
      emptyText="No open cases in this unit."
      error={error}
      loading={loading}
      offline={offline}
    >
      <div>
        {t4[0] ? (
          <div className="mb-t4-banner" role="status">
            Acute case {t4[0].case_id}. Acknowledge within {t4[0].sla_label}.
          </div>
        ) : null}
        <p className="mb-queue-meta">
          <span>Open {queue.length}</span>
          <span>Overdue 0</span>
          <span>My load {queue.length} of 25</span>
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
                  </a>
                ))}
              </section>
            ))}
          </div>
          {current ? <QueueAside current={current} /> : null}
        </div>
      </div>
    </ScreenState>
  );
}

function QueueAside({ current }: { current: WelfareCase }) {
  return (
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
  );
}
