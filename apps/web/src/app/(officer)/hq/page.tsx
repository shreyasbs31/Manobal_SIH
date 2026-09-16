"use client";

import { FairnessBar, KpiTile } from "@manobal/ui";
import { useState } from "react";

import { ScreenState } from "@/components/screen-state";
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

interface LeverItem {
  code: string;
  later_easing: string;
  n: string;
}

export default function HqPage() {
  const { data, error, loading, offline, reload } = useEngine("hq-overview", (client, signal) =>
    client.hqOverview(signal),
  );
  const profile = useEngine("officer-profile", (client, signal) => client.officerProfile(signal));
  const [brief, setBrief] = useState("");
  const [status, setStatus] = useState("");
  const payload = data as
    | {
        theatres: Theatre[];
        sectors: Sector[];
        capacity: { demand: string; recommend: string };
        levers: { note: string; items: LeverItem[] };
        retention: { transfer_requests: string; exit_intent_tags: string };
        policy: Record<string, number>;
        brief: { title: string; body: string; edited: boolean };
      }
    | null;
  const body = brief || payload?.brief.body || "";

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={!payload}>
      {payload ? (
        <div className="mb-home-stack">
          <p>
            Theatre comparison stays grouped. Cells under the minimum size stay hidden.
            {profile.data ? ` Lens ${String(profile.data.policy_lens)}.` : ""}
          </p>
          <div className="mb-hq-theatres">
            {payload.theatres.map((theatre) => (
              <article className="mb-card" key={theatre.id}>
                <h2>{theatre.label}</h2>
                <p>{theatre.posture}</p>
                <p>Workload {theatre.workload}</p>
                <p>Leave {theatre.leave}</p>
                <p>Incidents {theatre.incidents}</p>
                <p>Grievances {theatre.grievances}</p>
              </article>
            ))}
          </div>
          <div className="mb-hq-board" aria-label="Schematic sector board">
            {payload.sectors.map((sector) => (
              <span
                className="mb-hq-sector"
                data-band={sector.band}
                key={sector.id}
                style={{ left: `${sector.x}%`, top: `${sector.y}%` }}
              >
                {sector.id} {sector.band}
              </span>
            ))}
          </div>
          <div className="mb-grid-12">
            <div className="mb-span-4">
              <KpiTile hint="18-month view" label="Leave backlog" value="High in sector N" />
            </div>
            <div className="mb-span-4">
              <KpiTile hint={payload.capacity.recommend} label="Welfare capacity" value={payload.capacity.demand} />
            </div>
            <div className="mb-span-4">
              <KpiTile
                hint="k-anonymous"
                label="Retention pressure"
                value={payload.retention.transfer_requests}
              />
            </div>
          </div>
          <FairnessBar label="Posture share across theatres" ratio={1.04} />
          <section>
            <h2>Lever effectiveness</h2>
            <p>{payload.levers.note}</p>
            {payload.levers.items.map((item) => (
              <p key={item.code}>
                {item.code}: later easing {item.later_easing}. n {item.n}.
              </p>
            ))}
          </section>
          <section>
            <h2>Policy simulator</h2>
            <p>Leave approval {payload.policy.leave_approval_rate}. Rotation {payload.policy.rotation_length_months} months.</p>
            <button
              className="mb-secondary"
              onClick={() => {
                void engineClient()
                  .hqSimulate({ leave_approval_rate: 0.8 })
                  .then((result) => setStatus(String(result.projected ?? "Projected.")));
              }}
              type="button"
            >
              Project leave approval at 80 percent
            </button>
          </section>
          <section>
            <h2>{payload.brief.title}</h2>
            <label>
              Monthly brief
              <textarea onChange={(event) => setBrief(event.target.value)} rows={6} value={body} />
            </label>
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
              Save brief
            </button>
            <button
              className="mb-primary"
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
              Export PDF
            </button>
            {status ? <p role="status">{status}</p> : null}
          </section>
        </div>
      ) : null}
    </ScreenState>
  );
}
