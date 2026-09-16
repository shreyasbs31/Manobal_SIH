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

export default function RosterPage() {
  const { data, error, loading, offline } = useEngine("command-roster", (client, signal) =>
    client.commandRoster(signal),
  );
  const leave = useEngine("command-leave", (client, signal) => client.commandLeave(signal));
  const climate = useEngine("command-climate", (client, signal) => client.commandClimate(signal));
  const [companies, setCompanies] = useState<Company[]>([]);
  const [projection, setProjection] = useState("");
  const [order, setOrder] = useState("");
  const rows = companies.length ? companies : data?.companies ?? [];

  const coverage = useMemo(
    () =>
      rows.map((row) => ({
        label: row.label,
        locked: row.locked,
        duty: row.duty_hours,
      })),
    [rows],
  );

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={!data}>
      {data ? (
        <div className="mb-home-stack">
          <p>
            Company sliders stay at company level. Groups under 10 cannot be simulated
            alone.
          </p>
          <div className="mb-roster">
            <section>
              {rows.map((row, index) => (
                <article className="mb-card" key={row.id}>
                  <h2>{row.label}</h2>
                  {row.locked ? (
                    <p className="mb-locked-note">{row.lock_reason}</p>
                  ) : (
                    <>
                      <label>
                        Weekly duty hours {row.duty_hours}
                        <input
                          max={72}
                          min={40}
                          onChange={(event) => {
                            const next = [...rows];
                            const current = next[index];
                            if (!current) return;
                            next[index] = {
                              ...current,
                              duty_hours: Number(event.target.value),
                            };
                            setCompanies(next);
                          }}
                          type="range"
                          value={row.duty_hours}
                        />
                      </label>
                      <label>
                        Rest days {row.rest_days}
                        <input
                          max={3}
                          min={0}
                          onChange={(event) => {
                            const next = [...rows];
                            const current = next[index];
                            if (!current) return;
                            next[index] = {
                              ...current,
                              rest_days: Number(event.target.value),
                            };
                            setCompanies(next);
                          }}
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
                          onChange={(event) => {
                            const next = [...rows];
                            const current = next[index];
                            if (!current) return;
                            next[index] = {
                              ...current,
                              night_share: Number(event.target.value),
                            };
                            setCompanies(next);
                          }}
                          type="range"
                          value={row.night_share}
                        />
                      </label>
                    </>
                  )}
                </article>
              ))}
            </section>
            <section>
              <h2>Projected posture in 14 days</h2>
              {coverage.map((row) => (
                <p key={row.label}>
                  {row.label}: {row.locked ? "locked" : `${row.duty} hours`}
                </p>
              ))}
              <h2>Operational coverage</h2>
              {coverage.map((row) => (
                <p key={`${row.label}-cov`}>
                  {row.label}: {row.locked ? "held" : row.duty > 58 ? "stretched" : "steady"}
                </p>
              ))}
              <button
                className="mb-secondary"
                onClick={() => {
                  void engineClient()
                    .commandSimulate({ companies: rows })
                    .then((result) => setProjection(JSON.stringify(result.posture)));
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
                    .then((result) => setOrder(result.body));
                }}
                type="button"
              >
                Create draft order
              </button>
              {projection ? <p>{projection}</p> : null}
              {order ? <pre>{order}</pre> : null}
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
