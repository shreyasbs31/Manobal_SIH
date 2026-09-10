import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ApiError, createClient } from "../api/client";
import type { CaseSummary, Session } from "../api/types";
import { EmptyState } from "../components/EmptyState";
import { Notice } from "../components/Notice";
import { PageHeader } from "../components/PageHeader";
import { categoryList, formatWhen, shortToken } from "../ui/format";

type Props = { session: Session };

export function OfficerQueue({ session }: Props) {
  const [cases, setCases] = useState<CaseSummary[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    void createClient(session)
      .queue()
      .then((body) => setCases(body.cases))
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : "queue unavailable");
        setCases([]);
      });
  }, [session.token]);

  return (
    <div className="stack">
      <PageHeader
        eyebrow="Welfare officer"
        title="Assigned cases"
        lede="Tokens and category names only. There is no score on this board."
      />
      {error ? <Notice tone="error">{error}</Notice> : null}
      {!cases ? (
        <p className="muted">Loading the queue…</p>
      ) : !cases.length ? (
        <EmptyState title="No assigned cases">Open flags in your unit will appear here with a due time.</EmptyState>
      ) : (
        <section className="panel">
          <table>
            <thead>
              <tr>
                <th>Case</th>
                <th>Tier</th>
                <th>Categories</th>
                <th>Due</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((item) => (
                <tr key={item.id}>
                  <td>
                    <Link to={`/officer/cases/${item.id}`}>Case {item.id}</Link>
                    <div className="muted mono">{shortToken(item.subject_token)}</div>
                  </td>
                  <td>
                    <span className={`pill ${item.tier === "T4" ? "bad" : item.tier === "T3" ? "warn" : ""}`}>
                      {item.tier}
                    </span>
                  </td>
                  <td>{categoryList(item.contributing_categories)}</td>
                  <td>{formatWhen(item.sla_due_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}
