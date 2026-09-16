"use client";

import { CallPanel } from "@manobal/ui";
import { SceneCounsellorCall } from "@manobal/illustrations";
import { useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { engineClient } from "@/lib/engine";
import { useEngine } from "@/lib/use-engine";

export default function TalkPage() {
  const { data, error, loading, offline, reload } = useEngine("talk", (client, signal) =>
    client.meTalk(signal),
  );
  const [status, setStatus] = useState("");

  async function send(body: Record<string, unknown>) {
    const result = await engineClient().saveTalk(body);
    setStatus(
      result.demo_join
        ? result.demo_label
        : "Request saved.",
    );
    reload();
  }

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={!data}>
      {data ? (
        <div className="mb-home-stack">
          <h1 className="mb-type-title">Talk to a person</h1>
          <article className="mb-context-card">
            <SceneCounsellorCall />
            <div>
              <h2>Welfare officer</h2>
              <p>You choose whether your identity is shared.</p>
              <button
                className="mb-primary"
                onClick={() => void send({ kind: "uwo", anonymous: false, mode: "request" })}
                type="button"
              >
                Request a conversation
              </button>
            </div>
          </article>
          <article className="mb-context-card">
            <SceneCounsellorCall />
            <div>
              <h2>Counsellor</h2>
              <p>Anonymous handle {data.anonymous_handle}, or use your name.</p>
              <button
                className="mb-secondary"
                onClick={() => void send({ kind: "counsellor", anonymous: true, mode: "request" })}
                type="button"
              >
                Request anonymously
              </button>
              <button
                className="mb-secondary"
                onClick={() => void send({ kind: "counsellor", anonymous: false, mode: "book" })}
                type="button"
              >
                Book with my name
              </button>
            </div>
          </article>
          {data.demo_join ? (
            <p>{data.demo_label}</p>
          ) : (
            <CallPanel peer={data.anonymous_handle} status="Ready" />
          )}
          <button
            className="mb-primary"
            onClick={() => void send({ kind: "counsellor", anonymous: true, mode: "call_now", video: true })}
            type="button"
          >
            Demo join
          </button>
          <p>{status}</p>
          <h2 className="mb-section-label">Requests</h2>
          {data.requests.length === 0 ? (
            <p>No requests yet.</p>
          ) : (
            data.requests.map((row) => (
              <p key={String(row.id)}>
                {String(row.kind)} · {String(row.status)}
                {row.anonymous ? " · anonymous" : ""}
              </p>
            ))
          )}
        </div>
      ) : null}
    </ScreenState>
  );
}
