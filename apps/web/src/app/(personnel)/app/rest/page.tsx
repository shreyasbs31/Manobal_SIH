"use client";

import { LeaveWindowPicker, ShiftTimeline } from "@manobal/ui";
import { SceneLeaveWindow } from "@manobal/illustrations";
import { useEffect, useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { usePersonnelI18n } from "@/lib/personnel-i18n";
import { useEngine } from "@/lib/use-engine";

export default function RestPage() {
  const { p } = usePersonnelI18n();
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
          <article className="mb-context-card">
            <SceneLeaveWindow />
            <div>
              <h2>{p("Leave planner")}</h2>
              <p>
                {p("Earned leave {el} days. Casual leave {cl} days.", {
                  el: data.el_days,
                  cl: data.cl_days,
                })}
              </p>
              <p>{p(data.copy)}</p>
            </div>
          </article>
          {data.window ? (
            <>
              <p>
                {p("Suggested dates {start} to {end}. You send this yourself.", { start, end })}
              </p>
              <LeaveWindowPicker
                copy={{
                  start: p("Suggested window start"),
                  end: p("Suggested window end"),
                  note: p("Unit blackout windows are shown at unit level only. MANOBAL does not submit leave."),
                }}
                end={end}
                onChange={(next) => {
                  setStart(next.start);
                  setEnd(next.end);
                }}
                start={start}
              />
              <label className="mb-field">
                {p("Travel days")}
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
                  const text = p("Leave request {start} to {end}, travel {travel} days.", {
                    start,
                    end,
                    travel,
                  });
                  setDraft(text);
                  void navigator.clipboard?.writeText(text).then(() => setCopied(true));
                }}
                type="button"
              >
                {p("Draft leave request")}
              </button>
              {copied ? <p>{p("Copied. Paste it into your unit leave form yourself.")}</p> : null}
              {draft ? <pre>{draft}</pre> : null}
            </>
          ) : (
            <p>{p("No feasible window in the current roster. Ask a welfare officer about rest days.")}</p>
          )}
          <h2 className="mb-section-label">{p("Shift and sleep")}</h2>
          <p>{p("A suggestion for the next seven days.")}</p>
          <ShiftTimeline
            days={data.days.map((day) => ({ label: p(day.label), start: day.start, end: day.end }))}
            label={p("Shift timeline")}
          />
          <ul>
            {data.days.map((day) => (
              <li key={day.label}>
                {p("{day}: sleep {sleep}. Caffeine {caffeine}.", {
                  day: p(day.label),
                  sleep: p(day.sleep),
                  caffeine: p(day.caffeine),
                })}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </ScreenState>
  );
}
