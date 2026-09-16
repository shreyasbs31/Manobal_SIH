"use client";

import { LeaveWindowPicker, ShiftTimeline } from "@manobal/ui";
import { SceneLeaveWindow } from "@manobal/illustrations";

import { ScreenState } from "@/components/screen-state";
import { useEngine } from "@/lib/use-engine";

export default function RestPage() {
  const { data, error, loading, offline } = useEngine("rest", (client, signal) =>
    client.meRest(signal),
  );

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
                Suggested window {data.window.start} to {data.window.end}. Travel days you can
                edit below.
              </p>
              <LeaveWindowPicker />
              <label className="mb-field">
                Travel days
                <input defaultValue={data.window.travel_days} min={0} type="number" />
              </label>
              <button
                className="mb-primary"
                onClick={() => {
                  void navigator.clipboard?.writeText(
                    `Leave request ${data.window?.start} to ${data.window?.end}`,
                  );
                }}
                type="button"
              >
                Draft leave request
              </button>
            </>
          ) : (
            <p>No feasible window in the current roster.</p>
          )}
          <h2 className="mb-section-label">Shift and sleep</h2>
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
