import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ApiError, createClient } from "../api/client";
import type { CaseSummary, Session } from "../api/types";
import { Notice } from "../components/Notice";

type Props = { session: Session };

export function OfficerQueue({ session }: Props) {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    void createClient(session)
      .queue()
      .then((body) => setCases(body.cases))
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : "queue unavailable");
      });
  }, [session.token]);

  return (
    <>
      <h1>Assigned cases</h1>
      <p className="muted">Tokens and category names only. There is no score on this board.</p>
      {error ? <Notice tone="error">{error}</Notice> : null}
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
                <Link to={`/officer/cases/${item.id}`}>{item.subject_token}</Link>
              </td>
              <td>{item.tier}</td>
              <td>{item.contributing_categories.join(", ")}</td>
              <td>{item.sla_due_at}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
