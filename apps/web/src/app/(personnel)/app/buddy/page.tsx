"use client";

import { IconBuddyPair } from "@manobal/ui";
import { SceneBuddyTea } from "@manobal/illustrations";
import { useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { engineClient } from "@/lib/engine";
import { usePersonnelI18n } from "@/lib/personnel-i18n";
import { useEngine } from "@/lib/use-engine";

export default function BuddyPage() {
  const { p } = usePersonnelI18n();
  const { data, error, loading, offline, reload } = useEngine("buddy", (client, signal) =>
    client.meBuddy(signal),
  );
  const [code, setCode] = useState("");

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={!data}>
      {data ? (
        <div className="mb-home-stack">
          <article className="mb-context-card">
            <SceneBuddyTea />
            <div>
              <IconBuddyPair height={22} width={22} />
              <p>{p(data.privacy)}</p>
            </div>
          </article>
          {data.paired ? (
            <>
              <p>{p("Paired with a buddy in your unit. You never see their data.")}</p>
              {data.last ? (
                <p>
                  {p(
                    data.last.kind === "ok"
                      ? "Last check-in: they said they are okay."
                      : "Last check-in: you asked them to check in.",
                  )}
                </p>
              ) : (
                <p>{p("No check-in yet. Ask once, then wait.")}</p>
              )}
              <button
                className="mb-secondary"
                onClick={() => {
                  void engineClient().saveBuddy({ action: "ping" }).then(() => reload());
                }}
                type="button"
              >
                {p("Check in with me")}
              </button>
              <button
                className="mb-primary"
                onClick={() => {
                  void engineClient().saveBuddy({ action: "ok" }).then(() => reload());
                }}
                type="button"
              >
                {p("I am okay")}
              </button>
              <button
                className="mb-ghost"
                onClick={() => {
                  void engineClient().saveBuddy({ action: "unpair" }).then(() => reload());
                }}
                type="button"
              >
                {p("Unpair without notifying")}
              </button>
            </>
          ) : (
            <>
              <label>
                {p("Pairing code")}
                <input onChange={(event) => setCode(event.target.value)} value={code} />
              </label>
              <button
                className="mb-primary"
                onClick={() => {
                  void engineClient().saveBuddy({ action: "pair", code }).then(() => reload());
                }}
                type="button"
              >
                {p("Pair")}
              </button>
            </>
          )}
          <h2 className="mb-section-label">{p("How to support")}</h2>
          {data.lessons.map((lesson) => (
            <p key={lesson}>{p(lesson)}</p>
          ))}
        </div>
      ) : null}
    </ScreenState>
  );
}
