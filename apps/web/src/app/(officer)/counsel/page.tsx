"use client";

import { CallPanel, EmptyState } from "@manobal/ui";
import { useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { engineClient } from "@/lib/engine";
import { useEngine } from "@/lib/use-engine";

export default function CounselPage() {
  const { data, error, loading, offline } = useEngine("counsel-desk", (client, signal) =>
    client.counselDesk(signal),
  );
  const profile = useEngine("officer-profile", (client, signal) => client.officerProfile(signal));
  const [note, setNote] = useState("");
  const [status, setStatus] = useState("");
  const active = data?.requests[0];

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={!data}>
      {data ? (
        <div className="mb-home-stack">
          <p>
            Language match first, then load. Hindi routes to{" "}
            {data.routing.counsellor.replace("counsellor-", "")}.
            {profile.data ? ` Languages ${String((profile.data.languages as string[] | undefined)?.join(", ") ?? "")}.` : ""}
          </p>
          <section>
            <h2>Today</h2>
            <ul>
              {data.calendar.map((slot) => (
                <li key={slot}>{slot}</li>
              ))}
            </ul>
          </section>
          <section>
            <h2>Requests</h2>
            {data.requests.map((item) => (
              <p key={String(item.id)}>
                {String(item.kind)} {String(item.language)} routed to {String(item.routed_to)}.{" "}
                {item.handle ? `Handle ${String(item.handle)}.` : "Named."} {String(item.summary)}
              </p>
            ))}
          </section>
          {active ? (
            <CallPanel
              joinLabel={data.acs.label}
              peer={active.handle ? String(active.handle) : "Named session"}
              status="Notes stay on this desk. They are not sent to welfare."
            />
          ) : (
            <EmptyState message="The calendar fills when bookings arrive." title="No other sessions today" />
          )}
          <label>
            Private note
            <textarea onChange={(event) => setNote(event.target.value)} value={note} />
          </label>
          <button
            className="mb-secondary"
            onClick={() => {
              void engineClient()
                .counselNotes(String(active?.id ?? "req-hi-1"), note)
                .then((result) => setStatus(`Saved, ${result.scope} scope.`));
            }}
            type="button"
          >
            Save private note
          </button>
          <button
            className="mb-secondary"
            onClick={() => {
              void engineClient()
                .counselSuggest("MB-4091", "REST_48H", "A rest cycle may help.")
                .then((result) =>
                  setStatus(
                    `Suggested ${result.lever}. Notes shared: ${result.notes_shared ? "yes" : "no"}.`,
                  ),
                );
            }}
            type="button"
          >
            Suggest 48-hour rest
          </button>
          {status ? <p role="status">{status}</p> : null}
        </div>
      ) : null}
    </ScreenState>
  );
}
