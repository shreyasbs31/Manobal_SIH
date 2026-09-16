"use client";

import { useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { engineClient } from "@/lib/engine";
import { useEngine } from "@/lib/use-engine";

type Jobs = {
  contracts: { name: string; fields: string[]; forbidden: string[] }[];
  jobs: { id: string; source: string; status: string; accepted: number; held: number }[];
  quarantine: { row: string; reason: string; field: string }[];
  quality: { completeness: number; tokenised: boolean; name_columns: number };
};

export default function IntegrationsPage() {
  const [notice, setNotice] = useState<string | null>(null);
  const { data, error, loading, offline, reload } = useEngine("integrations", (client, signal) =>
    client.integrationsJobs(signal) as Promise<Jobs>,
  );

  return (
    <ScreenState error={error} loading={loading} offline={offline} empty={!data}>
      {data ? (
        <div className="mb-integrate">
          <p>CSV and API uploads are tokenised before they reach the engine. Identity fields are quarantined.</p>
          {notice ? <p role="status">{notice}</p> : null}
          <h2>Schema contracts</h2>
          <table className="mb-compare">
            <caption>Accepted fields</caption>
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
          <h2>Jobs</h2>
          <ul>
            {data.jobs.map((job) => (
              <li key={job.id}>
                {job.source}: {job.status}. Accepted {job.accepted}. Held {job.held}.
              </li>
            ))}
          </ul>
          <h2>Quarantine</h2>
          {data.quarantine.length === 0 ? (
            <p>Nothing held.</p>
          ) : (
            <ul>
              {data.quarantine.map((row) => (
                <li key={`${row.row}-${row.field}`}>
                  Row {row.row}: {row.reason}
                </li>
              ))}
            </ul>
          )}
          <p>
            Completeness {data.quality.completeness}. Tokenised{" "}
            {data.quality.tokenised ? "yes" : "no"}. Name columns {data.quality.name_columns}.
          </p>
          <button
            className="mb-secondary"
            onClick={() => {
              void engineClient()
                .integrationsUpload("probe.csv", [{ full_name: "should-not-pass", duty_date: "2026-09-16" }])
                .then(() => {
                  setNotice("The name column was quarantined.");
                  reload();
                });
            }}
            type="button"
          >
            Probe a name column
          </button>
        </div>
      ) : null}
    </ScreenState>
  );
}
