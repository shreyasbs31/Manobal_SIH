import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ApiError, createClient } from "../api/client";
import type { CaseSummary, Session } from "../api/types";
import { EmptyState } from "../components/EmptyState";
import { Notice } from "../components/Notice";
import { categoryList } from "../ui/format";

type Props = { session: Session };

export function ClinicalQueue({ session }: Props) {
  const api = createClient(session);
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    void api
      .clinicalQueue()
      .then((body) => {
        setCases(body.cases);
        setLoaded(true);
      })
      .catch((err: unknown) => {
        setLoaded(true);
        setError(err instanceof ApiError ? err.message : "clinical queue unavailable");
      });
  }, [session.token]);

  return (
    <section className="panel">
      <h2>Clinical referrals</h2>
      <p className="muted">Live grants only. You are never the assigned welfare officer.</p>
      {error ? <Notice tone="error">{error}</Notice> : null}
      {!loaded ? (
        <p className="muted">Loading referrals…</p>
      ) : !cases.length ? (
        <EmptyState title="No live referrals">Welfare officers refer T3 and T4 cases here. You cannot be assigned the case.</EmptyState>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Case</th>
              <th>Tier</th>
              <th>Categories</th>
            </tr>
          </thead>
          <tbody>
            {cases.map((row) => (
              <tr key={row.id}>
                <td>
                  <Link to={`/clinical/cases/${row.id}`}>
                    Case {row.id} · {row.tier}
                  </Link>
                </td>
                <td>{row.tier}</td>
                <td>{categoryList(row.contributing_categories)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
