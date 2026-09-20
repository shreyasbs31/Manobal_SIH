"use client";

import { useMemo, useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { useConsoleLang } from "@/lib/console-i18n";
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

interface Sector {
  id: string;
  x: number;
  y: number;
  band: string;
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
  const [busy, setBusy] = useState(false);
  const payload = data as
    | {
        theatres: Theatre[];
        sectors: Sector[];
        capacity: { demand: string; recommend: string };
        retention: { transfer_requests: string; exit_intent_tags: string };
        policy: Record<string, number>;
        brief: { title: string; body: string; edited: boolean };
      }
    | null;
  const body = brief || payload?.brief.body || "";
  const policy = payload?.policy;
  const leave = leaveRate ?? Number(policy?.leave_approval_rate ?? 0.62);
  const months = rotation ?? Number(policy?.rotation_length_months ?? 24);
  const theatre = useMemo(
    () => payload?.theatres.find((row) => row.id === selected) ?? payload?.theatres[0],
    [payload, selected],
  );

  async function project() {
    setBusy(true);
    try {
      const result = await engineClient().hqSimulate({
        leave_approval_rate: leave,
        rotation_length_months: months,
      });
      setStatus(String(result.projected ?? "Projected."));
      reload();
    } catch (caught: unknown) {
      setStatus(caught instanceof Error ? caught.message : "Could not project.");
    } finally {
      setBusy(false);
    }
  }

  const theatreId = (sectorId: string) =>
    sectorId.startsWith("N") ? "north" : sectorId.startsWith("E") ? "east" : "central";

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={!payload}>
      {payload ? (
        <div className="mb-desk mb-desk-fill">
          <div className="mb-theatre-grid">
            {payload.theatres.map((row) => (
              <button
                aria-pressed={row.id === selected}
                className="mb-theatre"
                key={row.id}
                onClick={() => setSelected(row.id)}
                type="button"
              >
                <strong>{row.label}</strong>
                <span>{row.workload}</span>
                <em>{row.posture}</em>
              </button>
            ))}
          </div>
          <div className="mb-hq-split">
            <div className="mb-hq-board" aria-label="Schematic sector board">
              {payload.sectors.map((sector) => (
                <button
                  aria-pressed={theatreId(sector.id) === selected}
                  className="mb-hq-sector"
                  data-band={sector.band}
                  key={sector.id}
                  onClick={() => setSelected(theatreId(sector.id))}
                  style={{ left: `${sector.x}%`, top: `${sector.y}%` }}
                  type="button"
                >
                  {sector.id}
                </button>
              ))}
            </div>
            {theatre ? (
              <aside className="mb-sheet">
                <h2>{theatre.label}</h2>
                <p className="mb-sheet-metric">
                  {theatre.workload} {tx.weeklyLoad}
                </p>
                <p>
                  {tx.leave} {theatre.leave}. {tx.incidentShort} {theatre.incidents}.
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
                <button className="mb-primary" disabled={busy} onClick={() => void project()} type="button">
                  {tx.projectPolicy}
                </button>
                {status ? <p role="status">{status}</p> : null}
                <div className="mb-action-row">
                  <button
                    className="mb-secondary"
                    onClick={() => {
                      void engineClient()
                        .hqSaveBrief(body)
                        .then(() => {
                          setStatus("Brief saved.");
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
                          setStatus("Brief exported.");
                        });
                    }}
                    type="button"
                  >
                    {tx.exportPdf}
                  </button>
                </div>
                <label>
                  {tx.monthlyBrief}
                  <textarea onChange={(event) => setBrief(event.target.value)} rows={4} value={body} />
                </label>
              </aside>
            ) : null}
          </div>
        </div>
      ) : null}
    </ScreenState>
  );
}
