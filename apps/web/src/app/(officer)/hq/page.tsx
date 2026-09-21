"use client";

import { useMemo, useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { localisePhrase, useConsoleLang } from "@/lib/console-i18n";
import { engineClient } from "@/lib/engine";
import { useEngine } from "@/lib/use-engine";

interface Theatre {
  id: string;
  label: string;
  posture: string;
  workload: string;
  leave: string;
  incidents: string;
  grievances: string;
}

interface CapacityRow {
  id: string;
  staffed: string;
  demand: string;
  gap: string;
}

interface Lever {
  code: string;
  later_easing: string;
  n: string;
}

export default function HqPage() {
  const { tx } = useConsoleLang();
  const { data, error, loading, offline, reload } = useEngine("hq-overview", (client, signal) =>
    client.hqOverview(signal),
  );
  const [brief, setBrief] = useState("");
  const [status, setStatus] = useState("");
  const [selected, setSelected] = useState("central");
  const [leaveRate, setLeaveRate] = useState<number | null>(null);
  const [rotation, setRotation] = useState<number | null>(null);
  const [dutyCap, setDutyCap] = useState<number | null>(null);
  const [quickReturn, setQuickReturn] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const payload = data as
    | {
        theatres: Theatre[];
        capacity: { demand: string; recommend: string; rows?: CapacityRow[] };
        retention: { transfer_requests: string; exit_intent_tags: string; note?: string };
        levers?: { note: string; items: Lever[] };
        policy: Record<string, number>;
        brief: { title: string; body: string; edited: boolean };
      }
    | null;
  const theatres = payload?.theatres ?? [];
  const body = brief || payload?.brief.body || "";
  const policy = payload?.policy;
  const leave = leaveRate ?? Number(policy?.leave_approval_rate ?? 0.62);
  const months = rotation ?? Number(policy?.rotation_length_months ?? 24);
  const duty = dutyCap ?? Number(policy?.max_consecutive_duty ?? 10);
  const returns = quickReturn ?? Number(policy?.quick_return_cap ?? 2);
  const theatre = useMemo(
    () => theatres.find((row) => row.id === selected) ?? theatres[0],
    [theatres, selected],
  );
  const capacityRows = payload?.capacity.rows ?? [];

  async function project() {
    setBusy(true);
    try {
      const result = await engineClient().hqSimulate({
        leave_approval_rate: leave,
        rotation_length_months: months,
        max_consecutive_duty: duty,
        quick_return_cap: returns,
      });
      setStatus(String(result.projected ?? tx.projected));
      reload();
    } catch (caught: unknown) {
      setStatus(caught instanceof Error ? caught.message : tx.couldNotProject);
    } finally {
      setBusy(false);
    }
  }

  return (
    <ScreenState
      error={error}
      loading={loading}
      offline={offline}
      empty={!payload}
      loadingText={tx.loading}
      offlineText={tx.offlineView}
    >
      {payload ? (
        <div className="mb-desk">
          <p className="mb-desk-purpose">{tx.hqPurpose}</p>
          {status ? <p role="status">{status}</p> : null}
          <section className="mb-sheet">
            <h2>{tx.hqCompare}</h2>
            <table className="mb-compare">
              <thead>
                <tr>
                  <th scope="col">{tx.unit}</th>
                  <th scope="col">{tx.hqPosture}</th>
                  <th scope="col">{tx.hqWorkload}</th>
                  <th scope="col">{tx.leave}</th>
                  <th scope="col">{tx.incidentShort}</th>
                  <th scope="col">{tx.hqGrievances}</th>
                </tr>
              </thead>
              <tbody>
                {theatres.map((row) => (
                  <tr data-focus={row.id === selected ? "true" : "false"} key={row.id}>
                    <th scope="row">
                      <button
                        aria-pressed={row.id === selected}
                        className="mb-sheet-head"
                        onClick={() => setSelected(row.id)}
                        type="button"
                      >
                        {row.label}
                      </button>
                    </th>
                    <td>{localisePhrase(tx, row.posture)}</td>
                    <td>{row.workload}</td>
                    <td>{localisePhrase(tx, row.leave)}</td>
                    <td>{localisePhrase(tx, row.incidents)}</td>
                    <td>{localisePhrase(tx, row.grievances)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
          <div className="mb-hq-split">
            <div className="mb-hq-stack">
              <section className="mb-sheet">
                <h2>{tx.hqCapacity}</h2>
                <p>
                  {tx.hqDemand}: {localisePhrase(tx, payload.capacity.demand)}
                </p>
                <p>{payload.capacity.recommend}</p>
                {capacityRows.length ? (
                  <table className="mb-compare">
                    <thead>
                      <tr>
                        <th scope="col">{tx.unit}</th>
                        <th scope="col">{tx.hqStaffed}</th>
                        <th scope="col">{tx.hqDemand}</th>
                        <th scope="col">{tx.hqGap}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {capacityRows.map((row) => {
                        const label = theatres.find((item) => item.id === row.id)?.label ?? row.id;
                        return (
                          <tr key={row.id}>
                            <th scope="row">{label}</th>
                            <td>{row.staffed}</td>
                            <td>{row.demand}</td>
                            <td>{localisePhrase(tx, row.gap)}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                ) : null}
                <p>
                  {tx.hqRecommend}: {payload.capacity.recommend}
                </p>
              </section>
              <section className="mb-sheet">
                <h2>{tx.hqRetention}</h2>
                <p>
                  {tx.hqTransfers}: {localisePhrase(tx, payload.retention.transfer_requests)}
                </p>
                <p>
                  {tx.hqExit}: {localisePhrase(tx, payload.retention.exit_intent_tags)}
                </p>
                <p>{payload.retention.note ?? tx.hqObservational}</p>
                <h3>{tx.hqLevers}</h3>
                <ul className="mb-work-list">
                  {(payload.levers?.items ?? []).map((item) => (
                    <li className="mb-job-row" key={item.code}>
                      <span>{item.code}</span>
                      <strong>{localisePhrase(tx, item.later_easing)}</strong>
                      <em>{localisePhrase(tx, item.n)}</em>
                    </li>
                  ))}
                </ul>
                <p>{payload.levers?.note ?? tx.hqObservational}</p>
              </section>
            </div>
            {theatre ? (
              <aside className="mb-sheet">
                <h2>{tx.hqPolicy}</h2>
                <p>
                  {theatre.label}: {theatre.workload} {tx.weeklyLoad}
                </p>
                <label>
                  {tx.leaveApproval} {Math.round(leave * 100)} {tx.percent}
                  <input
                    max={0.95}
                    min={0.4}
                    onChange={(event) => setLeaveRate(Number(event.target.value))}
                    step={0.01}
                    type="range"
                    value={leave}
                  />
                </label>
                <label>
                  {tx.rotation} {months} {tx.months}
                  <input
                    max={36}
                    min={12}
                    onChange={(event) => setRotation(Number(event.target.value))}
                    type="range"
                    value={months}
                  />
                </label>
                <label>
                  {tx.hqDutyCap} {duty} {tx.days}
                  <input
                    max={14}
                    min={6}
                    onChange={(event) => setDutyCap(Number(event.target.value))}
                    type="range"
                    value={duty}
                  />
                </label>
                <label>
                  {tx.hqQuickReturn} {returns}
                  <input
                    max={4}
                    min={0}
                    onChange={(event) => setQuickReturn(Number(event.target.value))}
                    type="range"
                    value={returns}
                  />
                </label>
                <button className="mb-primary" disabled={busy} onClick={() => void project()} type="button">
                  {tx.projectPolicy}
                </button>
                <p>{tx.hqAfter}</p>
                <label>
                  {tx.monthlyBrief}
                  <textarea onChange={(event) => setBrief(event.target.value)} rows={4} value={body} />
                </label>
                <div className="mb-action-row">
                  <button
                    className="mb-secondary"
                    onClick={() => {
                      void engineClient()
                        .hqSaveBrief(body)
                        .then(() => {
                          setStatus(tx.briefSaved);
                          reload();
                        });
                    }}
                    type="button"
                  >
                    {tx.saveBrief}
                  </button>
                  <button
                    className="mb-ghost"
                    onClick={() => {
                      void engineClient()
                        .hqBriefPdf()
                        .then((blob) => {
                          const url = URL.createObjectURL(blob);
                          const link = document.createElement("a");
                          link.href = url;
                          link.download = "monthly-brief.pdf";
                          link.click();
                          URL.revokeObjectURL(url);
                          setStatus(tx.briefExported);
                        });
                    }}
                    type="button"
                  >
                    {tx.exportPdf}
                  </button>
                </div>
              </aside>
            ) : null}
          </div>
        </div>
      ) : null}
    </ScreenState>
  );
}
