"use client";

import { IconBuddyPair } from "@manobal/ui";
import { SceneBuddyTea } from "@manobal/illustrations";
import { useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { engineClient } from "@/lib/engine";
import { useEngine } from "@/lib/use-engine";

export default function BuddyPage() {
  const { data, error, loading, offline, reload } = useEngine("buddy", (client, signal) =>
    client.meBuddy(signal),
  );
  const [code, setCode] = useState("");

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={!data}>
      {data ? (
        <div className="mb-home-stack">
          <h1 className="mb-type-title">Buddy</h1>
          <article className="mb-context-card">
            <SceneBuddyTea />
            <div>
              <IconBuddyPair height={22} width={22} />
              <p>{data.privacy}</p>
            </div>
          </article>
          {data.paired ? (
            <>
              <p>Paired with a buddy in your unit. You never see their data.</p>
              <button
                className="mb-secondary"
                onClick={() => {
                  void engineClient().saveBuddy({ action: "ping" }).then(() => reload());
                }}
                type="button"
              >
                Check in with me
              </button>
              <button
                className="mb-primary"
                onClick={() => {
                  void engineClient().saveBuddy({ action: "ok" }).then(() => reload());
                }}
                type="button"
              >
                I am okay
              </button>
              <button
                className="mb-ghost"
                onClick={() => {
                  void engineClient().saveBuddy({ action: "unpair" }).then(() => reload());
                }}
                type="button"
              >
                Unpair without notifying
              </button>
            </>
          ) : (
            <>
              <label>
                Pairing code
                <input onChange={(event) => setCode(event.target.value)} value={code} />
              </label>
              <button
                className="mb-primary"
                onClick={() => {
                  void engineClient().saveBuddy({ action: "pair", code }).then(() => reload());
                }}
                type="button"
              >
                Pair
              </button>
            </>
          )}
          <h2 className="mb-section-label">How to support</h2>
          {data.lessons.map((lesson) => (
            <p key={lesson}>{lesson}</p>
          ))}
        </div>
      ) : null}
    </ScreenState>
  );
}
