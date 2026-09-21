"use client";

import { useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { useConsoleLang } from "@/lib/console-i18n";
import { engineClient } from "@/lib/engine";
import { useEngine } from "@/lib/use-engine";

type DpoPayload = {
  requests?: { id: string; kind: string; status: string; due: string; token_hint: string }[];
  breaches?: { id: string; status?: string; opened?: string; note?: string }[];
  notices?: { id: string; title: string; status: string }[];
  retention?: { id: string; name: string; keep: string; next: string }[];
};

function asList<T>(value: T[] | undefined): T[] {
  return Array.isArray(value) ? value : [];
}

export default function DpoPage() {
  const { tx } = useConsoleLang();
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const { data, error, loading, offline, reload } = useEngine("dpo", (client, signal) =>
    client.dpoRequests(signal) as Promise<DpoPayload>,
  );
  const requests = asList(data?.requests);
  const notices = asList(data?.notices);
  const breaches = asList(data?.breaches);
  const retention = asList(data?.retention);
  const openCount = requests.filter((row) => row.status === "open").length;
  const heldCount = requests.filter((row) => row.status === "held").length;
  const publishedCount = notices.filter((row) => row.status === "published").length;

  function kindLabel(kind: string): string {
    if (kind === "access") return tx.dpoAccess;
    if (kind === "erasure") return tx.dpoErasure;
    if (kind === "grievance") return tx.dpoGrievance;
    if (kind === "correction") return tx.dpoCorrection;
    return kind;
  }

  function statusLabel(status: string): string {
    if (status === "open") return tx.dpoOpenStatus;
    if (status === "held") return tx.dpoHeldStatus;
    if (status === "closed") return tx.dpoClosedStatus;
    if (status === "draft") return tx.dpoDraftStatus;
    if (status === "published") return tx.dpoPublishedStatus;
    return status;
  }

  function noticeLabel(id: string, title: string): string {
    if (id === "notice-hi") return tx.dpoHindiNotice;
    if (id === "notice-en") return tx.dpoEnglishNotice;
    if (id === "notice-ta") return tx.dpoTamilNotice;
    return title;
  }

  function retentionCopy(row: { id: string; name: string; keep: string; next: string }) {
    if (row.id === "ret-voice") {
      return { name: tx.dpoVoiceClips, keep: tx.dpoUntilReviewed, next: tx.dpoNightly };
    }
    if (row.id === "ret-wear") {
      return { name: tx.dpoWearableDaily, keep: tx.dpoNinetyDays, next: row.next };
    }
    if (row.id === "ret-audit") {
      return { name: tx.dpoAuditRecord, keep: tx.dpoSevenYears, next: tx.dpoNoDelete };
    }
    return row;
  }

  async function run(id: string, work: () => Promise<void>) {
    setBusy(id);
    try {
      await work();
      reload();
    } catch (caught: unknown) {
      setNotice(caught instanceof Error ? caught.message : tx.couldNotComplete);
    } finally {
      setBusy(null);
    }
  }

  return (
    <ScreenState
      empty={data === null}
      emptyText={tx.dpoEmpty}
      error={error}
      loading={loading}
      offline={offline}
      loadingText={tx.loading}
      offlineText={tx.offlineView}
    >
      {data ? (
        <div className="mb-dpo-desk mb-desk">
          <p className="mb-desk-purpose">{tx.dpoPurpose}</p>
          {notice ? <p role="status">{notice}</p> : null}
          <div className="mb-dpo-stats">
            <span><strong>{openCount}</strong>{tx.dpoOpen}</span>
            <span><strong>{heldCount}</strong>{tx.dpoHeldCount}</span>
            <span><strong>{publishedCount}</strong>{tx.dpoPublished}</span>
            <span>
              <strong>{breaches.filter((row) => row.status === "open").length}</strong>
              {tx.dpoBreach}
            </span>
          </div>
          <div className="mb-dpo-layout">
            <section className="mb-sheet mb-dpo-queue">
              <div className="mb-section-head">
                <div>
                  <h2>{tx.dpoQueue}</h2>
                  <p>{tx.dpoQueueNote}</p>
                </div>
              </div>
              {requests.length === 0 ? <p>{tx.dpoEmpty}</p> : (
                <div className="mb-dpo-table">
                  <div className="mb-dpo-table-head" aria-hidden="true">
                    <span>{tx.dpoRequestType}</span>
                    <span>{tx.dpoToken}</span>
                    <span>{tx.dpoDue}</span>
                    <span>{tx.dpoStatus}</span>
                    <span>{tx.dpoActions}</span>
                  </div>
                  {requests.map((row) => (
                    <article className="mb-dpo-row" key={row.id}>
                      <strong>{kindLabel(row.kind)}</strong>
                      <span>{row.token_hint}</span>
                      <time>{row.due}</time>
                      <span className="mb-status-pill" data-status={row.status}>
                        {statusLabel(row.status)}
                      </span>
                      <div className="mb-dpo-row-actions">
                        {row.status === "open" ? (
                          <>
                            <button
                              className="mb-primary"
                              disabled={busy !== null}
                              onClick={() =>
                                void run(row.id, async () => {
                                  await engineClient().dpoDecide(row.id, "closed");
                                  setNotice(tx.dpoClosed);
                                })
                              }
                              type="button"
                            >
                              {tx.close}
                            </button>
                            <button
                              className="mb-ghost"
                              disabled={busy !== null}
                              onClick={() =>
                                void run(`${row.id}-hold`, async () => {
                                  await engineClient().dpoDecide(row.id, "held");
                                  setNotice(tx.dpoHeld);
                                })
                              }
                              type="button"
                            >
                              {tx.hold}
                            </button>
                          </>
                        ) : <span>{statusLabel(row.status)}</span>}
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </section>
            <aside className="mb-dpo-operations">
              <section className="mb-sheet">
                <h2>{tx.dpoNotices}</h2>
                {notices.map((row) => (
                  <div className="mb-dpo-notice" key={row.id}>
                    <div>
                      <strong>{noticeLabel(row.id, row.title)}</strong>
                      <span>{statusLabel(row.status)}</span>
                    </div>
                    <button
                      className="mb-toggle"
                      disabled={busy !== null}
                      onClick={() =>
                        void run(row.id, async () => {
                          const next = row.status === "published" ? "draft" : "published";
                          await engineClient().dpoNotice(row.id, next);
                          setNotice(next === "published" ? tx.dpoPublish : tx.dpoUnpublish);
                        })
                      }
                      type="button"
                    >
                      {row.status === "published" ? tx.dpoUnpublish : tx.dpoPublish}
                    </button>
                  </div>
                ))}
              </section>
              <section className="mb-sheet">
                <h2>{tx.dpoRetention}</h2>
                <p>{tx.dpoRetentionNote}</p>
                {retention.map((row) => {
                  const copy = retentionCopy(row);
                  return (
                    <article className="mb-retention-row" key={row.id}>
                      <strong>{copy.name}</strong>
                      <span>{tx.dpoKeep} {copy.keep}</span>
                      <em>{tx.dpoNext} {copy.next}</em>
                    </article>
                  );
                })}
              </section>
              <section className="mb-sheet">
                <h2>{tx.dpoBreach}</h2>
                <p>{tx.dpoBreachNote}</p>
                {breaches.length === 0 ? <p>{tx.dpoNoneBreach}</p> : null}
                {breaches.map((row) => (
                  <article className="mb-breach-row" key={row.id}>
                    <strong>{row.id}</strong>
                    <span className="mb-status-pill" data-status={row.status ?? "closed"}>
                      {statusLabel(row.status ?? "closed")}
                    </span>
                    <p>{row.id === "br-000" ? tx.dpoTestBreach : (row.note ?? row.opened ?? tx.dpoNoneBreach)}</p>
                  </article>
                ))}
              </section>
            </aside>
          </div>
        </div>
      ) : null}
    </ScreenState>
  );
}
