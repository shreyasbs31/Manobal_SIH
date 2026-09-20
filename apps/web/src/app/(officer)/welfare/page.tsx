"use client";

import type { WelfareCase } from "@manobal/contracts";
import { CaseCard, CaseStrip, SlaTimer, chimeKindForQueue, playConsoleChime } from "@manobal/ui";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { engineClient } from "@/lib/engine";
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
  const router = useRouter();
  const { data, error, loading, offline, reload } = useEngine("welfare-queue", (client, signal) =>
    client.welfareQueue(signal),
  );
  const tabs = useEngine("welfare-tabs", (client, signal) => client.welfareTabs(signal));
  const profile = useEngine("officer-profile", (client, signal) => client.officerProfile(signal));
  const queue = data ?? [];
  const [selected, setSelected] = useState("");
  const [tab, setTab] = useState<(typeof TABS)[number]>("Queue");
  const [done, setDone] = useState<Record<string, string>>({});
  const [notice, setNotice] = useState("");
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
        router.push(`/welfare/cases/${selected}`);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [queue, router, selected]);

  const groups = [
    { label: "Urgent", items: t4 },
    { label: "High", items: t3 },
    { label: "Elevated", items: t2 },
  ] as const;

  async function act(caseId: string, outcome: string, label: string) {
    try {
      await engineClient().welfareAction(caseId, {
        mode: "call",
        lever: "REST_48H",
        outcome,
        follow_up: outcome === "done" ? "closed" : "D+2",
        refer: "",
      });
      setDone((currentDone) => ({ ...currentDone, [caseId]: label }));
      setNotice(label);
      reload();
      tabs.reload();
    } catch (caught: unknown) {
      setNotice(caught instanceof Error ? caught.message : "Could not update that case.");
    }
  }

  return (
    <ScreenState
      empty={queue.length === 0 && tab === "Queue"}
      emptyText="No open cases in this unit."
      error={error ?? tabs.error}
      loading={loading}
      offline={offline}
    >
      <div className="mb-desk">
        {t4[0] ? (
          <div className="mb-t4-banner" role="status">
            Acute case {t4[0].case_id}. Acknowledge within {t4[0].sla_label}.
          </div>
        ) : null}
        <p className="mb-queue-meta">
          <span>Open {String(meta.open ?? queue.length)}</span>
          <span>Overdue {String(meta.overdue ?? 0)}</span>
          <span>
            My load {String(meta.load ?? queue.length)} of {String(meta.capacity ?? 25)}
          </span>
          {profile.data ? <span>Digest at {String(profile.data.digest_time)}</span> : null}
        </p>
        {notice ? <p role="status">{notice}</p> : null}
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
                      onDoubleClick={() => router.push(`/welfare/cases/${item.case_id}`)}
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
            {current ? (
              <QueueAside
                current={current}
                onRest={() => void act(current.case_id, "open", "48-hour rest logged.")}
                onRefer={() => void act(current.case_id, "referred", "Referred to counsellor.")}
              />
            ) : null}
          </div>
        ) : null}
        {tab === "Incident check-ins" ? (
          <TabCards
            done={done}
            empty="No one in this unit has asked to talk after an incident."
            items={asObjects(meta.incidents)}
            kind="incident"
            onAction={(caseId) => void act(caseId, "open", "Picked up after the incident.")}
          />
        ) : null}
        {tab === "Self-referrals" ? (
          <TabCards
            done={done}
            empty="No self-referrals."
            items={asObjects(meta.self_referrals)}
            kind="referral"
            onAction={(caseId) => void act(caseId, "open", "Self-referral picked up.")}
          />
        ) : null}
        {tab === "Follow-ups due" ? (
          <TabCards
            done={done}
            empty="No follow-ups due."
            items={asObjects(meta.followups)}
            kind="followup"
            onAction={(caseId) => void act(caseId, "done", "Follow-up closed.")}
          />
        ) : null}
        {tab === "Closed" ? (
          <TabCards
            done={done}
            empty="No closed cases."
            items={asIdObjects(meta.closed)}
            kind="closed"
          />
        ) : null}
        {tab === "Digest" ? (
          <TabCards
            done={done}
            empty="No digest items today."
            items={asIdObjects(meta.digest)}
            kind="digest"
            onAction={(caseId) => void act(caseId, "open", "Digest item opened.")}
          />
        ) : null}
        <p className="mb-workload" aria-label="Workload this week">
          {asNumbers(meta.workload).map((value, index) => (
            <i key={`${value}-${index}`} style={{ height: `${8 + value * 4}px` }} />
          ))}
        </p>
      </div>
    </ScreenState>
  );
}

function QueueAside({
  current,
  onRest,
  onRefer,
}: {
  current: WelfareCase;
  onRest: () => void;
  onRefer: () => void;
}) {
  return (
    <aside className="mb-sheet">
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
      <div className="mb-action-row">
        <a className="mb-primary" href={`/welfare/cases/${current.case_id}`}>
          Open case
        </a>
        <button className="mb-secondary" onClick={onRest} type="button">
          Log 48-hour rest
        </button>
        <button className="mb-ghost" onClick={onRefer} type="button">
          Refer
        </button>
      </div>
    </aside>
  );
}

function asObjects(value: unknown): Record<string, unknown>[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => {
    if (item && typeof item === "object") {
      return item as Record<string, unknown>;
    }
    return { case_id: String(item) };
  });
}

function asIdObjects(value: unknown): Record<string, unknown>[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => ({ case_id: String(item) }));
}

function asNumbers(value: unknown): number[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => Number(item) || 0);
}

function TabCards({
  items,
  empty,
  kind,
  done,
  onAction,
}: {
  items: Record<string, unknown>[];
  empty: string;
  kind: "incident" | "referral" | "followup" | "closed" | "digest";
  done: Record<string, string>;
  onAction?: (caseId: string) => void;
}) {
  if (items.length === 0) {
    return <p>{empty}</p>;
  }
  return (
    <ul className="mb-work-list">
      {items.map((item, index) => {
        const caseId = String(item.case_id ?? item.window_id ?? `row-${index}`);
        const href = item.case_id ? `/welfare/cases/${String(item.case_id)}` : "/welfare";
        const detail =
          kind === "incident"
            ? String(item.window_id ?? "Asked to talk")
            : kind === "referral"
              ? `${String(item.channel ?? "I want to talk")} · ${String(item.status ?? "open")}`
              : kind === "followup"
                ? `Due ${String(item.due ?? "soon")}`
                : kind === "closed"
                  ? "Closed"
                  : "In today's digest";
        const marked = done[caseId];
        return (
          <li className="mb-sheet" key={`${caseId}-${index}`}>
            <div className="mb-sheet-head">
              <h2>{caseId}</h2>
              <span>{marked ?? detail}</span>
            </div>
            <div className="mb-action-row">
              <a className="mb-secondary" href={href}>
                Open
              </a>
              {onAction && !marked ? (
                <button className="mb-primary" onClick={() => onAction(caseId)} type="button">
                  {kind === "followup" ? "Mark done" : "Pick up"}
                </button>
              ) : null}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
