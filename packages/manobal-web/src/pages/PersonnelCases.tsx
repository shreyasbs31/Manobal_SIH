import { FormEvent, useEffect, useState } from "react";

import { ApiError, createClient } from "../api/client";
import type { DisclosureRow, OwnCase, Session } from "../api/types";
import { Notice } from "../components/Notice";

type Props = { session: Session };

export function PersonnelCases({ session }: Props) {
  const api = createClient(session);
  const [cases, setCases] = useState<OwnCase[]>([]);
  const [requests, setRequests] = useState<DisclosureRow[]>([]);
  const [error, setError] = useState("");

  async function refresh() {
    const [nextCases, nextRequests] = await Promise.all([api.myCases(), api.disclosures()]);
    setCases(nextCases.cases);
    setRequests(nextRequests.requests);
  }

  useEffect(() => {
    void refresh().catch((err: unknown) => {
      setError(err instanceof ApiError ? err.message : "cases unavailable");
    });
  }, [session.token]);

  async function onContest(event: FormEvent<HTMLFormElement>, id: number) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await api.contestCase(id, String(form.get("note") || ""));
    await refresh();
  }

  return (
    <section className="panel">
      <h2>Your flags</h2>
      <p className="muted">Contest a flag without changing the assessment. Disclosure is yours to grant.</p>
      {error ? <Notice tone="error">{error}</Notice> : null}
      <ul>
        {cases.map((row) => (
          <li key={row.id}>
            Case {row.id} · {row.tier} · {row.status}
            {row.status === "open" || row.status === "contacted" ? (
              <form className="row" onSubmit={(event) => void onContest(event, row.id)}>
                <label htmlFor={`contest-${row.id}`}>
                  Contest note
                  <input id={`contest-${row.id}`} name="note" required aria-required="true" />
                </label>
                <button type="submit">Contest</button>
              </form>
            ) : null}
          </li>
        ))}
      </ul>
      <h3>Disclosure requests</h3>
      <ul>
        {requests.map((row) => (
          <li key={row.id}>
            {row.category} — {row.rationale}
            {row.granted == null ? (
              <span className="row">
                <button type="button" className="ghost" onClick={() => void api.answerDisclosure(row.id, true).then(refresh)}>
                  Grant
                </button>
                <button type="button" className="ghost" onClick={() => void api.answerDisclosure(row.id, false).then(refresh)}>
                  Refuse
                </button>
              </span>
            ) : (
              <span className="muted">{row.granted ? "granted" : "refused"}</span>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
