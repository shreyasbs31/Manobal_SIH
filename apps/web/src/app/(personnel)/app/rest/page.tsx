"use client";

import { LeaveWindowPicker, ShiftTimeline } from "@manobal/ui";
import { SceneLeaveWindow } from "@manobal/illustrations";
import { useEffect, useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { useEngine } from "@/lib/use-engine";

export default function RestPage() {
  const { data, error, loading, offline } = useEngine("rest", (client, signal) =>
    client.meRest(signal),
  );
  const [start, setStart] = useState(data?.window?.start ?? "2026-10-04");
  const [end, setEnd] = useState(data?.window?.end ?? "2026-10-12");
  const [travel, setTravel] = useState(data?.window?.travel_days ?? 2);
  const [draft, setDraft] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!data?.window) {
      return;
    }
    setStart(data.window.start);
    setEnd(data.window.end);
    setTravel(data.window.travel_days);
  }, [data]);

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={!data}>
      {data ? (
        <div className="mb-home-stack">
          <h1 className="mb-type-title">Plan my rest</h1>
          <article className="mb-context-card">
            <SceneLeaveWindow />
            <div>
              <h2>Leave planner</h2>
              <p>
                EL {data.el_days} days. CL {data.cl_days} days.
              </p>
              <p>{data.copy}</p>
            </div>
          </article>
          {data.window ? (
            <>
              <p>
                Suggested window {start} to {end}. Travel days you can edit. MANOBAL does not
                submit leave.
              </p>
              <LeaveWindowPicker
                end={end}
                onChange={(next) => {
                  setStart(next.start);
                  setEnd(next.end);
                }}
                start={start}
              />
              <label className="mb-field">
                Travel days
                <input
                  min={0}
                  onChange={(event) => setTravel(Number(event.target.value))}
                  type="number"
                  value={travel}
                />
              </label>
              <button
                className="mb-primary"
                onClick={() => {
                  const text = `Leave request ${start} to ${end}, travel ${travel} days. Synthetic. MANOBAL does not submit this.`;
                  setDraft(text);
                  void navigator.clipboard?.writeText(text).then(() => setCopied(true));
                }}
                type="button"
              >
                Draft leave request
              </button>
              {copied ? <p>Copied. Paste it into your unit leave form yourself.</p> : null}
              {draft ? <pre>{draft}</pre> : null}
            </>
          ) : (
            <p>No feasible window in the current roster. Ask a welfare officer about rest days.</p>
          )}
          <h2 className="mb-section-label">Shift and sleep</h2>
          <p>Next seven days. Sleep windows are a suggestion, not an order.</p>
          <ShiftTimeline days={data.days.map((day) => ({ label: day.label, start: day.start, end: day.end }))} />
          <ul>
            {data.days.map((day) => (
              <li key={day.label}>
                {day.label}: sleep {day.sleep}. Caffeine {day.caffeine}.
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </ScreenState>
  );
}
