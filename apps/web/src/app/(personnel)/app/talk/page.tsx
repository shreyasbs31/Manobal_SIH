"use client";

import { CallPanel } from "@manobal/ui";
import { SceneCounsellorCall } from "@manobal/illustrations";
import { useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { engineClient } from "@/lib/engine";
import { usePersonnelI18n } from "@/lib/personnel-i18n";
import { useEngine } from "@/lib/use-engine";

export default function TalkPage() {
  const { p } = usePersonnelI18n();
  const { data, error, loading, offline, reload } = useEngine("talk", (client, signal) =>
    client.meTalk(signal),
  );
  const [status, setStatus] = useState("");
  const [callStatus, setCallStatus] = useState(p("Ready"));

  async function send(body: Record<string, unknown>) {
    const result = await engineClient().saveTalk(body);
    setStatus(p("Request saved."));
    reload();
  }

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={!data}>
      {data ? (
        <div className="mb-home-stack">
          <p>{p("They see your request, not your chats with Saathi. You choose whether your name is shared.")}</p>
          <article className="mb-context-card">
            <SceneCounsellorCall />
            <div>
              <h2>{p("Welfare officer")}</h2>
              <p>{p("Ask someone from your unit to talk with you.")}</p>
              <div className="mb-action-row">
                <button
                  className="mb-primary"
                  onClick={() => void send({ kind: "uwo", anonymous: false, mode: "request" })}
                  type="button"
                >
                  {p("Request a conversation")}
                </button>
              </div>
            </div>
          </article>
          <article className="mb-context-card">
            <SceneCounsellorCall />
            <div>
              <h2>{p("Counsellor")}</h2>
              <p>{p("Keep your name hidden, or book with your name.")}</p>
              <div className="mb-action-row">
                <button
                  className="mb-secondary"
                  onClick={() => void send({ kind: "counsellor", anonymous: true, mode: "request" })}
                  type="button"
                >
                  {p("Request without my name")}
                </button>
                <button
                  className="mb-secondary"
                  onClick={() => void send({ kind: "counsellor", anonymous: false, mode: "book" })}
                  type="button"
                >
                  {p("Book with my name")}
                </button>
              </div>
            </div>
          </article>
          {data.demo_join ? (
            <button
              className="mb-primary"
              onClick={() =>
                void send({ kind: "counsellor", anonymous: true, mode: "call_now", video: true })
              }
              type="button"
            >
              {p("Join a call")}
            </button>
          ) : (
            <CallPanel
              joinLabel={p("Join call")}
              onJoin={() => {
                void engineClient()
                  .callsToken()
                  .then((result) => {
                    setCallStatus(result.configured ? p("Call is ready.") : p("Call is not available right now."));
                  });
              }}
              peer={data.anonymous_handle}
              status={callStatus}
            />
          )}
          <p>{status}</p>
          <h2 className="mb-section-label">{p("Requests")}</h2>
          {data.requests.length === 0 ? (
            <p>{p("No requests yet. Pick welfare or a counsellor above.")}</p>
          ) : (
            data.requests.map((row) => (
              <article className="mb-card" key={String(row.id)}>
                <h2>{p(String(row.kind) === "uwo" ? "Welfare officer" : "Counsellor")}</h2>
                <p>
                  {p(String(row.status))}
                  {row.anonymous ? ` · ${p("name hidden")}` : ` · ${p("name shared")}`}
                  {row.handle ? ` · ${String(row.handle)}` : ""}
                </p>
              </article>
            ))
          )}
        </div>
      ) : null}
    </ScreenState>
  );
}
