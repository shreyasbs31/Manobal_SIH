"use client";

import type { WelfareCase } from "@manobal/contracts";
import { CaseCard, CaseStrip, SlaTimer, chimeKindForQueue, playConsoleChime } from "@manobal/ui";
import { useEffect, useMemo, useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { useEngine } from "@/lib/use-engine";

const TABS = [
  "Queue",
  "Incident check-ins",
  "Self-referrals",
  "Follow-ups due",
  "Closed",
  "Digest",
] as const;

export default function WelfarePage() {
  const { data, error, loading, offline } = useEngine("welfare-queue", (client, signal) =>
    client.welfareQueue(signal),
  );
  const tabs = useEngine("welfare-tabs", (client, signal) => client.welfareTabs(signal));
  const profile = useEngine("officer-profile", (client, signal) => client.officerProfile(signal));
  const queue = data ?? [];
  const [selected, setSelected] = useState("");
  const [tab, setTab] = useState<(typeof TABS)[number]>("Queue");
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
  const meta = tabs.data ?? {};

  useEffect(() => {
    const kind = chimeKindForQueue(t4.length, t3.length);
    if (kind) {
      playConsoleChime(kind);
    }
  }, [t4.length, t3.length]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLElement) {
        const tag = event.target.tagName;
        if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") {
          return;
        }
      }
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
      empty={queue.length === 0 && tab === "Queue"}
      emptyText="No open cases in this unit."
      error={error ?? tabs.error}
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
          <span>Open {String(meta.open ?? queue.length)}</span>
          <span>Overdue {String(meta.overdue ?? 0)}</span>
          <span>My load {String(meta.load ?? queue.length)} of {String(meta.capacity ?? 25)}</span>
          {profile.data ? (
            <span>
              Briefs in {String(profile.data.brief_language)}. Digest {String(profile.data.digest_time)}.
            </span>
          ) : null}
        </p>
        <div className="mb-tabs" role="tablist" aria-label="Welfare views">
          {TABS.map((name) => (
            <button
              aria-selected={tab === name}
              className="mb-ghost"
              key={name}
              onClick={() => setTab(name)}
              role="tab"
              type="button"
            >
              {name}
            </button>
          ))}
        </div>
        {tab === "Queue" ? (
          <div className="mb-queue">
            <div>
              {groups.map((group) => (
                <section className="mb-queue-group" key={group.label}>
                  <h2>
                    {group.label} ({group.items.length})
                  </h2>
                  {group.items.map((item) => (
                    <a
                      data-selected={item.case_id === selected ? "true" : "false"}
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
                        selected={item.case_id === selected}
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
        ) : null}
        {tab === "Incident check-ins" ? (
          <TabList
            empty="No one in this unit has asked to talk."
            items={asRows(meta.incidents, "token")}
          />
        ) : null}
        {tab === "Self-referrals" ? (
          <TabList
            empty="No self-referrals."
            items={asRows(meta.self_referrals, "case_id")}
          />
        ) : null}
        {tab === "Follow-ups due" ? (
          <TabList empty="No follow-ups due." items={asRows(meta.followups, "case_id")} />
        ) : null}
        {tab === "Closed" ? (
          <TabList empty="No closed cases." items={asIdRows(meta.closed)} />
        ) : null}
        {tab === "Digest" ? (
          <TabList empty="No digest items today." items={asIdRows(meta.digest)} />
        ) : null}
        <section>
          <h2>Workload</h2>
          <p className="mb-workload">
            {asNumbers(meta.workload).map((value, index) => (
              <i key={`${value}-${index}`} style={{ height: `${8 + value * 4}px` }} />
            ))}
          </p>
        </section>
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

function asRows(value: unknown, key: string): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => {
    if (typeof item === "string") {
      return item;
    }
    if (item && typeof item === "object" && key in item) {
      return String((item as Record<string, unknown>)[key]);
    }
    return JSON.stringify(item);
  });
}

function asIdRows(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => String(item));
}

function asNumbers(value: unknown): number[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => Number(item) || 0);
}

function TabList({ items, empty }: { items: string[]; empty: string }) {
  if (items.length === 0) {
    return <p>{empty}</p>;
  }
  return (
    <ul>
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}