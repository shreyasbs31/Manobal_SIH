import { FormEvent, useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { ApiError, createClient } from "../api/client";
import type { CaseDetail, ResolvedIdentity, Session } from "../api/types";
import { Notice } from "../components/Notice";
import { OfficerFollowup } from "./OfficerFollowup";

type Props = { session: Session };

export function OfficerCase({ session }: Props) {
  const { caseId } = useParams();
  const id = Number(caseId);
  const api = createClient(session);
  const consultOnly = session.role === "medical_officer";
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [identity, setIdentity] = useState<ResolvedIdentity | null>(null);
  const [remaining, setRemaining] = useState(0);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) return;
    void api.caseDetail(id).then(setDetail).catch((err: unknown) => {
      setError(err instanceof ApiError ? err.message : "case unavailable");
    });
  }, [id, session.token]);

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

  async function onResolve() {
    const person = await api.resolve(id);
    setIdentity(person);
  }

  async function onDecide(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const next = await api.decide(
      id,
      String(form.get("outcome_code")),
      String(form.get("rationale")),
      String(form.get("status")),
    );
    setDetail(next);
  }

  if (!detail) {
    return error ? <Notice tone="error">{error}</Notice> : <p>Loading…</p>;
  }

  return (
    <>
      <h1>Case {detail.id}</h1>
      <p className={`tier ${detail.tier}`}>{detail.tier}</p>
      <p>{detail.contributing_categories.join(", ")}</p>
      <p className="muted">Token {detail.subject_token} · {detail.status}</p>
      {detail.contested_at ? <Notice>Contested: {detail.contest_note}</Notice> : null}

      {identity ? (
        <div className="identity-flash" role="dialog" aria-label="Resolved identity, ephemeral">
          <strong>{identity.full_name}</strong>
          <div>
            {identity.rank_code} · {identity.service_no}
          </div>
          <div>{identity.mobile_e164}</div>
          <time>Clears in {remaining}s. This is not stored.</time>
        </div>
      ) : null}

      {consultOnly ? (
        <Notice>Consult only. You are not the assigned welfare officer and cannot close this case.</Notice>
      ) : (
        <div className="row">
          <button type="button" className="ghost" onClick={() => void api.contact(id).then(setDetail)}>
            Record contact
          </button>
          {detail.tier === "T4" ? (
            <button type="button" className="danger" onClick={() => void onResolve().catch((err: unknown) => {
              setError(err instanceof ApiError ? err.message : "resolve refused");
            })}>
              Reveal identity
            </button>
          ) : null}
        </div>
      )}

      <section className="panel">
        <h2>Recommended next steps</h2>
        <ul>
          {detail.recommendations.map((row) => (
            <li key={row.code}>
              <strong>{row.code}</strong> — {row.rationale}
            </li>
          ))}
        </ul>
      </section>

      {consultOnly ? null : (
        <>
          <section className="panel">
            <h2>Close the case</h2>
            <form className="grid" onSubmit={(event) => void onDecide(event)}>
              <label htmlFor="outcome_code">
                Outcome
                <input id="outcome_code" name="outcome_code" required aria-required="true" />
              </label>
              <label htmlFor="rationale">
                Rationale
                <textarea id="rationale" name="rationale" required aria-required="true" rows={3} />
              </label>
              <label htmlFor="status">
                Status
                <select id="status" name="status" defaultValue="resolved">
                  <option value="resolved">Resolved</option>
                  <option value="no_action">No action needed</option>
                </select>
              </label>
              <button type="submit">Record decision</button>
            </form>
          </section>
          <OfficerFollowup session={session} caseId={detail.id} />
        </>
      )}
    </>
  );
}
