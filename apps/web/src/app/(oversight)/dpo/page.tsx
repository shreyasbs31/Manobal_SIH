"use client";

import { useState } from "react";

import { ScreenState } from "@/components/screen-state";
import { engineClient } from "@/lib/engine";
import { useEngine } from "@/lib/use-engine";

type DpoPayload = {
  requests: { id: string; kind: string; status: string; due: string; token_hint: string }[];
  breaches: { id: string; status?: string }[];
  notices: { id: string; title: string; status: string }[];
};

export default function DpoPage() {
  const [notice, setNotice] = useState<string | null>(null);
  const { data, error, loading, offline, reload } = useEngine("dpo", (client, signal) =>
    client.dpoRequests(signal) as Promise<DpoPayload>,
  );

  return (
    <ScreenState
      empty={!data}
      emptyText="No open rights requests."
      error={error}
      loading={loading}
      offline={offline}
    >
      {data ? (
        <div className="mb-dpo">
          <p>Access, correction, erasure, nomination, and grievance. Due dates are visible. Tokens stay masked.</p>
          {notice ? <p role="status">{notice}</p> : null}
          <table className="mb-compare">
            <caption>Open requests</caption>
            <thead>
              <tr>
                <th scope="col">Kind</th>
                <th scope="col">Due</th>
                <th scope="col">Hint</th>
                <th scope="col">Status</th>
                <th scope="col">Action</th>
              </tr>
            </thead>
            <tbody>
              {data.requests.map((row) => (
                <tr key={row.id}>
                  <td>{row.kind}</td>
                  <td>{row.due}</td>
                  <td>{row.token_hint}</td>
                  <td>{row.status}</td>
                  <td>
                    <button
                      className="mb-secondary"
                      onClick={() => {
                        void engineClient()
                          .dpoDecide(row.id, "closed")
                          .then(() => {
                            setNotice("Request closed with a receipt path.");
                            reload();
                          });
                      }}
                      type="button"
                    >
                      Close
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <h2>Notices</h2>
          <ul>
            {data.notices.map((row) => (
              <li key={row.id}>
                {row.title}: {row.status}
              </li>
            ))}
          </ul>
          <p>
            Breach log: {data.breaches.length === 0 ? "none open." : `${data.breaches.length} open.`}
          </p>
        </div>
      ) : null}
    </ScreenState>
  );
}
