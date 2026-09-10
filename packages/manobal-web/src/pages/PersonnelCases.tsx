import { FormEvent, useEffect, useState } from "react";

import { ApiError, createClient } from "../api/client";
import type { DisclosureRow, OwnCase, Session } from "../api/types";
import { EmptyState } from "../components/EmptyState";
import { Notice } from "../components/Notice";

type Props = { session: Session };

export function PersonnelCases({ session }: Props) {
  const api = createClient(session);
  const [cases, setCases] = useState<OwnCase[]>([]);
  const [requests, setRequests] = useState<DisclosureRow[]>([]);
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);

  async function refresh() {
    const [nextCases, nextRequests] = await Promise.all([api.myCases(), api.disclosures()]);
    setCases(nextCases.cases);
    setRequests(nextRequests.requests);
    setLoaded(true);
  }

  useEffect(() => {
    void refresh().catch((err: unknown) => {
      setLoaded(true);
      setError(err instanceof ApiError ? err.message : "cases unavailable");
    });
  }, [session.token]);

  async function onContest(event: FormEvent<HTMLFormElement>, id: number) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await api.contestCase(id, String(form.get("note") || ""));
      setError("");
      await refresh();
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : "could not contest this flag");
    }
  }

  async function answer(id: number, granted: boolean) {
    try {
      await api.answerDisclosure(id, granted);
      setError("");
      await refresh();
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : "could not answer the disclosure request");
    }
  }

  return (
    <section className="panel anchor" id="flags">
      <h2>Your flags</h2>
      <p className="muted">Contest a flag without changing the assessment. Disclosure is yours to grant.</p>
      {error ? <Notice tone="error">{error}</Notice> : null}
      {loaded && !cases.length ? (
        <EmptyState title="No open flags">If a welfare conversation is opened, it will appear here.</EmptyState>
      ) : (
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
      )}
      <h3>Disclosure requests</h3>
      {loaded && !requests.length ? (
        <EmptyState title="No disclosure requests">Officers cannot see a category trend until you grant it.</EmptyState>
      ) : (
        <ul>
          {requests.map((row) => (
            <li key={row.id}>
              {row.category} — {row.rationale}
              {row.granted == null ? (
                <span className="row">
                  <button type="button" className="ghost" onClick={() => void answer(row.id, true)}>
                    Grant
                  </button>
                  <button type="button" className="ghost" onClick={() => void answer(row.id, false)}>
                    Refuse
                  </button>
                </span>
              ) : (
                <span className={`pill ${row.granted ? "ok" : "bad"}`}>{row.granted ? "granted" : "refused"}</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
