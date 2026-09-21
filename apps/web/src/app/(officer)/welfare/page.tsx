"use client";

import type { WelfareCase } from "@manobal/contracts";
import { CaseCard, CaseStrip, SlaTimer, chimeKindForQueue, playConsoleChime } from "@manobal/ui";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { type ConsoleCopy, localiseDomain, localisePhrase, tierCaption, trajectoryCopy, useConsoleLang } from "@/lib/console-i18n";
import { engineClient } from "@/lib/engine";
import { useEngine } from "@/lib/use-engine";

const TAB_IDS = ["queue", "incidents", "selfRef", "followUps", "closed", "digest"] as const;
type TabId = (typeof TAB_IDS)[number];

function tabLabel(tx: ConsoleCopy, id: TabId): string {
  return tx[id];
}

export default function WelfarePage() {
  const router = useRouter();
  const { tx } = useConsoleLang();
  const { data, error, loading, offline, reload } = useEngine("welfare-queue", (client, signal) =>
    client.welfareQueue(signal),
  );
  const tabs = useEngine("welfare-tabs", (client, signal) => client.welfareTabs(signal));
  const profile = useEngine("officer-profile", (client, signal) => client.officerProfile(signal));
  const queue = data ?? [];
  const [selected, setSelected] = useState("");
  const [tab, setTab] = useState<TabId>("queue");
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
    { label: tx.urgent, items: t4 },
    { label: tx.high, items: t3 },
    { label: tx.elevated, items: t2 },
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
      setNotice(caught instanceof Error ? caught.message : tx.couldNotUpdate);
    }
  }

  return (
    <ScreenState
      empty={queue.length === 0 && tab === "queue"}
      emptyText={tx.emptyQueue}
      error={error ?? tabs.error}
      loading={loading}
      loadingText={tx.loading}
      offline={offline}
      offlineText={tx.offlineView}
    >
      <div className="mb-desk">
        {t4[0] ? (
          <div className="mb-t4-banner" role="status">
            {tx.acuteCase} {t4[0].case_id}. {tx.acknowledgeWithin} {t4[0].sla_label}.
          </div>
        ) : null}
        <p className="mb-queue-meta">
          <span>{tx.open} {String(meta.open ?? queue.length)}</span>
          <span>{tx.overdue} {String(meta.overdue ?? 0)}</span>
          <span>
            {tx.myLoad} {String(meta.load ?? queue.length)} {tx.of} {String(meta.capacity ?? 25)}
          </span>
          {profile.data ? <span>{tx.digestAt} {String(profile.data.digest_time)}</span> : null}
        </p>
        {notice ? <p role="status">{notice}</p> : null}
        <div className="mb-tabs" role="tablist" aria-label={tx.welfareViews}>
          {TAB_IDS.map((id) => (
            <button
              aria-selected={tab === id}
              className="mb-ghost"
              key={id}
              onClick={() => setTab(id)}
              role="tab"
              type="button"
            >
              {tabLabel(tx, id)}
            </button>
          ))}
        </div>
        {tab === "queue" ? (
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
                        domains={item.drivers.map((domain) => localiseDomain(tx, domain))}
                        drift={localisePhrase(tx, item.drift)}
                        lever={item.lever_title ? localisePhrase(tx, item.lever_title) : undefined}
                        limited={item.limited}
                        limitedLabel={tx.limitedData}
                        remainingRatio={item.remaining_ratio}
                        selected={item.case_id === selected}
                        sla={item.sla_label}
                        slaLabel={tx.sla}
                        source={item.source}
                        status={item.status}
                        tier={item.tier}
                        tierCaption={tierCaption(tx, item.tier)}
                        trajectory={item.trajectory}
                        trajectoryLabels={trajectoryCopy(tx)}
                      />
                    </a>
                  ))}
                </section>
              ))}
            </div>
            {current ? (
              <QueueAside
                current={current}
                openLabel={tx.openCase}
                restLabel={tx.logRest}
                referLabel={tx.refer}
                recommendedLabel={tx.recommended}
                slaLabel={tx.sla}
                tx={tx}
                onRest={() => void act(current.case_id, "open", tx.restLogged)}
                onRefer={() => void act(current.case_id, "referred", tx.referredCounsellor)}
              />
            ) : null}
          </div>
        ) : null}
        {tab === "incidents" ? (
          <TabCards
            actionLabel={tx.pickUp}
            closedLabel={tx.closedLabel}
            digestLabel={tx.digestItem}
            done={done}
            dueLabel={tx.due}
            empty={tx.emptyIncidents}
            items={asObjects(meta.incidents)}
            kind="incident"
            openLabel={tx.open}
            talkLabel={tx.askedTalk}
            soonLabel={tx.soon}
            onAction={(caseId) => void act(caseId, "open", tx.pickUp)}
          />
        ) : null}
        {tab === "selfRef" ? (
          <TabCards
            actionLabel={tx.pickUp}
            closedLabel={tx.closedLabel}
            digestLabel={tx.digestItem}
            done={done}
            dueLabel={tx.due}
            empty={tx.emptySelf}
            items={asObjects(meta.self_referrals)}
            kind="referral"
            openLabel={tx.open}
            talkLabel={tx.askedTalk}
            soonLabel={tx.soon}
            onAction={(caseId) => void act(caseId, "open", tx.pickUp)}
          />
        ) : null}
        {tab === "followUps" ? (
          <TabCards
            actionLabel={tx.markDone}
            closedLabel={tx.closedLabel}
            digestLabel={tx.digestItem}
            done={done}
            dueLabel={tx.due}
            empty={tx.emptyFollow}
            items={asObjects(meta.followups)}
            kind="followup"
            openLabel={tx.open}
            talkLabel={tx.askedTalk}
            soonLabel={tx.soon}
            onAction={(caseId) => void act(caseId, "done", tx.markDone)}
          />
        ) : null}
        {tab === "closed" ? (
          <TabCards
            actionLabel={tx.pickUp}
            closedLabel={tx.closedLabel}
            digestLabel={tx.digestItem}
            done={done}
            dueLabel={tx.due}
            empty={tx.emptyClosed}
            items={asIdObjects(meta.closed)}
            kind="closed"
            openLabel={tx.open}
            talkLabel={tx.askedTalk}
            soonLabel={tx.soon}
          />
        ) : null}
        {tab === "digest" ? (
          <TabCards
            actionLabel={tx.pickUp}
            closedLabel={tx.closedLabel}
            digestLabel={tx.digestItem}
            done={done}
            dueLabel={tx.due}
            empty={tx.emptyDigest}
            items={asIdObjects(meta.digest)}
            kind="digest"
            openLabel={tx.open}
            talkLabel={tx.askedTalk}
            soonLabel={tx.soon}
            onAction={(caseId) => void act(caseId, "open", tx.pickUp)}
          />
        ) : null}
        <p className="mb-workload" aria-label={tx.workloadWeek}>
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
  openLabel,
  restLabel,
  referLabel,
  recommendedLabel,
  slaLabel,
  tx,
}: {
  current: WelfareCase;
  onRest: () => void;
  onRefer: () => void;
  openLabel: string;
  restLabel: string;
  referLabel: string;
  recommendedLabel: string;
  slaLabel: string;
  tx: ConsoleCopy;
}) {
  const trajectory = trajectoryCopy(tx);
  const direction =
    current.trajectory === "rising"
      ? trajectory.rising
      : current.trajectory === "easing"
        ? trajectory.easing
        : trajectory.steady;
  return (
    <aside className="mb-sheet">
      <h2>
        {current.case_id} {tierCaption(tx, current.tier)} {direction}
      </h2>
      <p>{localisePhrase(tx, current.drift)}</p>
      <CaseStrip
        actions={[110]}
        days={Array.from({ length: 24 }, (_, index) => ({
          day: index * 5,
          tier: current.tier,
        }))}
        incidents={[118]}
        onsetDay={100}
      />
      <p>
        {recommendedLabel}: {localisePhrase(tx, current.lever_title)}
      </p>
      <SlaTimer
        label={slaLabel}
        remainingLabel={current.sla_label}
        remainingRatio={current.remaining_ratio}
        tier={current.tier}
      />
      <div className="mb-action-row">
        <a className="mb-primary" href={`/welfare/cases/${current.case_id}`}>
          {openLabel}
        </a>
        <button className="mb-secondary" onClick={onRest} type="button">
          {restLabel}
        </button>
        <button className="mb-ghost" onClick={onRefer} type="button">
          {referLabel}
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
  openLabel,
  actionLabel,
  closedLabel,
  digestLabel,
  dueLabel,
  talkLabel,
  soonLabel,
}: {
  items: Record<string, unknown>[];
  empty: string;
  kind: "incident" | "referral" | "followup" | "closed" | "digest";
  done: Record<string, string>;
  onAction?: (caseId: string) => void;
  openLabel: string;
  actionLabel: string;
  closedLabel: string;
  digestLabel: string;
  dueLabel: string;
  talkLabel: string;
  soonLabel: string;
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
            ? String(item.window_id ?? talkLabel)
            : kind === "referral"
              ? `${String(item.channel ?? talkLabel)} · ${String(item.status ?? openLabel)}`
              : kind === "followup"
                ? `${dueLabel} ${String(item.due ?? soonLabel)}`
                : kind === "closed"
                  ? closedLabel
                  : digestLabel;
        const marked = done[caseId];
        return (
          <li className="mb-sheet" key={`${caseId}-${index}`}>
            <div className="mb-sheet-head">
              <h2>{caseId}</h2>
              <span>{marked ?? detail}</span>
            </div>
            <div className="mb-action-row">
              <a className="mb-secondary" href={href}>
                {openLabel}
              </a>
              {onAction && !marked ? (
                <button className="mb-primary" onClick={() => onAction(caseId)} type="button">
                  {actionLabel}
                </button>
              ) : null}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
