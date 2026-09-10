import { FormEvent, useEffect, useState } from "react";

import { ApiError, createClient, fairnessPayloadHasNoToken } from "../api/client";
import type { AuditRow, FairnessReport, ResolvedIdentity, Session } from "../api/types";
import { Notice } from "../components/Notice";

type Props = { session: Session };

export function WdecOversight({ session }: Props) {
  const api = createClient(session);
  const [unit, setUnit] = useState(session.unitCode || "12BN_A");
  const [fairness, setFairness] = useState<FairnessReport | null>(null);
  const [events, setEvents] = useState<AuditRow[]>([]);
  const [identity, setIdentity] = useState<ResolvedIdentity | null>(null);
  const [remaining, setRemaining] = useState(0);
  const [error, setError] = useState("");

  useEffect(() => {
    void api
      .audit()
      .then((body) => setEvents(body.events))
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : "audit unavailable");
      });
  }, [session.token]);

  useEffect(() => {
    if (!identity) return;
    setRemaining(60);
    const timer = window.setInterval(() => {
      setRemaining((value) => {
        if (value <= 1) {
          setIdentity(null);
          return 0;
        }
        return value - 1;
      });
    }, 1000);
    return () => window.clearInterval(timer);
  }, [identity]);

  async function loadFairness(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const report = await api.fairness(unit);
      if (!fairnessPayloadHasNoToken(report)) {
        throw new Error("fairness report contained a subject token");
      }
      setError("");
      setFairness(report);
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : "fairness report unavailable");
    }
  }

  async function onBreakGlass(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const person = await api.invokeBreakGlass(
        Number(form.get("case_id")),
        String(form.get("justification")),
        String(form.get("second_approver_id")),
      );
      setError("");
      setIdentity(person);
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : "break-glass refused");
    }
  }

  return (
    <>
      {error ? <Notice tone="error">{error}</Notice> : null}
      <section className="panel">
        <h2>Fairness by rank band</h2>
        <p className="muted">Cells below k are withheld. Tokens never appear.</p>
        <form className="row" onSubmit={(event) => void loadFairness(event)}>
          <label htmlFor="fairness-unit">
            Unit
            <input id="fairness-unit" value={unit} onChange={(event) => setUnit(event.target.value)} />
          </label>
          <button type="submit">Load</button>
        </form>
        {fairness ? (
          <ul>
            {fairness.cells.map((cell) => (
              <li key={cell.rank_band}>
                {cell.rank_band}: {cell.suppressed ? "withheld" : `${cell.elevated_band} · ${cell.dominant_category}`}
              </li>
            ))}
          </ul>
        ) : null}
      </section>
      <section className="panel">
        <h2>Audit browser</h2>
        <p className="muted">Pseudonymous tokens only. Identifying detail is stripped.</p>
        <table>
          <thead>
            <tr>
              <th>When</th>
              <th>Action</th>
              <th>Token</th>
            </tr>
          </thead>
          <tbody>
            {events.map((row) => (
              <tr key={row.id}>
                <td>{row.occurred_at}</td>
                <td>{row.action}</td>
                <td>{row.subject_token || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <section className="panel">
        <h2>Break-glass resolve</h2>
        <p className="muted">Requires a second approver. The name is shown for 60 seconds and is not stored.</p>
        {identity ? (
          <div className="identity-flash" role="dialog" aria-label="Break-glass identity, ephemeral">
            <strong>{identity.full_name}</strong>
            <div>
              {identity.rank_code} · {identity.service_no}
            </div>
            <time>Clears in {remaining}s. This is not stored.</time>
          </div>
        ) : null}
        <form className="grid" onSubmit={(event) => void onBreakGlass(event)}>
          <label htmlFor="case_id">
            Case
            <input id="case_id" name="case_id" required aria-required="true" />
          </label>
          <label htmlFor="justification">
            Justification
            <textarea id="justification" name="justification" required aria-required="true" rows={2} />
          </label>
          <label htmlFor="second_approver_id">
            Second approver
            <input id="second_approver_id" name="second_approver_id" required aria-required="true" />
          </label>
          <button type="submit" className="danger">
            Reveal identity
          </button>
        </form>
      </section>
    </>
  );
}
