"use client";

import { useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { engineClient } from "@/lib/engine";
import { useEngine } from "@/lib/use-engine";

type DpoPayload = {
  requests: { id: string; kind: string; status: string; due: string; token_hint: string }[];
  breaches: { id: string; status?: string }[];
  notices: { id: string; title: string; status: string }[];
};

export default function DpoPage() {
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const { data, error, loading, offline, reload } = useEngine("dpo", (client, signal) =>
    client.dpoRequests(signal) as Promise<DpoPayload>,
  );

  async function run(id: string, work: () => Promise<void>) {
    setBusy(id);
    try {
      await work();
      reload();
    } catch (caught: unknown) {
      setNotice(caught instanceof Error ? caught.message : "Could not complete that action.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <ScreenState
      empty={!data}
      emptyText="No open rights requests."
      error={error}
      loading={loading}
      offline={offline}
    >
      {data ? (
        <div className="mb-dpo mb-desk">
          {notice ? <p role="status">{notice}</p> : null}
          <div className="mb-work-list">
            {data.requests.map((row) => (
              <article className="mb-sheet" key={row.id}>
                <div className="mb-sheet-head">
                  <h2>{row.kind}</h2>
                  <span>Due {row.due}</span>
                </div>
                <p>{row.status}</p>
                {row.status === "open" ? (
                  <div className="mb-action-row">
                    <button
                      className="mb-primary"
                      disabled={busy !== null}
                      onClick={() =>
                        void run(row.id, async () => {
                          await engineClient().dpoDecide(row.id, "closed");
                          setNotice("Request closed.");
                        })
                      }
                      type="button"
                    >
                      Close
                    </button>
                    <button
                      className="mb-secondary"
                      disabled={busy !== null}
                      onClick={() =>
                        void run(`${row.id}-hold`, async () => {
                          await engineClient().dpoDecide(row.id, "held");
                          setNotice("Request held.");
                        })
                      }
                      type="button"
                    >
                      Hold
                    </button>
                  </div>
                ) : null}
              </article>
            ))}
          </div>
          <section className="mb-sheet">
            <h2>Notices</h2>
            {data.notices.map((row) => (
              <div className="mb-kill" key={row.id}>
                <span>
                  {row.title}: {row.status}
                </span>
                <button
                  className="mb-toggle"
                  disabled={busy !== null}
                  onClick={() =>
                    void run(row.id, async () => {
                      const next = row.status === "published" ? "draft" : "published";
                      await engineClient().dpoNotice(row.id, next);
                      setNotice(`Notice ${next}.`);
                    })
                  }
                  type="button"
                >
                  {row.status === "published" ? "Unpublish" : "Publish"}
                </button>
              </div>
            ))}
          </section>
          <p>
            Breach log: {data.breaches.length === 0 ? "none open." : `${data.breaches.length} open.`}
          </p>
        </div>
      ) : null}
    </ScreenState>
  );
}
