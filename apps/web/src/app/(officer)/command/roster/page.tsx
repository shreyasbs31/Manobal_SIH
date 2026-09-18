"use client";

import { useMemo, useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { engineClient } from "@/lib/engine";
import { useEngine } from "@/lib/use-engine";

interface Company {
  id: string;
  label: string;
  n: number;
  duty_hours: number;
  rest_days: number;
  night_share: number;
  quick_return_cap: number;
  leave_release: number;
  locked: boolean;
  lock_reason?: string;
}

interface ProjectionRow {
  label: string;
  posture?: string;
  coverage?: string;
  before?: string;
  after?: string;
}

export default function RosterPage() {
  const { data, error, loading, offline } = useEngine("command-roster", (client, signal) =>
    client.commandRoster(signal),
  );
  const leave = useEngine("command-leave", (client, signal) => client.commandLeave(signal));
  const climate = useEngine("command-climate", (client, signal) => client.commandClimate(signal));
  const [companies, setCompanies] = useState<Company[]>([]);
  const [projection, setProjection] = useState<ProjectionRow[]>([]);
  const [coverage, setCoverage] = useState<ProjectionRow[]>([]);
  const [order, setOrder] = useState("");
  const [status, setStatus] = useState("");
  const rows = companies.length ? companies : data?.companies ?? [];

  const preview = useMemo(
    () =>
      rows.map((row) => ({
        label: row.label,
        locked: row.locked,
        duty: row.duty_hours,
      })),
    [rows],
  );

  function patch(index: number, field: keyof Company, value: number) {
    const next = [...rows];
    const current = next[index];
    if (!current) {
      return;
    }
    next[index] = { ...current, [field]: value };
    setCompanies(next);
  }

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={!data}>
      {data ? (
        <div className="mb-home-stack">
          <p className="mb-desk-intro">
            Move company sliders, then project 14 days. Groups under 10 stay locked. The draft
            order is a note you copy. MANOBAL does not issue it.
          </p>
          <div className="mb-roster">
            <section>
              {rows.map((row, index) => (
                <article className="mb-card" key={row.id}>
                  <h2>{row.label}</h2>
                  <p>{row.n} people in this company view.</p>
                  {row.locked ? (
                    <p className="mb-locked-note">{row.lock_reason}</p>
                  ) : (
                    <>
                      <label>
                        Weekly duty hours {row.duty_hours}
                        <input
                          max={72}
                          min={40}
                          onChange={(event) => patch(index, "duty_hours", Number(event.target.value))}
                          type="range"
                          value={row.duty_hours}
                        />
                      </label>
                      <label>
                        Rest days {row.rest_days}
                        <input
                          max={3}
                          min={0}
                          onChange={(event) => patch(index, "rest_days", Number(event.target.value))}
                          step={0.1}
                          type="range"
                          value={row.rest_days}
                        />
                      </label>
                      <label>
                        Night share {row.night_share}
                        <input
                          max={50}
                          min={10}
                          onChange={(event) => patch(index, "night_share", Number(event.target.value))}
                          type="range"
                          value={row.night_share}
                        />
                      </label>
                      <label>
                        Leave release a week {row.leave_release}
                        <input
                          max={8}
                          min={0}
                          onChange={(event) => patch(index, "leave_release", Number(event.target.value))}
                          type="range"
                          value={row.leave_release}
                        />
                      </label>
                    </>
                  )}
                </article>
              ))}
            </section>
            <section>
              <h2>What you are asking the unit to hold</h2>
              {preview.map((row) => (
                <p key={row.label}>
                  {row.label}: {row.locked ? "locked" : `${row.duty} hours`}
                </p>
              ))}
              <button
                className="mb-ghost"
                onClick={() => {
                  const eased = rows.map((row) =>
                    row.locked
                      ? row
                      : {
                          ...row,
                          night_share: Math.max(10, row.night_share - 8),
                          duty_hours: Math.max(40, row.duty_hours - 4),
                        },
                  );
                  setCompanies(eased);
                  setStatus("Night share and duty hours stepped down. Project 14 days to see coverage.");
                }}
                type="button"
              >
                Ease night share
              </button>
              <button
                className="mb-secondary"
                onClick={() => {
                  void engineClient()
                    .commandSimulate({ companies: rows })
                    .then((result) => {
                      const payload = result as {
                        posture?: ProjectionRow[];
                        coverage?: ProjectionRow[];
                      };
                      setProjection(payload.posture ?? []);
                      setCoverage(payload.coverage ?? []);
                      setStatus("14-day projection is ready. Compare posture and coverage.");
                    })
                    .catch((caught: unknown) => {
                      setStatus(caught instanceof Error ? caught.message : "Could not project.");
                    });
                }}
                type="button"
              >
                Project 14 days
              </button>
              <button
                className="mb-primary"
                onClick={() => {
                  void engineClient()
                    .commandDraft({ companies: rows })
                    .then((result) => {
                      setOrder(result.body);
                      setStatus("Draft order ready to copy. It is not sent.");
                    });
                }}
                type="button"
              >
                Create draft order
              </button>
              {projection.length ? (
                <div className="mb-projection">
                  <h2>Projected posture in 14 days</h2>
                  {projection.map((row) => (
                    <p key={`p-${row.label}`}>
                      {row.label}: {row.posture}. Coverage {row.coverage}.
                    </p>
                  ))}
                  <h2>Operational coverage</h2>
                  {coverage.map((row) => (
                    <p key={`c-${row.label}`}>
                      {row.label}: now {row.before}, after {row.after}.
                    </p>
                  ))}
                </div>
              ) : null}
              {order ? (
                <>
                  <pre>{order}</pre>
                  <button
                    className="mb-ghost"
                    onClick={() => {
                      void navigator.clipboard?.writeText(order);
                      setStatus("Draft copied.");
                    }}
                    type="button"
                  >
                    Copy draft
                  </button>
                </>
              ) : null}
              {status ? <p role="status">{status}</p> : null}
            </section>
          </div>
          <section>
            <h2>Leave pressure</h2>
            <p>{leave.data?.copy}</p>
            {leave.data?.companies.map((row) => (
              <p key={row.label}>
                {row.label}: backlog {row.backlog_days} days, longest wait {row.longest_wait}
              </p>
            ))}
          </section>
          <section>
            <h2>Unit climate</h2>
            <p>Anonymous weekly pulse. Never a named person.</p>
            {climate.data?.pulse.map((row) => (
              <p key={row.week}>
                {row.week}: {row.heavy}
              </p>
            ))}
            <p>{climate.data?.colleague_conflict}</p>
            {climate.data?.grievances.map((row) => (
              <p key={row.category}>
                {row.category}, age {row.age}
              </p>
            ))}
          </section>
        </div>
      ) : null}
    </ScreenState>
  );
}
