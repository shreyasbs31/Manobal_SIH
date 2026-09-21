"use client";

import { useEffect, useMemo, useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { type ConsoleCopy, localisePhrase, localiseUnit, useConsoleLang } from "@/lib/console-i18n";
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
  const { tx } = useConsoleLang();
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
    <ScreenState
      error={error}
      loading={loading}
      offline={offline}
      empty={!data}
      loadingText={tx.loading}
      offlineText={tx.offlineView}
    >
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
                    <h2>{localiseUnit(tx, row.label)}</h2>
                    <span>{row.n}</span>
                  </button>
                  {row.locked ? (
                    <p className="mb-locked-note">{localisePhrase(tx, row.lock_reason ?? "")}</p>
                  ) : (
                    <>
                      <label>
                        {tx.weeklyDuty} {row.duty_hours}
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
                        {tx.restDays} {row.rest_days}
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
                        {tx.nightShare} {row.night_share}
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
                        {tx.leaveRelease} {row.leave_release}
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
              <h2>{tx.hold14}</h2>
              <div className="mb-roster-board">
                <RosterMap focus={focus} rows={preview} tx={tx} />
                <div className="mb-roster-diagram" role="img" aria-label={tx.hold14}>
                {preview.map((row) => (
                  <div
                    className="mb-roster-diagram-row"
                    data-focus={row.label === focus ? "true" : "false"}
                    key={row.label}
                  >
                    <span className="mb-roster-coy">{localiseUnit(tx, row.label)}</span>
                    <div className="mb-roster-diagram-tracks">
                      <span className="mb-roster-track" data-kind="duty">
                        <i style={{ width: clampWidth(row.duty, 40, 72) }} />
                      </span>
                      <span className="mb-roster-track" data-kind="night">
                        <i style={{ width: clampWidth(row.night, 10, 50) }} />
                      </span>
                    </div>
                    <strong className="mb-roster-diagram-meta">
                      {row.locked
                        ? tx.locked
                        : `${row.duty}${tx.hoursUnit} · ${row.night}${tx.nightUnit}`}
                    </strong>
                  </div>
                ))}
                <p className="mb-roster-diagram-legend">
                  <span>
                    <i data-kind="duty" />
                    {tx.dutyTrack}
                  </span>
                  <span>
                    <i data-kind="night" />
                    {tx.nightTrack}
                  </span>
                </p>
              </div>
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
                    setStatus(tx.nightStepped);
                  }}
                  type="button"
                >
                  {tx.easeNight}
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
                        setStatus(tx.projectionReady);
                      })
                      .catch((caught: unknown) => {
                        setStatus(caught instanceof Error ? caught.message : tx.couldNotProject);
                      })
                      .finally(() => setBusy(false));
                  }}
                  type="button"
                >
                  {tx.project14}
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
                        setStatus(tx.draftReady);
                      })
                      .finally(() => setBusy(false));
                  }}
                  type="button"
                >
                  {tx.draftOrder}
                </button>
              </div>
              {projection.length ? (
                <div className="mb-projection">
                  <h2>{tx.projectedPosture}</h2>
                  {projection.map((row) => (
                    <div className="mb-compare-band" data-tone={row.posture} key={`p-${row.label}`}>
                      <span>{row.label}</span>
                      <strong>{row.posture}</strong>
                      <em>{row.coverage}</em>
                    </div>
                  ))}
                  <h2>{tx.coverage}</h2>
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
                      setStatus(tx.draftCopied);
                    }}
                    type="button"
                  >
                    {tx.copyDraft}
                  </button>
                </>
              ) : null}
              {status ? <p role="status">{status}</p> : null}
            </section>
          </div>
          <div className="mb-split">
            <section className="mb-sheet">
              <h2>{tx.leavePressure}</h2>
              {leave.data?.companies.map((row) => (
                <button
                  aria-pressed={focus === row.label}
                  className="mb-compare-band"
                  key={row.label}
                  onClick={() => {
                    setFocus(row.label);
                    setStatus(`${localiseUnit(tx, row.label)} ${tx.leaveWait} ${row.longest_wait}.`);
                  }}
                  type="button"
                >
                  <span>{localiseUnit(tx, row.label)}</span>
                  <strong>{row.backlog_days} {tx.days}</strong>
                  <em>{row.longest_wait}</em>
                </button>
              ))}
            </section>
            <section className="mb-sheet">
              <h2>{tx.unitClimate}</h2>
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
                      setStatus(`${row.week}: ${localisePhrase(tx, row.heavy)}.`);
                    }}
                    type="button"
                  >
                    <span>{row.week}</span>
                    <strong>{localisePhrase(tx, row.heavy)}</strong>
                  </button>
                ))}
              </div>
              {climate.data?.grievances.map((row) => (
                <button
                  className="mb-compare-band"
                  key={row.category}
                    onClick={() => setStatus(`${localisePhrase(tx, row.category)} ${tx.openStatus} ${row.age}.`)}
                  type="button"
                >
                  <span>{localisePhrase(tx, row.category)}</span>
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

function RosterMap({
  rows,
  focus,
  tx,
}: {
  rows: readonly { label: string; locked: boolean; duty: number; night: number }[];
  focus: string;
  tx: ConsoleCopy;
}) {
  const width = 640;
  const height = 220;
  const cx = 320;
  const cy = 112;
  const count = Math.max(rows.length, 1);
  return (
    <svg className="mb-roster-map" viewBox={`0 0 ${width} ${height}`} role="img" aria-hidden="true">
      <defs>
        <radialGradient id="mb-roster-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#a7fccd" stopOpacity="0.5" />
          <stop offset="100%" stopColor="#f6f3f1" stopOpacity="0" />
        </radialGradient>
      </defs>
      <circle cx={cx} cy={cy} r="58" fill="url(#mb-roster-glow)" />
      <circle className="mb-roster-hub" cx={cx} cy={cy} r="32" />
      <text className="mb-roster-hub-label" textAnchor="middle" x={cx} y={cy + 4}>
        {localiseUnit(tx, "Bn C-02")}
      </text>
      {rows.map((row, index) => {
        const angle = (Math.PI * 2 * index) / count - Math.PI / 2;
        const x = cx + Math.cos(angle) * 168;
        const y = cy + Math.sin(angle) * 72;
        const mx = (cx + x) / 2 + (y - cy) * 0.12;
        const my = (cy + y) / 2 - (x - cx) * 0.08;
        return (
          <g key={row.label}>
            <path
              className="mb-roster-link"
              d={`M ${cx} ${cy} Q ${mx.toFixed(1)} ${my.toFixed(1)} ${x.toFixed(1)} ${y.toFixed(1)}`}
            />
            <rect
              className="mb-roster-node"
              data-focus={row.label === focus ? "true" : "false"}
              data-locked={row.locked ? "true" : "false"}
              height="28"
              rx="14"
              width="132"
              x={x - 66}
              y={y - 14}
            />
            <text className="mb-roster-node-label" textAnchor="middle" x={x} y={y + 4}>
              {localiseUnit(tx, row.label)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
