"use client";

import { SceneFamilyCall } from "@manobal/illustrations";
import { useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { engineClient } from "@/lib/engine";
import { usePersonnelI18n } from "@/lib/personnel-i18n";
import { useEngine } from "@/lib/use-engine";

export default function FamilyPage() {
  const { p } = usePersonnelI18n();
  const { data, error, loading, offline, reload } = useEngine("family", (client, signal) =>
    client.meFamily(signal),
  );
  const [copied, setCopied] = useState(false);

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={!data}>
      {data ? (
        <div className="mb-home-stack">
          <article className="mb-context-card">
            <SceneFamilyCall />
            <div>
              <p>{p("Reminders stay on this phone. The family page does not include your name.")}</p>
            </div>
          </article>
          <div className="mb-action-row">
            {(["sunday", "wednesday", "friday"] as const).map((day) => (
              <button
                className={data.reminder === day ? "mb-primary" : "mb-secondary"}
                key={day}
                onClick={() => {
                  void engineClient().saveFamily(day).then(() => reload());
                }}
                type="button"
              >
                {p(day === "sunday" ? "Sunday call" : day === "wednesday" ? "Wednesday call" : "Friday call")}
              </button>
            ))}
          </div>
          <p>
            {data.reminder
              ? p("Reminder set: {day}", { day: p(data.reminder) })
              : p("No reminder yet.")}
          </p>
          <button
            className="mb-secondary"
            onClick={() => {
              void navigator.clipboard?.writeText(`${window.location.origin}/family`);
              setCopied(true);
            }}
            type="button"
          >
            {p(copied ? "Link copied" : "Copy family resources link")}
          </button>
          <ul>
            {data.resources.map((line) => (
              <li key={line}>{p(line)}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </ScreenState>
  );
}
