import { FormEvent, useEffect, useState } from "react";

import { ApiError, createClient } from "../api/client";
import type { JournalEntry, Session } from "../api/types";
import { EmptyState } from "../components/EmptyState";
import { Notice } from "../components/Notice";
import { formatWhen } from "../ui/format";

type Props = { session: Session };

export function PersonnelJournal({ session }: Props) {
  const api = createClient(session);
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [body, setBody] = useState("");
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);

  async function refresh() {
    const next = await api.journal();
    setEntries(next.entries);
    setLoaded(true);
  }

  useEffect(() => {
    void refresh().catch((err: unknown) => {
      setLoaded(true);
      setError(err instanceof ApiError ? err.message : "journal unavailable");
    });
  }, [session.token]);

  async function onWrite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await api.writeJournal(body, form.get("crisis") === "on");
      setBody("");
      setError("");
      await refresh();
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : "could not save the entry");
    }
  }

  return (
    <section className="panel anchor" id="journal">
      <h2>Private journal</h2>
      <p className="muted">Encrypted for you. Officers never see this. It is never scored.</p>
      {error ? <Notice tone="error">{error}</Notice> : null}
      <form className="grid" onSubmit={(event) => void onWrite(event)}>
        <label htmlFor="journal-body">
          Entry
          <textarea
            id="journal-body"
            value={body}
            onChange={(event) => setBody(event.target.value)}
            required
            aria-required="true"
            rows={4}
          />
        </label>
        <label htmlFor="journal-crisis" className="check">
          <input id="journal-crisis" name="crisis" type="checkbox" />
          I want help now
        </label>
        <button type="submit">Save entry</button>
      </form>
      {loaded && !entries.length ? (
        <EmptyState title="No entries yet">Write privately. This never reaches the risk engine.</EmptyState>
      ) : (
        <ul>
          {entries.map((row) => (
            <li key={row.id}>
              {formatWhen(row.created_at)} — {row.body}
              {row.crisis_referred ? " (help requested)" : ""}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
