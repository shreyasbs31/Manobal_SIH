"use client";

import { useMemo, useRef, useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { engineClient } from "@/lib/engine";
import { useEngine } from "@/lib/use-engine";

type Jobs = {
  contracts: { name: string; fields: string[]; forbidden: string[] }[];
  jobs: { id: string; source: string; status: string; accepted: number; held: number }[];
  quarantine: { row: string; reason: string; field: string }[];
  schedules: { id: string; source: string; cadence: string; enabled: boolean; last_run: string; feed: string }[];
  quality: {
    completeness: number;
    tokenised: boolean;
    name_columns: number;
    missingness: number;
    stale: number;
    psi: number;
    rows: number;
  };
  preview: {
    before: Record<string, string>;
    after: Record<string, string>;
  };
};

function parseCsv(text: string): Record<string, unknown>[] {
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  const header = lines[0];
  if (!header) {
    return [];
  }
  const keys = header.split(",").map((cell) => cell.trim());
  return lines.slice(1).map((line) => {
    const cells = line.split(",");
    const row: Record<string, unknown> = {};
    keys.forEach((key, index) => {
      row[key] = (cells[index] ?? "").trim();
    });
    return row;
  });
}

function pct(value: number): string {
  return `${Math.round(Math.min(1, Math.max(0, value)) * 100)}%`;
}

export default function IntegrationsPage() {
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [picked, setPicked] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const { data, error, loading, offline, reload } = useEngine("integrations", (client, signal) =>
    client.integrationsJobs(signal) as Promise<Jobs>,
  );
  const schedule = useMemo(
    () => data?.schedules.find((row) => row.id === picked) ?? data?.schedules[0],
    [data, picked],
  );

  async function run(id: string, work: () => Promise<void>) {
    setBusy(id);
    try {
      await work();
      reload();
    } catch (caught: unknown) {
      setNotice(caught instanceof Error ? caught.message : "Could not complete that action.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={!data}>
      {data ? (
        <div className="mb-integrate mb-desk">
          {notice ? <p role="status">{notice}</p> : null}
          <section className="mb-sheet">
            <h2>Feeds</h2>
            {data.schedules.map((row) => (
              <button
                aria-pressed={schedule?.id === row.id}
                className="mb-source"
                key={row.id}
                onClick={() => setPicked(row.id)}
                type="button"
              >
                <strong>{row.source}</strong>
                <span>{row.cadence}</span>
                <em>{row.enabled ? `Last ${row.last_run}` : "Paused"}</em>
              </button>
            ))}
            <div className="mb-action-row">
              <button
                className="mb-primary"
                disabled={busy !== null || !schedule}
                onClick={() =>
                  void run("run", async () => {
                    const source = schedule?.feed ?? "hrms.csv";
                    await engineClient().integrationsRun(source);
                    setNotice(`${schedule?.source ?? "Feed"} accepted. Names were removed.`);
                  })
                }
                type="button"
              >
                Run now
              </button>
              <button
                className="mb-secondary"
                disabled={busy !== null || !schedule}
                onClick={() =>
                  void run("sched", async () => {
                    if (!schedule) {
                      return;
                    }
                    await engineClient().integrationsSchedule(schedule.id, !schedule.enabled);
                    setNotice(schedule.enabled ? "Schedule paused." : "Schedule on.");
                  })
                }
                type="button"
              >
                {schedule?.enabled ? "Pause schedule" : "Resume schedule"}
              </button>
              <button
                className="mb-ghost"
                disabled={busy !== null}
                onClick={() => fileRef.current?.click()}
                type="button"
              >
                Upload CSV
              </button>
              <input
                accept=".csv,text/csv"
                className="mb-sr"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  event.target.value = "";
                  if (!file) {
                    return;
                  }
                  void run("csv", async () => {
                    const text = await file.text();
                    const rows = parseCsv(text);
                    const result = await engineClient().integrationsUpload(file.name, rows);
                    setNotice(
                      Number(result.held ?? 0) > 0
                        ? `${file.name} held ${String(result.held)} rows so names could be removed.`
                        : `${file.name} accepted ${String(result.accepted ?? rows.length)} rows.`,
                    );
                  });
                }}
                ref={fileRef}
                type="file"
              />
            </div>
          </section>
          <aside className="mb-sheet">
            <h2>Names</h2>
            <div className="mb-preview-pair">
              <article>
                <h3>Before names are removed</h3>
                {Object.entries(data.preview.before).map(([key, value]) => (
                  <p key={key}>
                    {key}: {value}
                  </p>
                ))}
              </article>
              <article>
                <h3>After names are removed</h3>
                {Object.entries(data.preview.after).map(([key, value]) => (
                  <p key={key}>
                    {key}: {value}
                  </p>
                ))}
              </article>
            </div>
            <h2>Quality</h2>
            {(
              [
                ["Completeness", data.quality.completeness],
                ["Missingness", data.quality.missingness],
                ["Stale share", data.quality.stale],
                ["Change since last week", data.quality.psi],
              ] as const
            ).map(([label, value]) => (
              <div className="mb-quality-row" key={label}>
                <span>
                  {label} {pct(value)}
                </span>
                <span className="mb-meter" aria-hidden="true">
                  <i style={{ width: pct(value) }} />
                </span>
              </div>
            ))}
            <p>
              {data.quality.rows} rows. Names removed: {data.quality.tokenised ? "yes" : "no"}.
            </p>
            <button
              className="mb-secondary"
              disabled={busy !== null}
              onClick={() =>
                void run("hook", async () => {
                  const result = await engineClient().integrationsWebhookTest();
                  setNotice(`Incident notice accepted for ${String(result.unit_path ?? "Charlie Coy")}.`);
                })
              }
              type="button"
            >
              Send a test incident notice
            </button>
          </aside>
          <section className="mb-sheet mb-integrate-span">
            <h2>Jobs</h2>
            {data.jobs.map((job) => (
              <article className="mb-job-row" key={job.id}>
                <span>{job.source}</span>
                <strong>{job.status}</strong>
                <em>
                  {job.accepted} in, {job.held} held
                </em>
                <span className="mb-meter" aria-hidden="true">
                  <i
                    style={{
                      width: `${Math.min(100, Math.round((job.accepted / Math.max(1, job.accepted + job.held)) * 100))}%`,
                    }}
                  />
                </span>
                {job.status !== "accepted" ? (
                  <button
                    className="mb-secondary"
                    disabled={busy !== null}
                    onClick={() =>
                      void run(job.id, async () => {
                        await engineClient().integrationsRetry(job.id);
                        setNotice("Job accepted after names were removed.");
                      })
                    }
                    type="button"
                  >
                    Retry after names were removed
                  </button>
                ) : (
                  <span />
                )}
              </article>
            ))}
          </section>
          <section className="mb-sheet">
            <h2>Quarantine</h2>
            {data.quarantine.length === 0 ? (
              <p>Nothing held.</p>
            ) : (
              data.quarantine.map((row) => (
                <article className="mb-job-row" key={`${row.row}-${row.field}`}>
                  <span>Row {row.row}</span>
                  <strong>{row.field}</strong>
                  <em>{row.reason}</em>
                  <span />
                  <button
                    className="mb-secondary"
                    disabled={busy !== null}
                    onClick={() =>
                      void run(row.row, async () => {
                        await engineClient().integrationsRelease(row.row);
                        setNotice(`Row ${row.row} released.`);
                      })
                    }
                    type="button"
                  >
                    Release
                  </button>
                </article>
              ))
            )}
            <button
              className="mb-ghost"
              disabled={busy !== null}
              onClick={() =>
                void run("probe", async () => {
                  await engineClient().integrationsUpload("probe.csv", [
                    { full_name: "should-not-pass", duty_date: "2026-09-16" },
                  ]);
                  setNotice("The name column was held.");
                })
              }
              type="button"
            >
              Test that names are blocked
            </button>
          </section>
          <section className="mb-sheet">
            <h2>What is accepted</h2>
            <table className="mb-compare">
              <thead>
                <tr>
                  <th scope="col">Contract</th>
                  <th scope="col">Fields</th>
                  <th scope="col">Never accepted</th>
                </tr>
              </thead>
              <tbody>
                {data.contracts.map((row) => (
                  <tr key={row.name}>
                    <td>{row.name}</td>
                    <td>{row.fields.join(", ")}</td>
                    <td>{row.forbidden.join(", ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </div>
      ) : null}
    </ScreenState>
  );
}
