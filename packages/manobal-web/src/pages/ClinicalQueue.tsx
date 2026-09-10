import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ApiError, createClient } from "../api/client";
import type { CaseSummary, Session } from "../api/types";
import { Notice } from "../components/Notice";

type Props = { session: Session };

export function ClinicalQueue({ session }: Props) {
  const api = createClient(session);
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    void api
      .clinicalQueue()
      .then((body) => setCases(body.cases))
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : "clinical queue unavailable");
      });
  }, [session.token]);

  return (
    <section className="panel">
      <h2>Clinical referrals</h2>
      <p className="muted">Live grants only. You are never the assigned welfare officer.</p>
      {error ? <Notice tone="error">{error}</Notice> : null}
      <ul>
        {cases.map((row) => (
          <li key={row.id}>
            <Link to={`/clinical/cases/${row.id}`}>
              Case {row.id} · {row.tier}
            </Link>{" "}
            · {row.contributing_categories.join(", ")}
          </li>
        ))}
      </ul>
    </section>
  );
}
