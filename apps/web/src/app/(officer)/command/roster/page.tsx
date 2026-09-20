"use client";

import { useEffect, useMemo, useState } from "react";

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

function clampWidth(value: number, min: number, max: number) {
  const span = Math.max(1, max - min);
  return `${Math.min(100, Math.max(8, ((value - min) / span) * 100))}%`;
}

export default function RosterPage() {
  const { data, error, loading, offline } = useEngine("command-roster", (client, signal) =>
    client.commandRoster(signal),
  );
  const leave = useEngine("command-leave", (client, signal) => client.commandLeave(signal));
  const climate = useEngine("command-climate", (client, signal) => client.commandClimate(signal));
  const [companies, setCompanies] = useState<Company[]>([]);
  const [focus, setFocus] = useState("");
  const [week, setWeek] = useState("W0");
  const [projection, setProjection] = useState<ProjectionRow[]>([]);
  const [coverage, setCoverage] = useState<ProjectionRow[]>([]);
  const [order, setOrder] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const rows = companies.length ? companies : data?.companies ?? [];

  useEffect(() => {
    const stored = window.sessionStorage.getItem("manobal.roster.unit") ?? "";
    if (stored) {
      setFocus(stored);
    }
  }, []);

  const preview = useMemo(
    () =>
      rows.map((row) => ({
        label: row.label,
        locked: row.locked,
        duty: row.duty_hours,
        night: row.night_share,
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
        <div className="mb-desk">
          <div className="mb-roster">
            <section className="mb-roster-list">
              {rows.map((row, index) => (
                <article
                  className="mb-card"
                  data-focus={row.label === focus ? "true" : "false"}
                  key={row.id}
                >
                  <button
                    className="mb-sheet-head"
                    onClick={() => setFocus(row.label)}
                    type="button"
                  >
                    <h2>{row.label}</h2>
                    <span>{row.n}</span>
                  </button>
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
                        <span className="mb-meter" aria-hidden="true">
                          <i style={{ width: clampWidth(row.duty_hours, 40, 72) }} />
                        </span>
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
                        <span className="mb-meter" aria-hidden="true">
                          <i style={{ width: clampWidth(row.night_share, 10, 50) }} />
                        </span>
                      </label>
                      <label>
                        Leave release a week {row.leave_release}
                        <input
                          max={8}
                          min={0}
                          onChange={(event) =>
                            patch(index, "leave_release", Number(event.target.value))
                          }
                          type="range"
                          value={row.leave_release}
                        />
                      </label>
                    </>
                  )}
                </article>
              ))}
            </section>
            <section className="mb-sheet">
              <h2>14-day hold</h2>
              <div className="mb-hold-list">
                {preview.map((row) => (
                  <p key={row.label}>
                    <span>{row.label}</span>
                    <strong>{row.locked ? "locked" : `${row.duty}h · ${row.night}% night`}</strong>
                  </p>
                ))}
              </div>
              <div className="mb-action-row">
                <button
                  className="mb-ghost"
                  disabled={busy}
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
                    setStatus("Night share stepped down. Project to see coverage.");
                  }}
                  type="button"
                >
                  Ease night share
                </button>
                <button
                  className="mb-secondary"
                  disabled={busy}
                  onClick={() => {
                    setBusy(true);
                    void engineClient()
                      .commandSimulate({ companies: rows })
                      .then((result) => {
                        const payload = result as {
                          posture?: ProjectionRow[];
                          coverage?: ProjectionRow[];
                        };
                        setProjection(payload.posture ?? []);
                        setCoverage(payload.coverage ?? []);
                        setStatus("14-day projection is ready.");
                      })
                      .catch((caught: unknown) => {
                        setStatus(caught instanceof Error ? caught.message : "Could not project.");
                      })
                      .finally(() => setBusy(false));
                  }}
                  type="button"
                >
                  Project 14 days
                </button>
                <button
                  className="mb-primary"
                  disabled={busy}
                  onClick={() => {
                    setBusy(true);
                    void engineClient()
                      .commandDraft({ companies: rows })
                      .then((result) => {
                        setOrder(result.body);
                        setStatus("Draft ready to copy. It is not sent.");
                      })
                      .finally(() => setBusy(false));
                  }}
                  type="button"
                >
                  Create draft order
                </button>
              </div>
              {projection.length ? (
                <div className="mb-projection">
                  <h2>Projected posture in 14 days</h2>
                  {projection.map((row) => (
                    <div className="mb-compare-band" data-tone={row.posture} key={`p-${row.label}`}>
                      <span>{row.label}</span>
                      <strong>{row.posture}</strong>
                      <em>{row.coverage}</em>
                    </div>
                  ))}
                  <h2>Operational coverage</h2>
                  {coverage.map((row) => (
                    <div className="mb-compare-band" key={`c-${row.label}`}>
                      <span>{row.label}</span>
                      <strong>{row.before}</strong>
                      <em>{row.after}</em>
                    </div>
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
          <div className="mb-split">
            <section className="mb-sheet">
              <h2>Leave pressure</h2>
              {leave.data?.companies.map((row) => (
                <button
                  aria-pressed={focus === row.label}
                  className="mb-compare-band"
                  key={row.label}
                  onClick={() => {
                    setFocus(row.label);
                    setStatus(`${row.label} leave wait ${row.longest_wait}.`);
                  }}
                  type="button"
                >
                  <span>{row.label}</span>
                  <strong>{row.backlog_days} days</strong>
                  <em>{row.longest_wait}</em>
                </button>
              ))}
            </section>
            <section className="mb-sheet">
              <h2>Unit climate</h2>
              <div className="mb-pulse-row">
                {climate.data?.pulse.map((row) => (
                  <button
                    aria-pressed={week === row.week}
                    className="mb-pulse"
                    key={row.week}
                    onClick={() => {
                      const next =
                        row.heavy === "hidden"
                          ? "Post D-7"
                          : row.week === "W0" || row.week === "W-1"
                            ? "Charlie Coy"
                            : "Alpha Coy";
                      setWeek(row.week);
                      setFocus(next);
                      setStatus(`${row.week}: ${row.heavy}.`);
                    }}
                    type="button"
                  >
                    <span>{row.week}</span>
                    <strong>{row.heavy}</strong>
                  </button>
                ))}
              </div>
              {climate.data?.grievances.map((row) => (
                <button
                  className="mb-compare-band"
                  key={row.category}
                  onClick={() => setStatus(`${row.category} open ${row.age}.`)}
                  type="button"
                >
                  <span>{row.category}</span>
                  <strong>{row.age}</strong>
                </button>
              ))}
            </section>
          </div>
        </div>
      ) : null}
    </ScreenState>
  );
}
